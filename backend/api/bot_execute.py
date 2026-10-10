import logging

from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema
from redis import Redis
from redis.exceptions import RedisError

from account.models import BotAccount
from .openapi import (
    ApiErrorSchema,
    QueuedTaskResponseSchema,
    TaskStatusResponseSchema,
    VerificationCodeSubmitRequestSchema,
    VerificationCodeSubmitResponseSchema,
)
from .job_serializers import (
    AutomationJobCreateSerializer,
    AutomationJobStatusSerializer,
    VerificationCodeSubmitSerializer,
)
from .job_service import (
    AccountJobAlreadyActive,
    IdempotencyConflict,
    QueueSubmissionError,
    submit_automation_job,
)
from .models import AutomationJob
from .verification import otp_redis_key

logger = logging.getLogger(__name__)


def _expire_pending_verification(job):
    if (
        job.status == AutomationJob.Status.AWAITING_OTP
        and (
            job.verification_expires_at is None
            or job.verification_expires_at <= timezone.now()
        )
    ):
        expired_at = timezone.now()
        AutomationJob.objects.filter(
            id=job.id,
            status=AutomationJob.Status.AWAITING_OTP,
        ).update(
            status=AutomationJob.Status.FAILED,
            error="The verification challenge expired before a code was submitted.",
            completed_at=expired_at,
            verification_expires_at=None,
            updated_at=expired_at,
        )
        job.refresh_from_db()
        return True
    return False


class BotExecuteView(APIView):
    """Backward-compatible endpoint that submits an asynchronous automation job."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=str,
                location=OpenApiParameter.HEADER,
                required=False,
            )
        ],
        request=AutomationJobCreateSerializer,
        responses={
            202: QueuedTaskResponseSchema,
            200: QueuedTaskResponseSchema,
            400: ApiErrorSchema,
            409: ApiErrorSchema,
            503: ApiErrorSchema,
        },
    )
    def post(self, request):
        serializer = AutomationJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        accounts = BotAccount.objects.filter(owner=request.user)
        if request.user.is_staff:
            accounts = BotAccount.objects.all()
        try:
            account = accounts.get(id=data["account_id"])
        except BotAccount.DoesNotExist as exc:
            raise NotFound("Bot account not found.") from exc

        if account.status != "active":
            raise ValidationError({"account_id": "Bot account is not active."})

        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key and len(idempotency_key) > 128:
            raise ValidationError(
                {"Idempotency-Key": "Must be at most 128 characters."}
            )

        try:
            submission = submit_automation_job(
                user=request.user,
                account=account,
                action=data["action"],
                targets=data["targets"],
                options=data["options"],
                idempotency_key=idempotency_key,
            )
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except AccountJobAlreadyActive:
            return Response(
                {"detail": "An automation job is already active for this account."},
                status=status.HTTP_409_CONFLICT,
            )
        except QueueSubmissionError as exc:
            logger.error(
                "Celery queue rejected automation job",
                extra={
                    "account_id": account.id,
                    "action": data["action"],
                    "user_id": request.user.id,
                    "error_type": type(exc.__cause__ or exc).__name__,
                },
            )
            return Response(
                {
                    "status": AutomationJob.Status.FAILED,
                    "error": "The automation queue is unavailable.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        job = submission.job
        response_status = (
            status.HTTP_202_ACCEPTED
            if submission.created
            else status.HTTP_200_OK
        )
        return Response(
            {
                "job_id": str(job.id),
                "task_id": job.celery_task_id,
                "status": job.status,
                "message": "Automation job accepted."
                if submission.created
                else "Existing automation job returned.",
            },
            status=response_status,
        )


class BotExecuteAsyncView(BotExecuteView):
    """Legacy async route; shares the same durable-job submission implementation."""


class TaskStatusView(APIView):
    """Return durable application job state, not Celery AsyncResult state."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TaskStatusResponseSchema, 404: ApiErrorSchema})
    def get(self, request, task_id):
        try:
            if request.resolver_match.url_name == "task-status":
                job = AutomationJob.objects.get(
                    celery_task_id=task_id,
                    user=request.user,
                )
            else:
                job = AutomationJob.objects.get(id=task_id, user=request.user)
        except (AutomationJob.DoesNotExist, ValueError) as exc:
            raise NotFound("Automation job not found.") from exc
        _expire_pending_verification(job)
        return Response(AutomationJobStatusSerializer(job).data)


class VerificationCodeSubmitView(APIView):
    """Receive one user-supplied OTP for an owned pending automation job."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=VerificationCodeSubmitRequestSchema,
        responses={
            202: VerificationCodeSubmitResponseSchema,
            400: ApiErrorSchema,
            404: ApiErrorSchema,
            409: ApiErrorSchema,
            503: ApiErrorSchema,
        },
    )
    def post(self, request, job_id):
        serializer = VerificationCodeSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        redis_client = Redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            with transaction.atomic():
                try:
                    job = AutomationJob.objects.select_for_update().get(
                        id=job_id,
                        user=request.user,
                    )
                except (AutomationJob.DoesNotExist, ValueError) as exc:
                    raise NotFound("Automation job not found.") from exc

                if _expire_pending_verification(job):
                    response = Response(
                        {"detail": "The verification challenge has expired."},
                        status=status.HTTP_409_CONFLICT,
                    )
                elif (
                    job.status != AutomationJob.Status.AWAITING_OTP
                    or job.cancel_requested
                ):
                    response = Response(
                        {"detail": "This job is not waiting for a verification code."},
                        status=status.HTTP_409_CONFLICT,
                    )
                else:
                    try:
                        accepted = redis_client.set(
                            otp_redis_key(job.id),
                            serializer.validated_data["code"],
                            ex=max(
                                1,
                                int(
                                    (
                                        job.verification_expires_at
                                        - timezone.now()
                                    ).total_seconds()
                                ),
                            ),
                            nx=True,
                        )
                    except RedisError:
                        logger.exception(
                            "Could not deliver verification code to automation worker",
                            extra={"job_id": str(job.id)},
                        )
                        response = Response(
                            {
                                "detail": (
                                    "Verification delivery is temporarily unavailable."
                                )
                            },
                            status=status.HTTP_503_SERVICE_UNAVAILABLE,
                        )
                    else:
                        response = (
                            Response(
                                {"status": "received"},
                                status=status.HTTP_202_ACCEPTED,
                            )
                            if accepted
                            else Response(
                                {
                                    "detail": (
                                        "A verification code is already awaiting "
                                        "processing."
                                    )
                                },
                                status=status.HTTP_409_CONFLICT,
                            )
                        )
        finally:
            redis_client.close()
        return response


class JobCancelView(APIView):
    """Request safe cancellation of a queued or running job."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TaskStatusResponseSchema, 404: ApiErrorSchema})
    def post(self, request, job_id):
        revoke_task_id = None
        with transaction.atomic():
            try:
                job = AutomationJob.objects.select_for_update().get(
                    id=job_id,
                    user=request.user,
                )
            except (AutomationJob.DoesNotExist, ValueError) as exc:
                raise NotFound("Automation job not found.") from exc

            if job.status in {
                AutomationJob.Status.QUEUED,
                AutomationJob.Status.RETRYING,
            }:
                job.status = AutomationJob.Status.CANCELLED
                job.completed_at = timezone.now()
                job.cancel_requested = True
                job.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        "cancel_requested",
                        "updated_at",
                    ]
                )
                revoke_task_id = job.celery_task_id or None
            elif job.status == AutomationJob.Status.RUNNING:
                job.cancel_requested = True
                job.status = AutomationJob.Status.CANCELLING
                job.save(update_fields=["cancel_requested", "status", "updated_at"])
            elif job.status == AutomationJob.Status.AWAITING_OTP:
                job.cancel_requested = True
                job.status = AutomationJob.Status.CANCELLING
                job.verification_expires_at = None
                job.save(
                    update_fields=[
                        "cancel_requested",
                        "status",
                        "verification_expires_at",
                        "updated_at",
                    ]
                )

        if revoke_task_id:
            from celery import current_app

            try:
                current_app.control.revoke(revoke_task_id, terminate=False)
            except Exception:
                logger.warning(
                    "Could not publish Celery revoke; worker will observe durable cancellation.",
                    extra={"job_id": str(job.id), "task_id": revoke_task_id},
                )
        return Response(AutomationJobStatusSerializer(job).data)
