"""Tests for news stream processing."""

import logging
from unittest.mock import MagicMock, patch

from agents.models import Agent
from django.test import TestCase
from django.utils import timezone
from mediamanager.models import Examples, Media
from sources.models import News, Source
from streams.models import Stream
from streams.tasks.news_stream import (
    BedrockProcessor,
    NewsStreamProcessor,
    process_news_stream,
)

logger = logging.getLogger(__name__)


class TestNewsStream(TestCase):
    """Test cases for news stream processing."""

    def setUp(self):
        """Set up test environment."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "BEDROCK_AWS_ACCESS_KEY_ID": "test-key",
                "BEDROCK_AWS_SECRET_ACCESS_KEY": "test-secret",
                "BEDROCK_AWS_REGION": "us-east-1",
            },
        )
        self.env_patcher.start()

        # Create test data
        self.media = Media.objects.create(name="Test Media")
        self.source = Source.objects.create(
            name="Test Source",
            link="http://test.com",
            type="web",
        )
        self.media.sources.add(self.source)

        # Create example
        self.example = Examples.objects.create(media=self.media, text="Example content")

        # Create news item
        self.news = News.objects.create(
            title="Test News",
            text="Test content",
            link="http://test.com",
            created_at=timezone.now(),
            source=self.source,
        )
        # Create stream with valid configuration
        self.stream = Stream.objects.create(
            name="Test Stream",
            stream_type="news_stream",
            frequency="daily",
            configuration={
                "agent_id": 1,  # Will be updated after agent creation
                "time_window_minutes": 60,
                "max_items": 100,
                "save_to_docs": True,
            },
            status="active",
            media=self.media,  # Link to media
        )
        # Create agent and update stream configuration
        self.agent = Agent.objects.create(
            name="Test Agent",
            provider="bedrock",
            system_prompt="Test system prompt",
            user_prompt_template="Test template with {news}",
            is_active=True,
        )
        self.stream.configuration["agent_id"] = self.agent.id
        self.stream.save()

    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()

    @patch("streams.tasks.news_stream.AnthropicBedrock")
    def test_bedrock_processor_success(self, mock_anthropic):
        """Test successful content processing with BedrockProcessor."""
        # Mock Anthropic response
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock()]
        mock_response.content[0].type = "text"
        mock_response.content[0].text = "Test response"
        mock_response.model_dump.return_value = {
            "content": [{"type": "text", "text": "Test response"}]
        }

        # Set up mock client
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # Test processor
        processor = BedrockProcessor()
        result = processor.process_content(
            system_prompt="Test system prompt",
            user_prompt="Test user prompt",
        )

        # Verify results
        self.assertEqual(result["completion"], "Test response")
        self.assertEqual(result["saved_count"], 0)
        mock_client.messages.create.assert_called_once()

    @patch("streams.tasks.news_stream.BedrockProcessor")
    def test_news_stream_processor_success(self, mock_bedrock_cls):
        """Test successful news stream processing."""
        # Mock BedrockProcessor
        mock_bedrock = MagicMock()
        mock_bedrock.process_content.return_value = {
            "completion": "Test completion",
            "full_response": {"test": "response"},
            "message_history": [],
            "saved_count": 1,
        }
        mock_bedrock_cls.return_value = mock_bedrock

        # Test processor
        processor = NewsStreamProcessor(
            stream_id=self.stream.id, agent_id=self.agent.id
        )
        result = processor.process()

        # Verify results
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["saved"], 1)
        self.assertIsNone(result["error"])
        mock_bedrock.process_content.assert_called_once()

    def test_news_stream_processor_invalid_agent(self):
        """Test processing with invalid agent."""
        # Create inactive agent
        inactive_agent = Agent.objects.create(
            name="Inactive Agent",
            provider="bedrock",
            system_prompt="Test system prompt",
            user_prompt_template="Test template with {news}",
            is_active=False,
        )

        # Test processor with inactive agent
        processor = NewsStreamProcessor(
            stream_id=self.stream.id, agent_id=inactive_agent.id
        )
        result = processor.process()

        # Verify error handling
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["saved"], 0)

    def test_news_stream_processor_no_news(self):
        """Test processing with no news items."""
        # Clear any existing news items
        News.objects.all().delete()

        # Test processor
        processor = NewsStreamProcessor(
            stream_id=self.stream.id, agent_id=self.agent.id
        )
        result = processor.process()

        # Verify empty result
        self.assertIn("No news items found", result["error"])
        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["saved"], 0)

    def test_process_news_stream_wrapper(self):
        """Test the process_news_stream wrapper function."""
        with patch(
            "streams.tasks.news_stream.NewsStreamProcessor"
        ) as mock_processor_cls:
            # Mock the processor
            mock_processor = MagicMock()
            mock_processor.process.return_value = {
                "processed": 1,
                "saved": 1,
                "error": None,
                "bedrock_response": {"test": "response"},
            }
            mock_processor_cls.return_value = mock_processor

            # Test the wrapper
            result = process_news_stream(
                stream_id=self.stream.id,
                agent_id=self.agent.id,
                time_window_minutes=30,
                max_items=50,
            )

            # Verify results
            self.assertEqual(result["processed"], 1)
            self.assertEqual(result["saved"], 1)
            self.assertIsNone(result["error"])
            mock_processor_cls.assert_called_once_with(
                stream_id=self.stream.id, agent_id=self.agent.id
            )
            mock_processor.process.assert_called_once_with(
                time_window_minutes=30, max_items=50
            )
