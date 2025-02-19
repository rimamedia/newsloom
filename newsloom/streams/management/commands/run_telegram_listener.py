import logging
import os
import time
import traceback

from chat.services.base_handler import BaseChatHandler
from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)


class TelegramChatHandler(BaseChatHandler):
    """Telegram-specific implementation of the chat handler."""

    def __init__(self):
        super().__init__()

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
                # Get or create Django user
                django_user = await self.user_service.get_or_create_user(
                    "telegram",
                    {
                        "id": user.id,
                        "name": user.full_name or str(user.id),
                    },
                )

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
                chat = await self.user_service.get_or_create_chat(
                    "telegram",
                    django_user,
                    {"chat_id": chat_id, "message_id": thread_message_id},
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
                        platform_data={"telegram_message_id": str(message_id)},
                    )
                    logger.info("Message saved successfully")

                    # Send to Telegram
                    logger.info("Sending response to Telegram...")
                    await context.bot.send_message(
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
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Sorry, there was an error processing your request.",
                    reply_to_message_id=message_id,
                )

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            logger.error(traceback.format_exc())
            if "chat_id" in locals() and "message_id" in locals():
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


class Command(BaseCommand):
    """Django management command to run the Telegram bot."""

    help = "Starts the Telegram bot for chat integration"

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

            # Initialize handler
            handler = TelegramChatHandler()

            while True:
                try:
                    # Create application and add handlers
                    application = Application.builder().token(bot_token).build()
                    application.add_handler(
                        MessageHandler(filters.TEXT, handler.handle_message)
                    )

                    # Enable logging
                    logging.basicConfig(
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        level=logging.INFO,
                    )

                    self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))
                    application.run_polling(
                        allowed_updates=["message"],
                        poll_interval=1.0,
                        timeout=5,
                        drop_pending_updates=True,
                        close_loop=False,
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
