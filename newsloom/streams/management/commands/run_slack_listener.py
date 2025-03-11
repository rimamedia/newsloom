import json
import logging
import time
import traceback
from functools import wraps

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Import components from chat module
from chat.chat_consumer import ChatConsumer
from chat.message_processor import MessageProcessor
from chat.message_storage import MessageStorage
from chat.models import Chat, ChatMessage

logger = logging.getLogger(__name__)


# Helper function to convert async methods to sync
def async_to_sync_with_args(async_func):
    """
    Convert an async function to a sync function.

    Parameters:
        async_func: The async function to convert

    Returns:
        A synchronous version of the function
    """

    @wraps(async_func)
    def sync_func(*args, **kwargs):
        return async_to_sync(async_func)(*args, **kwargs)

    return sync_func


# Create synchronous versions of async methods
class SyncMessageProcessor:
    """
    Provide synchronous access to MessageProcessor methods.

    This class provides synchronous versions of the async methods in MessageProcessor.
    """

    @staticmethod
    def process_message_core(message, chat, chat_history, client, user):
        """
        Process a message with Claude AI (synchronous version).

        Parameters:
            message: The user message to process
            chat: The chat object
            chat_history: The current chat history
            client: The Anthropic client
            user: The user who sent the message

        Returns:
            tuple: (final_response, chat_message)
        """
        return async_to_sync(MessageProcessor.process_message_core)(
            message, chat, chat_history, client, user
        )


class SyncMessageStorage:
    """
    Provide synchronous access to MessageStorage methods.

    This class provides synchronous versions of the async methods in MessageStorage.
    """

    @staticmethod
    def create_chat(user):
        """
        Create a chat for the given user (synchronous version).

        Parameters:
            user: The user to create the chat for

        Returns:
            Chat: The newly created chat object
        """
        return async_to_sync(MessageStorage.create_chat)(user)

    @staticmethod
    def get_chat(chat_id, user):
        """
        Retrieve a chat by ID for the given user (synchronous version).

        Parameters:
            chat_id: The ID of the chat to retrieve
            user: The user who should own the chat

        Returns:
            Chat or None: The chat object if found, None otherwise
        """
        return async_to_sync(MessageStorage.get_chat)(chat_id, user)

    @staticmethod
    def load_chat_history(chat):
        """
        Load chat history from the database (synchronous version).

        Parameters:
            chat: The chat to load history for

        Returns:
            list: The chat history as a list of message dictionaries
        """
        return async_to_sync(MessageStorage.load_chat_history)(chat)

    @staticmethod
    def save_message(chat, user, message, response=None):
        """
        Save a message and its response to the database (synchronous version).

        Parameters:
            chat: The chat the message belongs to
            user: The user who sent the message
            message: The message text
            response: The AI response text

        Returns:
            ChatMessage: The created message object
        """
        return async_to_sync(MessageStorage.save_message)(chat, user, message, response)

    @staticmethod
    def save_message_details(chat_message, chat, chat_history):
        """
        Save detailed message flow to database (synchronous version).

        Parameters:
            chat_message: The parent message
            chat: The chat the message belongs to
            chat_history: The full conversation history
        """
        return async_to_sync(MessageStorage.save_message_details)(
            chat_message, chat, chat_history
        )


class Command(BaseCommand):
    """
    Start the Slack event listener for chat integration.

    This command initializes the Slack app, sets up event handlers, and starts
    the Socket Mode handler for real-time messaging.
    """

    help = "Starts the Slack event listener for chat integration"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = App(token=settings.SLACK_BOT_TOKEN)

        # Initialize Anthropic Bedrock client using ChatConsumer's method
        self.client = self._initialize_bedrock_client()

        self.setup_event_handlers()

    def _initialize_bedrock_client(self):
        """
        Initialize the Anthropic Bedrock client with credentials from environment.

        Reuse the logic from ChatConsumer._initialize_bedrock_client
        but in a synchronous context.

        Returns:
            AnthropicBedrock: The initialized client
        """
        # Create a temporary ChatConsumer instance
        consumer = ChatConsumer()

        # Call the async method in a synchronous context
        try:
            async_to_sync(consumer._initialize_bedrock_client)()
            # Return the initialized client
            return consumer.client
        except Exception as e:
            error_msg = f"Failed to initialize Bedrock client: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise

    def setup_event_handlers(self):
        """Set up Slack event handlers for mentions and thread replies."""

        def process_message(event, say, is_mention=True):
            """Process both mentions and thread replies."""
            try:
                # Log incoming event
                event_type = "mention" if is_mention else "thread reply"
                logger.info(
                    f"Received {event_type} event: {json.dumps(event, indent=2)}"
                )

                # Extract relevant information
                channel_id = event.get("channel")
                current_ts = event.get("ts")  # Current message timestamp
                # If in thread, use thread's ts
                thread_ts = event.get("thread_ts", current_ts)
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

                # Get or create Django user for the Slack user
                user = self._get_or_create_user(user_id)
                if not user:
                    logger.error(f"Could not create/get user for Slack ID: {user_id}")
                    say(
                        text="Sorry, there was an error processing your request.",
                        thread_ts=thread_ts,
                    )
                    return

                # Get or create chat thread
                chat = self._get_or_create_chat(channel_id, thread_ts, user)
                logger.info(f"Using chat ID: {chat.id}")

                try:
                    # Create chat message with Slack timestamp
                    message = ChatMessage.objects.create(
                        chat=chat,
                        user=user,
                        message=text,
                        slack_ts=current_ts,
                    )
                    logger.info(f"Created chat message with ID: {message.id}")

                    # Load chat history using MessageStorage
                    chat_history = SyncMessageStorage.load_chat_history(chat)
                    message_count = len(chat_history) // 2 + 1  # Approximate count
                    logger.info(f"Found {message_count} messages in thread {thread_ts}")

                    # Process message with MessageProcessor
                    logger.info("Processing message with Claude...")
                    response, updated_message = (
                        SyncMessageProcessor.process_message_core(
                            text, chat, chat_history, self.client, user
                        )
                    )

                    if response:
                        logger.info("Got response from Claude, saving to database...")
                        # The response is already saved by MessageProcessor, but we need to update
                        # the slack_ts field which is specific to this integration
                        if updated_message.id != message.id:
                            # If MessageProcessor created a new message, update our reference
                            message = updated_message
                            # Ensure slack_ts is set
                            message.slack_ts = current_ts
                            message.save()

                        logger.info(f"Saved response for message ID: {message.id}")

                        # Then send to Slack
                        logger.info("Sending response to Slack...")
                        say(text=response, thread_ts=thread_ts)
                        logger.info("Response sent to Slack successfully")
                    else:
                        logger.error("No response received from Claude")

                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    logger.error(traceback.format_exc())
                    # Try to save error state if message exists
                    if "message" in locals():
                        try:
                            message.response = f"Error processing message: {str(e)}"
                            message.save()
                        except Exception as save_error:
                            logger.error(f"Error saving error state: {str(save_error)}")

            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")
                logger.error(traceback.format_exc())
                say(
                    text="Sorry, there was an error processing your request.",
                    thread_ts=thread_ts,
                )

        @self.app.event("app_mention")
        def handle_mention(event, say):
            """Handle direct mentions of the bot."""
            process_message(event, say, is_mention=True)

        @self.app.event("message")
        def handle_message(event, say):
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
                    process_message(event, say, is_mention=False)
                else:
                    logger.info("Ignoring thread reply in unknown chat")

    def _get_or_create_user(self, slack_user_id):
        """
        Get or create a Django user for the Slack user.

        Parameters:
            slack_user_id: The Slack user ID

        Returns:
            User: The Django user
        """
        try:
            # Get user info from Slack
            user_info = self.app.client.users_info(user=slack_user_id)
            if user_info["ok"]:
                slack_user = user_info["user"]
                email = slack_user.get("profile", {}).get(
                    "email", f"{slack_user_id}@slack.user"
                )
                name = slack_user.get("real_name", slack_user_id)

                # Try to get existing user by email
                try:
                    return User.objects.get(email=email)
                except User.DoesNotExist:
                    # Create new user
                    username = f"slack_{slack_user_id}"
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=name.split()[0] if " " in name else name,
                        last_name=name.split()[-1] if " " in name else "",
                    )
                    return user
            return None
        except Exception as e:
            logger.error(f"Error getting/creating user: {str(e)}")
            return None

    def _get_or_create_chat(self, channel_id, thread_ts, user):
        """
        Get or create a chat thread.

        Parameters:
            channel_id: The Slack channel ID
            thread_ts: The Slack thread timestamp
            user: The Django user

        Returns:
            Chat: The chat object
        """
        try:
            # Try to get existing chat
            chat = Chat.objects.filter(
                slack_channel_id=channel_id, slack_thread_ts=thread_ts
            ).first()

            if not chat:
                # Create new chat
                chat = Chat.objects.create(
                    user=user, slack_channel_id=channel_id, slack_thread_ts=thread_ts
                )
                logger.info(f"Created new chat with ID: {chat.id}")
            else:
                logger.info(f"Found existing chat with ID: {chat.id}")

            return chat
        except Exception as e:
            logger.error(f"Error getting/creating chat: {str(e)}")
            raise

    def handle(self, *args, **options):
        """Django command handler."""
        try:
            # Log environment variables (without sensitive values)
            self.stdout.write(self.style.SUCCESS("Checking Slack configuration..."))

            if not settings.SLACK_BOT_TOKEN:
                self.stderr.write(
                    self.style.ERROR("SLACK_BOT_TOKEN not found in environment")
                )
                return
            if not settings.SLACK_APP_TOKEN:
                self.stderr.write(
                    self.style.ERROR("SLACK_APP_TOKEN not found in environment")
                )
                return

            self.stdout.write(self.style.SUCCESS("Found required Slack tokens"))
            self.stdout.write(
                self.style.SUCCESS(f"Bot token prefix: {settings.SLACK_BOT_TOKEN[:10]}...")
            )
            self.stdout.write(
                self.style.SUCCESS(f"App token prefix: {settings.SLACK_APP_TOKEN[:10]}...")
            )

            # Test Slack API connection
            self.stdout.write(self.style.SUCCESS("Testing Slack API connection..."))
            try:
                auth_test = self.app.client.auth_test()
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

            while True:
                try:
                    # Initialize and start Socket Mode Handler
                    self.stdout.write(
                        self.style.SUCCESS("Starting Slack event listener...")
                    )
                    handler = SocketModeHandler(app=self.app, app_token=app_token)
                    handler.start()

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
