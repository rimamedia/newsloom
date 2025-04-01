"""
Utility module for parsing links using the Articlean service.

This module provides functions to parse web links using the Articlean service,
which can be used by any task that saves web links to enrich the data.
"""

import json
import logging
import os
from typing import Any, Dict

import requests
from django.db import transaction
from dotenv import load_dotenv
from sources.models import News

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_articlean_credentials() -> Dict[str, str]:
    """
    Get Articlean API credentials from environment variables.

    Returns:
        Dict containing API key and URL

    Raises:
        EnvironmentError: If required environment variables are not set
    """
    required_vars = ["ARTICLEAN_API_KEY", "ARTICLEAN_API_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise EnvironmentError(error_msg)

    return {
        "api_key": os.getenv("ARTICLEAN_API_KEY"),
        "api_url": os.getenv("ARTICLEAN_API_URL"),
    }


def parse_link(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Parse a link using the Articlean service.

    Args:
        url: The URL to parse
        timeout: Request timeout in seconds

    Returns:
        Dict containing the parsed data or error information

    Example:
        result = parse_link("https://example.com/article")
        if result["success"]:
            title = result["data"]["title"]
            text = result["data"]["plain_text"]
    """
    try:
        credentials = get_articlean_credentials()

        payload = json.dumps({"url": url})
        headers = {
            "x-api-key": credentials["api_key"],
            "Content-Type": "application/json",
        }

        api_url = f"{credentials['api_url']}/process-url"
        logger.info(f"Sending request to Articlean API for URL: {url}")

        response = requests.post(
            api_url,
            headers=headers,
            data=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            logger.error(f"Process URL failed with status {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return {
                "success": False,
                "error": f"API request failed with status code {response.status_code}",
                "status_code": response.status_code,
                "response": response.text,
            }

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            logger.error(f"Raw response content: {response.text}")
            return {
                "success": False,
                "error": f"Failed to parse JSON response: {str(e)}",
                "response": response.text,
            }

        if not data.get("result", {}).get("is_success"):
            error_msg = data.get("result", {}).get("error", "Unknown error")
            logger.error(f"Articlean processing failed: {error_msg}")
            return {"success": False, "error": error_msg, "data": data}

        return {"success": True, "data": data["result"]}

    except requests.RequestException as e:
        logger.error(f"Network error processing URL {url}: {str(e)}")
        return {"success": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Unexpected error processing URL {url}: {str(e)}")
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def update_news_with_articlean_data(news: News, articlean_data: Dict[str, Any]) -> bool:
    """
    Update a News object with data from Articlean.

    Args:
        news: The News object to update
        articlean_data: The data returned from Articlean

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        with transaction.atomic():
            if "title" in articlean_data and articlean_data["title"]:
                news.title = articlean_data["title"]

            if "plain_text" in articlean_data and articlean_data["plain_text"]:
                news.text = articlean_data["plain_text"]

            news.save()
            logger.info(f"Successfully updated news {news.id} with Articlean data")
            return True
    except Exception as e:
        logger.error(f"Database error updating news {news.id}: {str(e)}")
        return False


def process_and_update_news(news: News) -> Dict[str, Any]:
    """
    Process a News object's link with Articlean and update the object.

    Args:
        news: The News object to process and update

    Returns:
        Dict containing the result of the operation
    """
    if not news.link:
        return {
            "success": False,
            "error": "News object has no link",
            "news_id": news.id,
        }

    result = parse_link(news.link)

    if not result["success"]:
        return {"success": False, "error": result["error"], "news_id": news.id}

    update_success = update_news_with_articlean_data(news, result["data"])

    if not update_success:
        return {
            "success": False,
            "error": "Failed to update news with Articlean data",
            "news_id": news.id,
        }

    return {"success": True, "news_id": news.id, "data": result["data"]}


def enrich_link_data(
    link_data: Dict[str, Any], parse_now: bool = True
) -> Dict[str, Any]:
    """
    Enrich link data with Articlean content.

    This function can be used by tasks that collect links before saving them
    to the database, to enrich the link data with content from Articlean.

    Args:
        link_data: Dictionary containing at least a 'url' key
        parse_now: Whether to parse the link immediately or just prepare the data

    Returns:
        Dict containing the original link_data enriched with Articlean data
    """
    if "url" not in link_data:
        logger.error("Link data missing 'url' key")
        return link_data

    if not parse_now:
        # Just mark the link for later processing
        link_data["needs_articlean_processing"] = True
        return link_data

    result = parse_link(link_data["url"])

    if not result["success"]:
        logger.warning(f"Failed to enrich link with Articlean: {result['error']}")
        return link_data

    # Enrich the link data with Articlean content
    if "title" in result["data"] and result["data"]["title"]:
        link_data["title"] = result["data"]["title"]

    if "plain_text" in result["data"] and result["data"]["plain_text"]:
        link_data["text"] = result["data"]["plain_text"]

    # Add other Articlean data that might be useful
    link_data["articlean_data"] = result["data"]

    return link_data
