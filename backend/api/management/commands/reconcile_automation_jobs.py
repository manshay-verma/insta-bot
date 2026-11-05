from django.core.management.base import BaseCommand
from api.reconciliation import reconcile_startup_jobs


class Command(BaseCommand):
    help = "Reconcile stale or unrecovered automation jobs and release orphaned browser locks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Audit recoverable jobs without modifying state",
        )
        parser.add_argument(
            "--non-blocking",
            action="store_true",
            help="Skip execution if another reconciliation is currently holding the advisory lock",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        blocking = not options.get("non_blocking", False)

        self.stdout.write(self.style.NOTICE("Starting automation reconciliation..."))
        result = reconcile_startup_jobs(blocking=blocking, dry_run=dry_run)

        if result.get("skipped_concurrent"):
            self.stdout.write(
                self.style.WARNING("Reconciliation skipped: another worker holds advisory lock.")
            )
            return

        reconciled = result.get("reconciled_jobs", 0)
        locks = result.get("locks_reconciled", 0)
        self.stdout.write(
            self.style.SUCCESS(
                f"Reconciliation completed successfully: {reconciled} jobs processed, {locks} locks cleaned."
            )
        )
        for res in result.get("results", []):
            self.stdout.write(f" - Job {res.get('job_id')}: {res.get('action')}")

