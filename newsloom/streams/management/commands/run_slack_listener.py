import json
import logging
import os
import time
import traceback

from chat.models import Chat
from chat.services.base_handler import BaseChatHandler
from django.core.management.base import BaseCommand
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logger = logging.getLogger(__name__)


class SlackChatHandler(BaseChatHandler):
    """Slack-specific implementation of the chat handler."""

    def __init__(self, app: App):
        super().__init__()
        self.app = app
        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Set up Slack event handlers."""

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            """Handle direct mentions of the bot."""
            await self.process_message(event, say, is_mention=True)

        @self.app.event("message")
        async def handle_message(event, say):
            """Handle thread replies."""
            # Only process thread replies where we're involved
            if event.get("thread_ts"):
                # Get the thread's chat to see if we're involved
                chat = Chat.objects.filter(
                    slack_channel_id=event.get("channel"),
                    slack_thread_ts=event.get("thread_ts"),
                ).first()

                if chat:
                    logger.info("Processing thread reply in existing chat")
                    await self.process_message(event, say, is_mention=False)
                else:
                    logger.info("Ignoring thread reply in unknown chat")

    async def process_message(self, event, say, is_mention=True):
        """Process both mentions and thread replies."""
        try:
            # Log incoming event
            event_type = "mention" if is_mention else "thread reply"
            logger.info(f"Received {event_type} event: {json.dumps(event, indent=2)}")

            # Extract relevant information
            channel_id = event.get("channel")
            current_ts = event.get("ts")  # Current message timestamp
            thread_ts = event.get(
                "thread_ts", current_ts
            )  # If in thread, use thread's ts
            user_id = event.get("user")
            text = event.get("text")

            # Skip bot's own messages
            if event.get("bot_id"):
                logger.info("Skipping bot's own message")
                return

            logger.info("Message details:")
            logger.info(f"- Channel ID: {channel_id}")
            logger.info(f"- Current TS: {current_ts}")
            logger.info(f"- Thread TS: {thread_ts}")
            logger.info(f"- Is thread reply: {bool(event.get('thread_ts'))}")
            logger.info(f"- User ID: {user_id}")
            logger.info(f"- Text: {text}")

            try:
                # Get user info from Slack
                user_info = self.app.client.users_info(user=user_id)
                if not user_info["ok"]:
                    raise ValueError(f"Could not get Slack user info for {user_id}")

                slack_user = user_info["user"]
                user_data = {
                    "id": user_id,
                    "email": slack_user.get("profile", {}).get(
                        "email", f"{user_id}@slack.user"
                    ),
                    "name": slack_user.get("real_name", user_id),
                }

                # Get or create Django user
                django_user = await self.user_service.get_or_create_user(
                    "slack", user_data
                )
                if not django_user:
                    logger.error(f"Could not create/get user for Slack ID: {user_id}")
                    say(
                        text="Sorry, there was an error processing your request.",
                        thread_ts=thread_ts,
                    )
                    return

                # Get or create chat thread
                chat = await self.user_service.get_or_create_chat(
                    "slack",
                    django_user,
                    {"chat_id": channel_id, "message_id": thread_ts},
                )
                logger.info(f"Using chat ID: {chat.id}")

                # Load chat history
                chat_history = await self.load_chat_history(chat)
                chat_history.append({"role": "user", "content": text})

                # Process message with Claude
                response = await self.message_processor.process_message(chat_history)

                if response:
                    logger.info("Got response from Claude, saving to database...")
                    # Save message and response
                    await self.save_message(
                        chat=chat,
                        user=django_user,
                        message=text,
                        response=response,
                        platform_data={"slack_ts": current_ts},
                    )
                    logger.info("Message saved successfully")

                    # Send to Slack
                    logger.info("Sending response to Slack...")
                    say(text=response, thread_ts=thread_ts)
                    logger.info("Response sent to Slack successfully")
                else:
                    logger.error("No response received from Claude")

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                logger.error(traceback.format_exc())
                say(
                    text="Sorry, there was an error processing your request.",
                    thread_ts=thread_ts,
                )

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            logger.error(traceback.format_exc())
            if "thread_ts" in locals():
                say(
                    text="Sorry, there was an error processing your request.",
                    thread_ts=thread_ts,
                )


class Command(BaseCommand):
    """Django management command to run the Slack bot."""

    help = "Starts the Slack event listener for chat integration"

    def handle(self, *args, **options):
        """Django command handler."""
        try:
            # Log environment variables (without sensitive values)
            self.stdout.write(self.style.SUCCESS("Checking Slack configuration..."))
            bot_token = os.environ.get("SLACK_BOT_TOKEN")
            app_token = os.environ.get("SLACK_APP_TOKEN")

            if not bot_token:
                self.stderr.write(
                    self.style.ERROR("SLACK_BOT_TOKEN not found in environment")
                )
                return
            if not app_token:
                self.stderr.write(
                    self.style.ERROR("SLACK_APP_TOKEN not found in environment")
                )
                return

            self.stdout.write(self.style.SUCCESS("Found required Slack tokens"))
            self.stdout.write(
                self.style.SUCCESS(f"Bot token prefix: {bot_token[:10]}...")
            )
            self.stdout.write(
                self.style.SUCCESS(f"App token prefix: {app_token[:10]}...")
            )

            # Initialize Slack app
            app = App(token=bot_token)

            # Test Slack API connection
            self.stdout.write(self.style.SUCCESS("Testing Slack API connection..."))
            try:
                auth_test = app.client.auth_test()
                if auth_test["ok"]:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully connected to Slack as {auth_test["bot_id"]}'
                        )
                    )
                else:
                    self.stderr.write(
                        self.style.ERROR(f"Slack auth test failed: {auth_test}")
                    )
                    return
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error testing Slack connection: {str(e)}")
                )
                return

            # Initialize event handlers
            SlackChatHandler(app)  # This registers the event handlers with the app

            while True:
                try:
                    # Initialize and start Socket Mode Handler
                    self.stdout.write(
                        self.style.SUCCESS("Starting Slack event listener...")
                    )
                    socket_handler = SocketModeHandler(app=app, app_token=app_token)
                    socket_handler.start()  # This will block until the connection is closed

                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"Slack connection error: {str(e)}")
                    )
                    logger.error(f"Slack connection error: {str(e)}")
                    logger.error(traceback.format_exc())
                    logger.info("Waiting 5 seconds before reconnecting...")
                    time.sleep(5)

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Error starting Slack listener: {str(e)}")
            )
            logger.error(f"Slack listener error: {str(e)}")
            logger.error(traceback.format_exc())
            raise


# TODO: add general class for chat
# TODO: verify user's email
