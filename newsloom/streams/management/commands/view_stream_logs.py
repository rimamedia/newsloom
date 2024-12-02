from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from streams.models import StreamLog


class Command(BaseCommand):
    help = "View stream execution logs"

    def add_arguments(self, parser):
        parser.add_argument("--stream-id", type=int, help="Filter logs by stream ID")
        parser.add_argument(
            "--status",
            choices=["success", "failed", "running"],
            help="Filter logs by status",
        )
        parser.add_argument(
            "--hours", type=int, default=24, help="Show logs from the last N hours"
        )

    def handle(self, *args, **options):
        # Build query
        logs = StreamLog.objects.select_related("stream")

        if options["stream_id"]:
            logs = logs.filter(stream_id=options["stream_id"])

        if options["status"]:
            logs = logs.filter(status=options["status"])

        if options["hours"]:
            since = timezone.now() - timedelta(hours=options["hours"])
            logs = logs.filter(started_at__gte=since)

        # Display logs
        for log in logs:
            self.stdout.write(
                f"\nStream: {log.stream.name} ({log.stream.id})\n"
                f"Status: {log.status}\n"
                f"Started: {log.started_at}\n"
                f"Completed: {log.completed_at or 'Not completed'}\n"
            )

            if log.error_message:
                self.stdout.write(self.style.ERROR(f"Error: {log.error_message}\n"))

            if log.result:
                self.stdout.write(f"Result: {log.result}\n")
