import logging
import os
import time
import traceback
from typing import Optional

from anthropic import AnthropicBedrock
from asgiref.sync import sync_to_async
from chat.models import Chat, ChatMessage
from chat.system_prompt import SYSTEM_PROMPT
from chat.tools import TOOLS
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Starts the Telegram bot for chat integration"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize Anthropic Bedrock client
        aws_access_key = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("BEDROCK_AWS_REGION", "us-west-2")

        self.client = AnthropicBedrock(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
        )

    def _get_or_create_user(self, telegram_user) -> Optional[User]:
        """Get or create a Django user for the Telegram user."""
        try:
            username = f"telegram_{telegram_user.id}"
            email = f"{telegram_user.id}@telegram.user"
            name = telegram_user.full_name or str(telegram_user.id)

            # Try to get existing user by username
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                # Create new user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=name.split()[0] if " " in name else name,
                    last_name=name.split()[-1] if " " in name else "",
                )
                return user
        except Exception as e:
            logger.error(f"Error getting/creating user: {str(e)}")
            return None

    def _get_or_create_chat(self, chat_id: int, message_id: int, user: User) -> Chat:
        """Get or create a chat thread."""
        try:
            # Try to get existing chat
            chat = Chat.objects.filter(
                telegram_chat_id=str(chat_id),
                telegram_message_id=str(message_id),
            ).first()

            if not chat:
                # Create new chat
                chat = Chat.objects.create(
                    user=user,
                    telegram_chat_id=str(chat_id),
                    telegram_message_id=str(message_id),
                )
                logger.info(f"Created new chat with ID: {chat.id}")
            else:
                logger.info(f"Found existing chat with ID: {chat.id}")

            return chat
        except Exception as e:
            logger.error(f"Error getting/creating chat: {str(e)}")
            raise

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

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process both mentions and replies."""
        try:
            message = update.message
            chat_id = message.chat_id
            message_id = message.message_id
            reply_to_message = message.reply_to_message
            user = message.from_user
            text = message.text

            # Skip bot's own messages
            if user.is_bot:
                logger.info("Skipping bot's own message")
                return

            # Log message details
            logger.info("Message details:")
            logger.info(f"- Chat ID: {chat_id}")
            logger.info(f"- Message ID: {message_id}")
            logger.info(f"- Is reply: {bool(reply_to_message)}")
            logger.info(f"- User ID: {user.id}")
            logger.info(f"- Text: {text}")

            try:
                # Run database operations in a thread
                get_or_create_user_async = sync_to_async(self._get_or_create_user)
                django_user = await get_or_create_user_async(user)

                if not django_user:
                    logger.error(
                        f"Could not create/get user for Telegram ID: {user.id}"
                    )
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Sorry, there was an error processing your request.",
                        reply_to_message_id=message_id,
                    )
                    return

                # Get thread message ID
                thread_message_id = (
                    reply_to_message.message_id if reply_to_message else message_id
                )

                # Get or create chat thread
                get_or_create_chat_async = sync_to_async(self._get_or_create_chat)
                chat = await get_or_create_chat_async(
                    chat_id, thread_message_id, django_user
                )
                logger.info(f"Using chat ID: {chat.id}")

                # Create chat message
                create_message_async = sync_to_async(ChatMessage.objects.create)
                message_obj = await create_message_async(
                    chat=chat,
                    user=django_user,
                    message=text,
                    telegram_message_id=str(message_id),
                )
                logger.info(f"Created chat message with ID: {message_obj.id}")

                # Load chat history
                chat_history = []
                get_messages_async = sync_to_async(
                    lambda: list(
                        ChatMessage.objects.filter(chat=chat).order_by("timestamp")
                    )
                )
                messages = await get_messages_async()
                message_count = len(messages)
                logger.info(
                    f"Found {message_count} messages in thread {thread_message_id}"
                )

                # Build chat history
                for i, msg in enumerate(messages, 1):
                    logger.info(f"Message {i}/{message_count}:")
                    logger.info(f"- ID: {msg.id}")
                    logger.info(f"- Text: {msg.message[:100]}")
                    logger.info(f"- Telegram Message ID: {msg.telegram_message_id}")
                    logger.info(f"- Has Response: {bool(msg.response)}")

                    chat_history.append({"role": "user", "content": msg.message})
                    if msg.response:
                        chat_history.append(
                            {"role": "assistant", "content": msg.response}
                        )

                # Process message with Claude
                get_claude_response_async = sync_to_async(self._get_claude_response)
                response = await get_claude_response_async(chat_history)

                if response:
                    logger.info("Got response from Claude, saving to database...")
                    # Save response
                    message_obj.response = response
                    save_async = sync_to_async(message_obj.save)
                    await save_async()
                    logger.info(f"Saved response for message ID: {message_obj.id}")

                    # Send to Telegram
                    logger.info("Sending response to Telegram...")
                    sent_message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=response,
                        reply_to_message_id=message_id,
                    )
                    logger.info("Response sent to Telegram successfully")
                else:
                    logger.error("No response received from Claude")

            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                logger.error(traceback.format_exc())
                # Try to save error state if message exists
                if "message_obj" in locals():
                    try:
                        message_obj.response = f"Error processing message: {str(e)}"
                        save_async = sync_to_async(message_obj.save)
                        await save_async()
                    except Exception as save_error:
                        logger.error(f"Error saving error state: {str(save_error)}")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            logger.error(traceback.format_exc())
            await context.bot.send_message(
                chat_id=chat_id,
                text="Sorry, there was an error processing your request.",
                reply_to_message_id=message_id,
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages that mention the bot or reply to its messages."""
        message = update.message

        # Process if message mentions bot or is a reply to bot's message
        bot_mentioned = False
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    mentioned_text = message.text[
                        entity.offset : entity.offset + entity.length
                    ]
                    if mentioned_text.lower() == f"@{context.bot.username.lower()}":
                        bot_mentioned = True
                        break
        replying_to_bot = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == context.bot.id
        )

        if bot_mentioned or replying_to_bot:
            await self.process_message(update, context)

    def handle(self, *args, **options):
        """Django command handler."""
        try:
            # Log environment variables (without sensitive values)
            self.stdout.write(self.style.SUCCESS("Checking Telegram configuration..."))
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

            if not bot_token:
                self.stderr.write(
                    self.style.ERROR("TELEGRAM_BOT_TOKEN not found in environment")
                )
                return

            self.stdout.write(self.style.SUCCESS("Found required Telegram token"))
            self.stdout.write(
                self.style.SUCCESS(f"Bot token prefix: {bot_token[:10]}...")
            )

            while True:
                try:
                    # Create application and add handlers
                    application = Application.builder().token(bot_token).build()

                    # Add message handler for text messages and commands
                    application.add_handler(
                        MessageHandler(filters.TEXT, self.handle_message)
                    )

                    # Enable logging
                    logging.basicConfig(
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        level=logging.INFO,
                    )

                    self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))
                    # Set shorter polling timeout and enable automatic reconnection
                    application.run_polling(
                        allowed_updates=["message"],
                        poll_interval=1.0,
                        timeout=5,
                        drop_pending_updates=True,  # Don't process old updates on restart
                        close_loop=False,  # Keep the event loop running
                    )
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"Telegram connection error: {str(e)}")
                    )
                    logger.error(f"Telegram connection error: {str(e)}")
                    logger.error(traceback.format_exc())
                    logger.info("Waiting 5 seconds before reconnecting...")
                    time.sleep(5)

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Error starting Telegram bot: {str(e)}")
            )
            logger.error(f"Telegram bot error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
