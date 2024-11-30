import asyncio
import json
import logging
import random
from typing import List

import luigi
from django.utils import timezone
from telegram import Bot


class TelegramTestTask(luigi.Task):
    stream_id = luigi.IntParameter()
    channel_id = luigi.Parameter()
    bot_token = luigi.Parameter()
    scheduled_time = luigi.Parameter()

    # Some sample quotes for testing
    TEST_QUOTES: List[str] = [
        "Be yourself; everyone else is already taken. - Oscar Wilde",
        "Two things are infinite: the universe and human stupidity. - Albert Einstein",
        "You only live once, but if you do it right, once is enough. - Mae West",
        "Be the change that you wish to see in the world. - Mahatma Gandhi",
        "The only way to do great work is to love what you do. - Steve Jobs",
    ]

    @classmethod
    def get_config_example(cls):
        return {
            "channel_id": "-100123456789",
            "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        }

    def run(self):
        logger = logging.getLogger(__name__)
        output_data = {
            "published": False,
            "message": "",
            "timestamp": timezone.now().isoformat(),
            "channel_id": self.channel_id,
            "test_results": {
                "channel_access": False,
                "message_sent": False,
                "bot_connection": False,
            },
            "execution_time": None,
            "selected_quote": None,
        }

        start_time = timezone.now()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def send_test_message():
                bot = None
                try:
                    # Test bot connection
                    bot = Bot(token=self.bot_token)
                    output_data["test_results"]["bot_connection"] = True

                    # Test channel access
                    await bot.get_chat(self.channel_id)
                    output_data["test_results"]["channel_access"] = True

                    # Select and send quote
                    quote = random.choice(self.TEST_QUOTES)
                    output_data["selected_quote"] = quote
                    message = f"🔔 Test Message\n\n{quote}"

                    await bot.send_message(
                        chat_id=self.channel_id,
                        text=message,
                        disable_web_page_preview=True,
                    )

                    logger.info(f"Test message sent to {self.channel_id}")
                    output_data.update(
                        {
                            "published": True,
                            "message": message,
                        }
                    )
                    output_data["test_results"]["message_sent"] = True

                except Exception as e:
                    error_msg = f"Failed to send test message: {str(e)}"
                    logger.error(error_msg)
                    output_data["error"] = error_msg
                    output_data["error_details"] = {
                        "type": type(e).__name__,
                        "message": str(e),
                    }
                    raise e
                finally:
                    if bot:
                        await bot.close()

            try:
                loop.run_until_complete(send_test_message())
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error in telegram test task: {str(e)}", exc_info=True)
            output_data["error"] = str(e)
        finally:
            # Calculate execution time
            end_time = timezone.now()
            output_data["execution_time"] = (end_time - start_time).total_seconds()

            # Write output to file
            with self.output().open("w") as f:
                json.dump(output_data, f, indent=2)

    def output(self):
        return luigi.LocalTarget(f"logs/telegram_test_{self.scheduled_time}.txt")
