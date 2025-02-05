"""News stream processing using Anthropic's Claude model via Amazon Bedrock."""

import json
import logging
import os
from datetime import timedelta
from typing import Dict, List, Optional

from agents.models import Agent
from anthropic import AnthropicBedrock
from django.conf import settings
from django.db import connection
from django.utils import timezone
from dotenv import load_dotenv
from mediamanager.models import Examples
from sources.models import Doc, News
from streams.models import Stream
from streams.tools.news_tools import NEWS_PROCESSING_TOOLS
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

load_dotenv()


class BedrockProcessor:
    """Handles interactions with Amazon Bedrock using the Anthropic SDK."""

    def __init__(self):
        """Initialize the Bedrock processor with AWS credentials."""
        self.client = AnthropicBedrock(
            aws_access_key=os.getenv("BEDROCK_AWS_ACCESS_KEY_ID"),
            aws_secret_key=os.getenv("BEDROCK_AWS_SECRET_ACCESS_KEY"),
            aws_region=os.getenv("BEDROCK_AWS_REGION", "us-east-1"),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def process_content(
        self, system_prompt: str, user_prompt: str, stream: Optional[Stream] = None
    ) -> Dict:
        """
        Process content using Claude model with retry support.

        Args:
            system_prompt: The system prompt that defines behavior
            user_prompt: The user prompt with content to process
            stream: Optional Stream object for document creation

        Returns:
            Dict containing the model's response and processing results
        """
        try:
            response = self.client.messages.create(
                model="anthropic.claude-3-5-sonnet-20241022-v2:0",
                max_tokens=8192,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                tools=NEWS_PROCESSING_TOOLS,
            )

            logger.info(
                "Received response from Bedrock: %s",
                json.dumps(response.model_dump(), indent=2),
            )

            # Initialize message history with the initial exchange
            messages = [
                {"role": "user", "content": user_prompt},
                {
                    "role": "assistant",
                    "content": [content.model_dump() for content in response.content],
                },
            ]

            # Process tool calls if present
            saved_count = 0
            if response.stop_reason == "tool_use":
                for content in response.content:
                    if (
                        content.type == "tool_use"
                        and content.name == "create_documents"
                    ):
                        tool_result = self._handle_document_creation(
                            content.input, stream
                        )
                        saved_count = tool_result.get("saved_count", 0)

                        # Add tool result to message history
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content.id,
                                        "content": json.dumps(tool_result),
                                    }
                                ],
                            }
                        )

            # Get final text content
            final_text = ""
            for content in response.content:
                if content.type == "text":
                    final_text += content.text

            return {
                "completion": final_text.strip(),
                "full_response": response.model_dump(),
                "message_history": messages,
                "saved_count": saved_count,
            }

        except Exception as e:
            logger.error("Error in process_content: %s", str(e), exc_info=True)
            raise ValueError(f"Failed to process content: {str(e)}")

    def _handle_document_creation(
        self, tool_input: Dict, stream: Optional[Stream]
    ) -> Dict:
        """Handle document creation from tool input."""
        try:
            if stream is None:
                raise ValueError("Stream object is required for saving documents")

            documents = tool_input.get("documents", [])
            topic = tool_input.get("topic", "Untitled")
            saved_count = 0

            # Create documents in database
            for document in documents:
                doc = Doc.objects.create(
                    media=stream.media,
                    link=document.get("url", ""),
                    title=topic,
                    text=document.get("text", ""),
                    status="new",
                )
                saved_count += 1
                logger.info("Created doc %d", doc.id)

            return {
                "success": True,
                "message": f"Successfully saved {saved_count} documents",
                "saved_count": saved_count,
            }

        except Exception as e:
            error_msg = f"Error saving documents: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "saved_count": 0}


class NewsStreamProcessor:
    """Handles the processing of news streams."""

    def __init__(self, stream_id: int, agent_id: int):
        """Initialize the news stream processor."""
        self.stream_id = stream_id
        self.agent_id = agent_id
        self.bedrock = BedrockProcessor()

    def process(self, time_window_minutes: int = 60, max_items: int = 100) -> Dict:
        """
        Process news items using the specified agent.

        Args:
            time_window_minutes: Time window in minutes to look back for news
            max_items: Maximum number of news items to process

        Returns:
            Dict containing processing results
        """
        try:
            # Get stream and agent
            stream = Stream.objects.get(id=self.stream_id)
            agent = Agent.objects.get(id=self.agent_id)

            # Validate agent
            if not agent.is_active:
                raise ValueError(f"Agent {self.agent_id} is not active")
            if agent.provider.lower() != "bedrock":
                raise ValueError("Only Bedrock provider is currently supported")

            # Verify timezone settings
            self._verify_timezone_settings()

            # Get news items
            news_items = self._get_news_items(stream, time_window_minutes, max_items)
            if not news_items:
                return self._empty_result(time_window_minutes)

            # Get examples and prepare content
            examples = Examples.objects.filter(media=stream.media)
            examples_text = "\n\n".join(example.text for example in examples)

            # Format news content
            news_content = self._format_news_content(news_items)

            # Prepare template variables
            template_vars = {
                "news": news_content,
                "examples": examples_text,
                "example": examples_text,  # Backward compatibility
                "now": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            }

            # Format prompts
            system_prompt = agent.system_prompt.format(**template_vars)
            user_prompt = agent.user_prompt_template.format(**template_vars)

            # Process content
            response = self.bedrock.process_content(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                stream=stream,
            )

            return {
                "processed": len(news_items),
                "saved": response.get("saved_count", 0),
                "error": None,
                "bedrock_response": {
                    "full_response": response.get("full_response"),
                    "message_history": response.get("message_history", []),
                },
            }

        except Exception as e:
            error_msg = f"Error in news stream task: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "processed": 0,
                "saved": 0,
                "error": error_msg,
                "bedrock_response": {"full_response": None, "message_history": []},
            }

    def _verify_timezone_settings(self):
        """Verify timezone settings are properly configured."""
        if not settings.USE_TZ:
            raise ValueError("Django timezone support must be enabled")

        if settings.TIME_ZONE != "UTC":
            logger.warning("Django TIME_ZONE is not UTC: %s", settings.TIME_ZONE)

        # Check database timezone
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SHOW timezone;")
                db_timezone = cursor.fetchone()[0]
                if db_timezone != "UTC":
                    raise ValueError("Database timezone must be UTC")
        elif connection.vendor == "sqlite":
            logger.info("Using SQLite - ensuring all datetime operations use UTC")

    def _get_news_items(
        self, stream: Stream, time_window_minutes: int, max_items: int
    ) -> List[News]:
        """Get recent news items for processing."""
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        return list(
            News.objects.filter(
                source__in=stream.media.sources.all(),
                created_at__gte=time_threshold,
            ).order_by("-created_at")[:max_items]
        )

    def _format_news_content(self, news_items: List[News]) -> str:
        """Format news items into a single string."""
        return "\n\n---\n\n".join(
            f"Title: {news.title}\n\nContent: {news.text}\n\nURL: {news.link}"
            for news in news_items
        )

    def _empty_result(self, time_window_minutes: int) -> Dict:
        """Return result for when no news items are found."""
        return {
            "processed": 0,
            "saved": 0,
            "error": f"No news items found in the last {time_window_minutes} minutes",
            "bedrock_response": {"full_response": None, "message_history": []},
        }


def process_news_stream(
    stream_id: int,
    agent_id: int,
    time_window_minutes: int = 60,
    max_items: int = 100,
    save_to_docs: bool = True,
    **kwargs,
) -> Dict:
    """
    Process news items using the specified agent.

    This is the main entry point for news stream processing.

    Args:
        stream_id: ID of the stream
        agent_id: ID of the agent to use
        time_window_minutes: Time window in minutes to look back for news
        max_items: Maximum number of news items to process
        save_to_docs: Whether to save the processed output to docs

    Returns:
        Dict containing processing results
    """
    processor = NewsStreamProcessor(stream_id=stream_id, agent_id=agent_id)
    return processor.process(
        time_window_minutes=time_window_minutes,
        max_items=max_items,
    )
