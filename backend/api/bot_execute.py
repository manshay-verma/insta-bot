import logging

from django.utils import timezone
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from account.models import BotAccount
from .openapi import (
    ApiErrorSchema,
    QueuedTaskResponseSchema,
    TaskStatusResponseSchema,
)
from .job_serializers import (
    AutomationJobCreateSerializer,
    AutomationJobStatusSerializer,
)
from .job_service import (
    AccountJobAlreadyActive,
    IdempotencyConflict,
    QueueSubmissionError,
    submit_automation_job,
)
from .models import AutomationJob

logger = logging.getLogger(__name__)


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
        return Response(AutomationJobStatusSerializer(job).data)


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
