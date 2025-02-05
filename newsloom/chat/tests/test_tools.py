from agents.models import Agent
from chat.tools import (
    add_agent,
    add_media,
    add_source,
    add_stream,
    delete_agent,
    delete_media,
    delete_source,
    delete_stream,
    list_agents,
    list_media,
    list_sources,
    list_streams,
    update_agent,
    update_media,
    update_source,
    update_stream,
)
from django.core.exceptions import ValidationError
from django.test import TestCase
from mediamanager.models import Media
from sources.models import Source
from streams.models import Stream


class ToolsBaseTestCase(TestCase):
    def setUp(self):
        """Create test data for all tools tests."""
        # Create test media entries
        self.media_list = []
        for i in range(60):  # Create 60 entries for pagination testing
            media = Media.objects.create(name=f"Test Media {i}")
            self.media_list.append(media)

        # Create test source entries
        self.source_list = []
        for i in range(60):
            source = Source.objects.create(
                name=f"Test Source {i}", link=f"https://example{i}.com", type="web"
            )
            self.source_list.append(source)

        # Create test stream entries
        self.stream_list = []
        for i in range(60):
            # Alternate between web_article and rss_feed streams
            if i % 2 == 0:
                stream = Stream.objects.create(
                    name=f"Test Web Article Stream {i}",
                    stream_type="web_article",
                    frequency="daily",
                    configuration={
                        "base_url": "https://example.com",
                        "selectors": {"title": "h1", "content": "article"},
                    },
                    status="active",
                )
            else:
                stream = Stream.objects.create(
                    name=f"Test RSS Stream {i}",
                    stream_type="rss_feed",
                    frequency="daily",
                    configuration={
                        "url": "https://example.com/feed.xml",
                        "max_items": 10,
                    },
                    status="paused",
                )
            self.stream_list.append(stream)

        # Create test agent entries
        self.agent_list = []
        for i in range(60):
            agent = Agent.objects.create(
                name=f"Test Agent {i}",
                provider="anthropic",
                system_prompt="Test system prompt",
                user_prompt_template="Test template with {news}",
                is_active=i % 2 == 0,
            )
            self.agent_list.append(agent)


class MediaToolsTests(ToolsBaseTestCase):
    def test_list_media_pagination(self):
        """Test pagination for list_media function."""
        # Test default pagination (50 items)
        result = list_media()
        self.assertEqual(len(result["items"]), 50)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 50)
        self.assertEqual(result["offset"], 0)

        # Test custom limit
        result = list_media(limit=20)
        self.assertEqual(len(result["items"]), 20)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 20)

        # Test offset
        result = list_media(offset=50)
        self.assertEqual(len(result["items"]), 10)  # Only 10 items remaining
        self.assertEqual(result["offset"], 50)

        # Test combined limit and offset
        result = list_media(limit=5, offset=55)
        self.assertEqual(len(result["items"]), 5)
        self.assertEqual(result["offset"], 55)

    def test_media_crud(self):
        """Test CRUD operations for media tools."""
        # Test add_media
        new_media = add_media(name="New Test Media")
        self.assertIsNotNone(new_media)
        self.assertEqual(new_media.name, "New Test Media")

        # Test add_media with sources
        source_ids = [self.source_list[0].id, self.source_list[1].id]
        new_media_with_sources = add_media(
            name="Media With Sources", source_ids=source_ids
        )
        self.assertEqual(new_media_with_sources.sources.count(), 2)
        self.assertListEqual(
            sorted(new_media_with_sources.sources.values_list("id", flat=True)),
            sorted(source_ids),
        )

        # Test update_media
        updated_media = update_media(id=new_media.id, name="Updated Test Media")
        self.assertEqual(updated_media.name, "Updated Test Media")

        # Test update_media with sources
        new_source_ids = [self.source_list[2].id, self.source_list[3].id]
        updated_media = update_media(id=new_media.id, source_ids=new_source_ids)
        self.assertListEqual(
            sorted(updated_media.sources.values_list("id", flat=True)),
            sorted(new_source_ids),
        )

        # Test delete_media
        delete_media(id=new_media.id)
        with self.assertRaises(Media.DoesNotExist):
            Media.objects.get(id=new_media.id)

        # Test error cases
        with self.assertRaises(Media.DoesNotExist):
            delete_media(id=99999)  # Non-existent ID

        with self.assertRaises(Source.DoesNotExist):
            add_media(name="Test", source_ids=[99999])  # Non-existent source ID


class SourceToolsTests(ToolsBaseTestCase):
    def test_list_sources_pagination(self):
        """Test pagination for list_sources function."""
        # Test default pagination (50 items)
        result = list_sources()
        self.assertEqual(len(result["items"]), 50)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 50)
        self.assertEqual(result["offset"], 0)

        # Test custom limit
        result = list_sources(limit=20)
        self.assertEqual(len(result["items"]), 20)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 20)

        # Test offset
        result = list_sources(offset=50)
        self.assertEqual(len(result["items"]), 10)  # Only 10 items remaining
        self.assertEqual(result["offset"], 50)

        # Test combined limit and offset
        result = list_sources(limit=5, offset=55)
        self.assertEqual(len(result["items"]), 5)
        self.assertEqual(result["offset"], 55)

    def test_source_crud(self):
        """Test CRUD operations for source tools."""
        # Test add_source
        new_source = add_source(
            name="New Test Source", link="https://example.com", type="web"
        )
        self.assertIsNotNone(new_source)
        self.assertEqual(new_source.name, "New Test Source")
        self.assertEqual(new_source.link, "https://example.com")
        self.assertEqual(new_source.type, "web")

        # Test update_source
        updated_source = update_source(
            id=new_source.id,
            name="Updated Test Source",
            link="https://updated.com",
            type="rss",
        )
        self.assertEqual(updated_source.name, "Updated Test Source")
        self.assertEqual(updated_source.link, "https://updated.com")
        self.assertEqual(updated_source.type, "rss")

        # Test partial update
        partial_update = update_source(
            id=new_source.id, name="Partially Updated Source"
        )
        self.assertEqual(partial_update.name, "Partially Updated Source")
        self.assertEqual(partial_update.link, "https://updated.com")  # Unchanged
        self.assertEqual(partial_update.type, "rss")  # Unchanged

        # Test delete_source
        delete_source(id=new_source.id)
        with self.assertRaises(Source.DoesNotExist):
            Source.objects.get(id=new_source.id)

        # Test error cases
        with self.assertRaises(Source.DoesNotExist):
            delete_source(id=99999)  # Non-existent ID

        with self.assertRaises(ValidationError):
            add_source(  # Invalid source type
                name="Invalid Source", link="https://example.com", type="invalid_type"
            )


class StreamToolsTests(ToolsBaseTestCase):
    def test_list_streams_pagination(self):
        """Test pagination for list_streams function."""
        # Test default pagination (50 items)
        result = list_streams()
        self.assertEqual(len(result["items"]), 50)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 50)
        self.assertEqual(result["offset"], 0)

        # Test custom limit
        result = list_streams(limit=20)
        self.assertEqual(len(result["items"]), 20)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 20)

        # Test offset
        result = list_streams(offset=50)
        self.assertEqual(len(result["items"]), 10)  # Only 10 items remaining
        self.assertEqual(result["offset"], 50)

        # Test status filter
        result = list_streams(status="active")
        self.assertEqual(len(result["items"]), 30)  # Half of the streams are active
        self.assertEqual(result["total"], 30)

        # Test combined status filter and pagination
        result = list_streams(status="active", limit=10, offset=25)
        self.assertEqual(len(result["items"]), 5)  # Only 5 active items remaining
        self.assertEqual(result["total"], 30)
        self.assertEqual(result["limit"], 10)
        self.assertEqual(result["offset"], 25)

    def test_web_article_stream_crud(self):
        """Test CRUD operations for web article streams."""
        # Test add web article stream
        new_stream = add_stream(
            name="New Web Article Stream",
            stream_type="web_article",
            frequency="daily",
            configuration={
                "base_url": "https://example.com",
                "selectors": {"title": "h1", "content": "article"},
            },
        )
        self.assertIsNotNone(new_stream)
        self.assertEqual(new_stream.name, "New Web Article Stream")
        self.assertEqual(new_stream.stream_type, "web_article")
        self.assertEqual(new_stream.frequency, "daily")
        self.assertEqual(
            new_stream.configuration,
            {
                "base_url": "https://example.com",
                "selectors": {"title": "h1", "content": "article"},
            },
        )

        # Test update web article stream
        updated_stream = update_stream(
            id=new_stream.id,
            name="Updated Web Article Stream",
            configuration={
                "base_url": "https://updated.com",
                "selectors": {"title": ".title", "content": ".content"},
            },
            status="paused",
        )
        self.assertEqual(updated_stream.name, "Updated Web Article Stream")
        self.assertEqual(updated_stream.stream_type, "web_article")  # Type unchanged
        self.assertEqual(
            updated_stream.configuration,
            {
                "base_url": "https://updated.com",
                "selectors": {"title": ".title", "content": ".content"},
            },
        )
        self.assertEqual(updated_stream.status, "paused")

        # Test delete web article stream
        delete_stream(id=new_stream.id)
        with self.assertRaises(Stream.DoesNotExist):
            Stream.objects.get(id=new_stream.id)

    def test_rss_feed_stream_crud(self):
        """Test CRUD operations for RSS feed streams."""
        # Test add RSS feed stream
        new_stream = add_stream(
            name="New RSS Feed Stream",
            stream_type="rss_feed",
            frequency="daily",
            configuration={"url": "https://example.com/feed.xml", "max_items": 20},
        )
        self.assertIsNotNone(new_stream)
        self.assertEqual(new_stream.name, "New RSS Feed Stream")
        self.assertEqual(new_stream.stream_type, "rss_feed")
        self.assertEqual(new_stream.frequency, "daily")
        self.assertEqual(
            new_stream.configuration,
            {"url": "https://example.com/feed.xml", "max_items": 20},
        )

        # Test update RSS feed stream
        updated_stream = update_stream(
            id=new_stream.id,
            name="Updated RSS Feed Stream",
            configuration={"url": "https://updated.com/feed.xml", "max_items": 50},
            status="paused",
        )
        self.assertEqual(updated_stream.name, "Updated RSS Feed Stream")
        self.assertEqual(updated_stream.stream_type, "rss_feed")  # Type unchanged
        self.assertEqual(
            updated_stream.configuration,
            {"url": "https://updated.com/feed.xml", "max_items": 50},
        )
        self.assertEqual(updated_stream.status, "paused")

        # Test delete RSS feed stream
        delete_stream(id=new_stream.id)
        with self.assertRaises(Stream.DoesNotExist):
            Stream.objects.get(id=new_stream.id)

    def test_stream_validation_errors(self):
        """Test stream validation error cases."""
        # Test invalid stream type
        with self.assertRaises(ValidationError):
            add_stream(
                name="Invalid Stream",
                stream_type="invalid_type",
                frequency="daily",
                configuration={},
            )

        # Test invalid frequency
        with self.assertRaises(ValidationError):
            add_stream(
                name="Invalid Frequency",
                stream_type="web_article",
                frequency="hourly",  # Invalid frequency
                configuration={
                    "base_url": "https://example.com",
                    "selectors": {"title": "h1", "content": "article"},
                },
            )

        # Test invalid web article configuration
        with self.assertRaises(ValidationError):
            add_stream(
                name="Invalid Web Article Config",
                stream_type="web_article",
                frequency="daily",
                configuration={
                    "base_url": "https://example.com"
                    # Missing required selectors
                },
            )

        # Test invalid RSS feed configuration
        with self.assertRaises(ValidationError):
            add_stream(
                name="Invalid RSS Config",
                stream_type="rss_feed",
                frequency="daily",
                configuration={
                    "max_items": 10
                    # Missing required url
                },
            )

        # Test non-existent source
        with self.assertRaises(Source.DoesNotExist):
            add_stream(
                name="Invalid Source",
                stream_type="web_article",
                frequency="daily",
                configuration={
                    "base_url": "https://example.com",
                    "selectors": {"title": "h1", "content": "article"},
                },
                source_id=99999,
            )

        # Test non-existent media
        with self.assertRaises(Media.DoesNotExist):
            add_stream(
                name="Invalid Media",
                stream_type="web_article",
                frequency="daily",
                configuration={
                    "base_url": "https://example.com",
                    "selectors": {"title": "h1", "content": "article"},
                },
                media_id=99999,
            )

    def test_stream_with_references(self):
        """Test stream operations with source and media references."""
        source_id = self.source_list[0].id
        media_id = self.media_list[0].id

        # Test add stream with references
        new_stream = add_stream(
            name="Stream With References",
            stream_type="web_article",
            frequency="daily",
            configuration={
                "base_url": "https://example.com",
                "selectors": {"title": "h1", "content": "article"},
            },
            source_id=source_id,
            media_id=media_id,
        )
        self.assertEqual(new_stream.source_id, source_id)
        self.assertEqual(new_stream.media_id, media_id)

        # Test update stream references
        new_source_id = self.source_list[1].id
        new_media_id = self.media_list[1].id
        updated_stream = update_stream(
            id=new_stream.id, source_id=new_source_id, media_id=new_media_id
        )
        self.assertEqual(updated_stream.source_id, new_source_id)
        self.assertEqual(updated_stream.media_id, new_media_id)

        # Test remove references
        updated_stream = update_stream(
            id=new_stream.id,
            source_id=0,  # Special case to remove source
            media_id=0,  # Special case to remove media
        )
        self.assertIsNone(updated_stream.source_id)
        self.assertIsNone(updated_stream.media_id)


class AgentToolsTests(ToolsBaseTestCase):
    def test_list_agents_pagination(self):
        """Test pagination for list_agents function."""
        # Test default pagination (50 items)
        result = list_agents()
        self.assertEqual(len(result["items"]), 50)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 50)
        self.assertEqual(result["offset"], 0)

        # Test custom limit
        result = list_agents(limit=20)
        self.assertEqual(len(result["items"]), 20)
        self.assertEqual(result["total"], 60)
        self.assertEqual(result["limit"], 20)

        # Test offset
        result = list_agents(offset=50)
        self.assertEqual(len(result["items"]), 10)  # Only 10 items remaining
        self.assertEqual(result["offset"], 50)

        # Test is_active filter
        result = list_agents(is_active=True)
        self.assertEqual(len(result["items"]), 30)  # Half of the agents are active
        self.assertEqual(result["total"], 30)

        # Test combined is_active filter and pagination
        result = list_agents(is_active=True, limit=10, offset=25)
        self.assertEqual(len(result["items"]), 5)  # Only 5 active items remaining
        self.assertEqual(result["total"], 30)
        self.assertEqual(result["limit"], 10)
        self.assertEqual(result["offset"], 25)

    def test_agent_crud(self):
        """Test CRUD operations for agent tools."""
        # Test add_agent
        new_agent = add_agent(
            name="New Test Agent",
            provider="anthropic",
            system_prompt="Test system prompt",
            user_prompt_template="Test template with {news}",
            description="Test description",
            is_active=True,
        )
        self.assertIsNotNone(new_agent)
        self.assertEqual(new_agent.name, "New Test Agent")
        self.assertEqual(new_agent.provider, "anthropic")
        self.assertEqual(new_agent.system_prompt, "Test system prompt")
        self.assertEqual(new_agent.user_prompt_template, "Test template with {news}")
        self.assertEqual(new_agent.description, "Test description")
        self.assertTrue(new_agent.is_active)

        # Test update_agent
        updated_agent = update_agent(
            id=new_agent.id,
            name="Updated Test Agent",
            provider="bedrock",
            system_prompt="Updated system prompt",
            user_prompt_template="Updated template with {news}",
            description="Updated description",
            is_active=False,
        )
        self.assertEqual(updated_agent.name, "Updated Test Agent")
        self.assertEqual(updated_agent.provider, "bedrock")
        self.assertEqual(updated_agent.system_prompt, "Updated system prompt")
        self.assertEqual(
            updated_agent.user_prompt_template, "Updated template with {news}"
        )
        self.assertEqual(updated_agent.description, "Updated description")
        self.assertFalse(updated_agent.is_active)

        # Test partial update
        partial_update = update_agent(
            id=new_agent.id, name="Partially Updated Agent", is_active=True
        )
        self.assertEqual(partial_update.name, "Partially Updated Agent")
        self.assertEqual(partial_update.provider, "bedrock")  # Unchanged
        self.assertTrue(partial_update.is_active)

        # Test delete_agent
        delete_agent(id=new_agent.id)
        with self.assertRaises(Agent.DoesNotExist):
            Agent.objects.get(id=new_agent.id)

        # Test error cases
        with self.assertRaises(Agent.DoesNotExist):
            delete_agent(id=99999)  # Non-existent ID

        with self.assertRaises(ValidationError):
            add_agent(  # Invalid provider
                name="Invalid Agent",
                provider="invalid_provider",
                system_prompt="Test prompt",
                user_prompt_template="Test template with {news}",
            )

        with self.assertRaises(ValidationError):
            add_agent(  # Missing {news} placeholder
                name="Invalid Agent",
                provider="anthropic",
                system_prompt="Test prompt",
                user_prompt_template="Invalid template",
            )
