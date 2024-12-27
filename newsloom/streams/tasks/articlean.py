import json
import logging
from typing import Any, Dict

import requests
from django.db import transaction
from django.db.models import Q
from sources.models import News
from streams.models import Stream

logger = logging.getLogger(__name__)


def articlean(stream_id: int, endpoint: str, token: str) -> Dict[str, Any]:
    """Process articles through the Articlean service.

    Args:
        stream_id: ID of the stream being executed
        endpoint: Articlean service endpoint
        token: Authentication token

    Returns:
        Dict containing execution statistics
    """
    # Get stream to access its source
    stream = Stream.objects.get(id=stream_id)

    # Build query for unprocessed articles from this source
    query = Q(text__isnull=True) | Q(text="")
    if stream.source:
        query &= Q(source=stream.source)

    # Get articles that need processing
    articles = News.objects.filter(query)

    processed_count = 0
    failed_count = 0

    # Process each article
    for article in articles:
        try:
            # Prepare request
            payload = json.dumps({"url": article.link})
            headers = {"x-api-key": token, "Content-Type": "application/json"}

            # Send request
            response = requests.request("POST", endpoint, headers=headers, data=payload)
            response.raise_for_status()

            # Parse response
            data = response.json()

            if not data.get("result", {}).get("is_success"):
                logger.error(
                    f"Articlean processing failed for {article.link}: "
                    f"{data.get('result', {}).get('error')}"
                )
                failed_count += 1
                continue

            result = data["result"]

            # Update article with received data
            with transaction.atomic():
                article.title = result.get("title", article.title)
                article.text = result.get("plain_text", "")
                article.save()
                processed_count += 1

        except Exception as e:
            logger.exception(f"Failed to process article {article.link}: {str(e)}")
            failed_count += 1

    return {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "total_count": processed_count + failed_count,
    }
