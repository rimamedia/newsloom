from agents.models import Agent
from chat.models import Chat, ChatMessage
from django.core.management.base import BaseCommand
from django.db import transaction
from mediamanager.models import Examples, Media
from sources.models import Doc, News, Source
from streams.models import Stream, StreamLog, TelegramDocPublishLog, TelegramPublishLog


class Command(BaseCommand):
    help = "Cleans up the database by removing all data except users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        if not options["force"]:
            self.stdout.write(
                "WARNING: This will delete all data\n"
                "Only user data will be preserved.\n"
                "Are you sure you want to continue? [y/N] "
            )
            if input().lower() != "y":
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return

        try:
            with transaction.atomic():
                # Delete all logs and streams since they reference other models
                stream_logs_count = StreamLog.objects.all().count()
                StreamLog.objects.all().delete()

                streams_count = Stream.objects.all().count()
                Stream.objects.all().delete()

                telegram_publish_logs_count = TelegramPublishLog.objects.all().count()
                TelegramPublishLog.objects.all().delete()

                telegram_doc_publish_logs_count = (
                    TelegramDocPublishLog.objects.all().count()
                )
                TelegramDocPublishLog.objects.all().delete()

                # Delete chat messages and chats
                chat_messages_count = ChatMessage.objects.all().count()
                ChatMessage.objects.all().delete()

                chats_count = Chat.objects.all().count()
                Chat.objects.all().delete()

                # Delete news and docs
                news_count = News.objects.all().count()
                News.objects.all().delete()

                docs_count = Doc.objects.all().count()
                Doc.objects.all().delete()

                # Delete examples
                examples_count = Examples.objects.all().count()
                Examples.objects.all().delete()

                # Delete agents
                agents_count = Agent.objects.all().count()
                Agent.objects.all().delete()

                # Delete media and sources last since other models depend on them
                media_count = Media.objects.all().count()
                Media.objects.all().delete()

                sources_count = Source.objects.all().count()
                Source.objects.all().delete()

                # Print summary
                self.stdout.write(
                    self.style.SUCCESS("Successfully cleaned up the database:")
                )
                self.stdout.write(f"- Deleted {stream_logs_count} stream logs")
                self.stdout.write(f"- Deleted {streams_count} streams")
                self.stdout.write(
                    f"- Deleted {telegram_publish_logs_count} telegram publish logs"
                )
                self.stdout.write(
                    f"- Deleted {telegram_doc_publish_logs_count} telegram doc publish logs"
                )
                self.stdout.write(f"- Deleted {chat_messages_count} chat messages")
                self.stdout.write(f"- Deleted {chats_count} chats")
                self.stdout.write(f"- Deleted {news_count} news items")
                self.stdout.write(f"- Deleted {docs_count} docs")
                self.stdout.write(f"- Deleted {examples_count} examples")
                self.stdout.write(f"- Deleted {agents_count} agents")
                self.stdout.write(f"- Deleted {media_count} media")
                self.stdout.write(f"- Deleted {sources_count} sources")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"An error occurred while cleaning up the database: {str(e)}"
                )
            )
