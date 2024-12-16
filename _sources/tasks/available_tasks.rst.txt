Available Tasks
=============

This guide provides a comprehensive list of all available tasks in NewLoom.

Content Collection Tasks
---------------------

Sitemap Parser
~~~~~~~~~~~~
- Type: ``sitemap_news``, ``sitemap_blog``
- Description: Parses XML sitemaps to extract URLs for news articles or blog posts
- Key Features:
    * Configurable max links
    * Support for next page following
    * Automatic URL validation

RSS Feed Parser
~~~~~~~~~~~~
- Type: ``rss_feed``
- Description: Extracts content from RSS/Atom feeds
- Key Features:
    * Support for multiple feed formats
    * Entry limit configuration
    * Automatic feed validation

Web Article Scraper
~~~~~~~~~~~~~~~~
- Type: ``web_article``
- Description: Scrapes content from web articles using configurable selectors
- Key Features:
    * Custom CSS/XPath selectors
    * Header customization
    * Content extraction rules

Playwright Link Extractor
~~~~~~~~~~~~~~~~~~~~~~
- Type: ``playwright_link_extractor``
- Description: Uses Playwright for JavaScript-rendered content extraction
- Key Features:
    * Support for dynamic content
    * Custom link selectors
    * Browser automation

Article Content Searcher
~~~~~~~~~~~~~~~~~~~~
- Type: ``article_searcher``
- Description: Searches article content for specific text or patterns
- Key Features:
    * Text pattern matching
    * Multiple selector types
    * Configurable search depth

Bing Search
~~~~~~~~~
- Type: ``bing_search``
- Description: Performs searches using Bing's search engine
- Key Features:
    * Multiple keyword support
    * News/web search options
    * Result limit configuration

Content Processing Tasks
---------------------

News Stream Processor
~~~~~~~~~~~~~~~~~
- Type: ``news_stream``
- Description: Processes news items using AI agents
- Key Features:
    * AI-powered content analysis
    * Batch processing
    * Automatic doc creation

Publishing Tasks
-------------

Telegram Publisher
~~~~~~~~~~~~~~
- Type: ``telegram_publish``
- Description: Publishes news items to Telegram channels
- Key Features:
    * Batch publishing
    * Time window filtering
    * Publishing logs

Doc Publisher
~~~~~~~~~~
- Type: ``doc_publisher``
- Description: Publishes processed docs to Telegram channels
- Key Features:
    * Status tracking (new -> published/failed)
    * Batch processing
    * Configurable time window
    * Publishing logs

Monitoring Tasks
-------------

Telegram Channel Monitor
~~~~~~~~~~~~~~~~~~~~
- Type: ``telegram_channel``
- Description: Monitors Telegram channels for new content
- Key Features:
    * Post limit configuration
    * Automatic content extraction
    * Channel monitoring

Telegram Bulk Parser
~~~~~~~~~~~~~~~~~
- Type: ``telegram_bulk_parser``
- Description: Bulk parses multiple Telegram channels
- Key Features:
    * Multiple channel support
    * Configurable scroll depth
    * Time window filtering

Testing Tasks
----------

Telegram Test Publisher
~~~~~~~~~~~~~~~~~~~
- Type: ``telegram_test``
- Description: Tests Telegram channel connectivity and permissions
- Key Features:
    * Channel access verification
    * Bot token validation
    * Test message sending

Configuration Examples
------------------

For configuration examples of each task type, refer to the ``TASK_CONFIG_EXAMPLES`` in the task initialization file:

.. code-block:: python

    TASK_CONFIG_EXAMPLES = {
        "doc_publisher": {
            "channel_id": "-100123456789",  # Telegram channel ID
            "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",  # Bot token
            "time_window_minutes": 60,  # Look back 1 hour
            "batch_size": 10,  # Process up to 10 docs at a time
        },
        # ... other task configurations
    }

For detailed implementation examples, see :doc:`examples`.
