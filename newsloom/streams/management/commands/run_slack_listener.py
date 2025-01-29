import json
import logging
import os
import time
import traceback

from anthropic import AnthropicBedrock
from chat.models import Chat, ChatMessage
from chat.system_prompt import SYSTEM_PROMPT
from chat.tools import TOOLS
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Starts the Slack event listener for chat integration"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

        # Initialize Anthropic Bedrock client
        aws_access_key = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("BEDROCK_AWS_REGION", "us-west-2")

        self.client = AnthropicBedrock(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
        )

        self.setup_event_handlers()

    def setup_event_handlers(self):
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
                    # Create chat message first
                    message = ChatMessage.objects.create(
                        chat=chat,
                        user=user,
                        message=text,
                        slack_ts=current_ts,  # Store current message timestamp
                    )
                    logger.info(f"Created chat message with ID: {message.id}")

                    # Load chat history
                    chat_history = []
                    messages = ChatMessage.objects.filter(chat=chat).order_by(
                        "timestamp"
                    )
                    message_count = messages.count()
                    logger.info(f"Found {message_count} messages in thread {thread_ts}")

                    # Debug log all messages in thread
                    for i, msg in enumerate(messages, 1):
                        logger.info(f"Message {i}/{message_count}:")
                        logger.info(f"- ID: {msg.id}")
                        logger.info(f"- Text: {msg.message[:100]}")
                        logger.info(f"- Slack TS: {msg.slack_ts}")
                        logger.info(f"- Has Response: {bool(msg.response)}")

                        chat_history.append({"role": "user", "content": msg.message})
                        if msg.response:
                            chat_history.append(
                                {"role": "assistant", "content": msg.response}
                            )

                    # Process message
                    logger.info("Processing message with Claude...")
                    response = self._get_claude_response(chat_history)

                    if response:
                        logger.info("Got response from Claude, saving to database...")
                        # Save response to database first
                        message.response = response
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

    def _get_claude_response(self, chat_history):
        """Get response from Claude with tool handling."""
        try:
            while True:
                # Get response from Claude
                response = self.client.messages.create(
                    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    max_tokens=8192,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=chat_history,
                )

                # Check if response contains tool calls
                if response.stop_reason == "tool_use":
                    logger.info("Tool use detected in response")

                    # Add assistant's response to history
                    chat_history.append(
                        {
                            "role": "assistant",
                            "content": [
                                content.model_dump() for content in response.content
                            ],
                        }
                    )

                    for content in response.content:
                        if content.type == "tool_use":
                            # Extract tool details
                            tool_name = content.name
                            tool_input = content.input
                            tool_id = content.id

                            logger.info(f"Executing tool: {tool_name}")
                            logger.info(f"Tool input: {tool_input}")

                            # Execute the tool
                            try:
                                from chat import tool_functions

                                tool_func = getattr(tool_functions, tool_name)
                                tool_result = tool_func(**tool_input)
                                logger.info(
                                    f"Tool execution successful. Result: {tool_result}"
                                )

                                # Add tool result to history
                                chat_history.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": tool_id,
                                                "content": str(tool_result),
                                            }
                                        ],
                                    }
                                )

                            except Exception as e:
                                logger.error(f"Tool execution failed: {str(e)}")
                                # Add error result to history
                                chat_history.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": tool_id,
                                                "content": str(e),
                                                "is_error": True,
                                            }
                                        ],
                                    }
                                )

                    logger.info("Continuing conversation with tool results")
                    continue  # Continue the conversation with tool results

                # If no tool calls, add response to history and return
                logger.info("No tool calls in response, returning final text")
                final_response = response.content[0].text
                chat_history.append({"role": "assistant", "content": final_response})
                return final_response

        except Exception as e:
            logger.error(f"Error getting Claude response: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error getting response: {str(e)}"

    def _get_or_create_user(self, slack_user_id):
        """Get or create a Django user for the Slack user."""
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
        """Get or create a chat thread."""
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
