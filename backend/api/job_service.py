from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import AutomationJob
from .tasks import execute_automation_job


class IdempotencyConflict(Exception):
    pass


class QueueSubmissionError(Exception):
    pass


class AccountJobAlreadyActive(Exception):
    pass


@dataclass
class Submission:
    job: AutomationJob
    created: bool


def submit_automation_job(*, user, account, action, targets, options, idempotency_key=None):
    defaults = {
        "account": account,
        "action": action,
        "targets": targets,
        "options": options,
        "status": AutomationJob.Status.QUEUED,
    }

    if idempotency_key:
        try:
            job, created = AutomationJob.objects.get_or_create(
                user=user,
                idempotency_key=idempotency_key,
                defaults=defaults,
            )
        except IntegrityError:
            try:
                job = AutomationJob.objects.get(
                    user=user,
                    idempotency_key=idempotency_key,
                )
                created = False
            except AutomationJob.DoesNotExist as exc:
                raise AccountJobAlreadyActive from exc
    else:
        try:
            with transaction.atomic():
                job = AutomationJob.objects.create(user=user, **defaults)
        except IntegrityError as exc:
            raise AccountJobAlreadyActive from exc
        created = True

    if not created:
        same_request = (
            job.account_id == account.id
            and job.action == action
            and job.targets == targets
            and job.options == options
        )
        if not same_request:
            raise IdempotencyConflict(
                "This idempotency key was already used for a different request."
            )
        return Submission(job=job, created=False)

    try:
        celery_result = execute_automation_job.apply_async(args=[str(job.id)])
    except Exception as exc:
        job.status = AutomationJob.Status.FAILED
        job.error = "The automation queue did not accept this job."
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error", "completed_at", "updated_at"])
        raise QueueSubmissionError from exc

    job.celery_task_id = celery_result.id
    job.save(update_fields=["celery_task_id", "updated_at"])
    return Submission(job=job, created=True)
