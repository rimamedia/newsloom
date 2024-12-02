import asyncio
import logging
import random
from typing import List

from django.utils import timezone
from telegram import Bot

TEST_QUOTES: List[str] = [
    "Be yourself; everyone else is already taken. - Oscar Wilde",
    "Two things are infinite: the universe and human stupidity. - Albert Einstein",
    "You only live once, but if you do it right, once is enough. - Mae West",
    "Be the change that you wish to see in the world. - Mahatma Gandhi",
    "The only way to do great work is to love what you do. - Steve Jobs",
]


def test_telegram_channel(stream_id, channel_id, bot_token):
    logger = logging.getLogger(__name__)
    result = {
        "published": False,
        "message": "",
        "timestamp": timezone.now().isoformat(),
        "channel_id": channel_id,
        "test_results": {
            "channel_access": False,
            "message_sent": False,
        },
        "errors": [],
    }

    try:
        bot = Bot(token=bot_token)

        async def send_test_message():
            nonlocal result
            try:
                # Send a random test message
                message = random.choice(TEST_QUOTES)
                await bot.send_message(chat_id=channel_id, text=message)
                result["test_results"]["channel_access"] = True

                logger.info(f"Test message sent to {channel_id}")
                result.update(
                    {
                        "published": True,
                        "message": message,
                    }
                )
                result["test_results"]["message_sent"] = True

            except Exception as e:
                error_msg = f"Failed to send test message: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                raise e
            finally:
                if bot:
                    await bot.close()

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(send_test_message())
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Error in telegram test task: {str(e)}", exc_info=True)
        result["errors"].append(str(e))

    return result
