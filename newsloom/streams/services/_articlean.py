import json
import logging
from typing import Any, Dict

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from dotenv import load_dotenv
from sources.models import News
from streams.models import Stream

# Load environment variables
load_dotenv()


logger = logging.getLogger(__name__)


def articlean(stream: Stream, **kwargs) -> Dict[str, Any]:
    """Process articles through the Articlean service.

    Args:
        Stream: stream being executed
        **kwargs: Additional keyword arguments that will be ignored

    Returns:
        Dict containing execution statistics

    Raises:
        EnvironmentError: If required environment variables are not set
    """
    # Check required environment variables

    # Build query for unprocessed articles from this source
    condition = Q(text__isnull=True) | Q(text="")
    if stream.source:
        condition &= Q(source=stream.source)

    # Get articles that need processing
    articles = News.objects.filter(condition)

    processed_count = 0
    failed_count = 0

    # Process each article
    for article in articles:
        try:
            logger.info(f"Processing article ID {article.id} with URL: {article.link}")

            payload = json.dumps({"url": article.link})
            headers = {
                "x-api-key": settings.ARTICLEAN_API_KEY,
                "Content-Type": "application/json",
            }
            logger.info(f"Making request to Articlean API with payload: {payload}")


            logger.info(f"Sending request to: {settings.ARTICLEAN_API_URL}")

            # Send request
            response = requests.post(
                settings.ARTICLEAN_API_URL,
                headers=headers,
                data=payload,
                timeout=30,  # Add 30 second timeout to prevent hanging
            )

            logger.info(f"Received response with status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            if response.status_code != 200:
                logger.error(f"Process URL failed with status {response.status_code}")
                logger.error(f"Response content: {response.text}")
                logger.error(f"Request URL: {settings.ARTICLEAN_API_URL}")
                logger.error(f"Request headers: {headers}")
                response.raise_for_status()

            # Parse response
            try:
                data = response.json()
                logger.debug(f"Parsed response data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Raw response content: {response.text}")
                failed_count += 1
                continue

            if not data.get("result", {}).get("is_success"):
                error_msg = data.get("result", {}).get("error", "Unknown error")
                logger.error(
                    f"Articlean processing failed for article {article.id}:\n"
                    f"URL: {article.link}\n"
                    f"Error: {error_msg}\n"
                    f"Full response: {data}"
                )
                failed_count += 1
                continue

            result = data["result"]
            logger.info(f"Successfully parsed article {article.id} data from Articlean")
            logger.debug(
                f"Article data: Title length: {len(result.get('title', ''))}, "
                f"Text length: {len(result.get('plain_text', ''))}"
            )

            # Update article with received data
            try:
                with transaction.atomic():
                    article.title = result.get("title", article.title)
                    article.text = result.get("plain_text", "")
                    article.save()
                    processed_count += 1
                    logger.info(
                        f"Successfully updated article {article.id} in database"
                    )
            except Exception as e:
                logger.error(f"Database error updating article {article.id}: {str(e)}")
                failed_count += 1

        except requests.RequestException as e:
            logger.error(
                f"Network error processing article {article.id}:\n"
                f"URL: {article.link}\n"
                f"Error: {str(e)}"
            )
            failed_count += 1
        except Exception as e:
            logger.exception(
                f"Unexpected error processing article {article.id}:\n"
                f"URL: {article.link}\n"
                f"Error: {str(e)}"
            )
            failed_count += 1

    return {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "total_count": processed_count + failed_count,
    }
