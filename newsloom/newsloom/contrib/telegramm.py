import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

def send_message_to_telegram(api_key: str, chat_id: str, message: str) -> Optional[int]:
    if not (api_key and chat_id):
        return None
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': "HTML",
    }
    message_id = None
    try:
        response = requests.post(f'https://api.telegram.org/bot{api_key}/sendMessage', data=data, verify=False)
    except requests.RequestException as e:
        logger.exception(e)
    else:
        if response.status_code == requests.codes.ok:
            try:
                message_id = response.json()['result']['message_id']
            except Exception as e:
                logger.exception(e)
        else:
            logger.error('Invalid response code from telegram')
    return message_id
