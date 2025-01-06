Available Tasks
==============

.. contents:: Table of Contents
   :local:
   :depth: 2

This section describes all available tasks in the Newsloom system and their specific use cases.

Article Search Tasks
------------------

article_searcher
~~~~~~~~~~~~~~
A task for searching articles on web pages based on specific text content. It uses Playwright to:

* Extract links from a webpage using CSS or XPath selectors
* Visit each link and search for specific text in the article content
* Save matching articles to the database

.. important::
   To save found articles, the stream **must** have a source configured in the admin panel. 
   Without a configured source, the task will find articles but won't be able to save them 
   to the database.

Required Setup:
    1. Create a Source in the admin panel
    2. Create a Stream and select the created source
    3. Configure the stream with the settings below

Configuration example:

.. code-block:: python

    {
        "url": "https://example.com",
        "link_selector": "//*[@id='wtxt']/div[2]/ul/li[1]/a",
        "link_selector_type": "xpath",
        "article_selector": "div.article-content",
        "article_selector_type": "css",
        "search_text": "białoruś",
        "max_links": 10
    }

Search Engine Tasks
-----------------

bing_search
~~~~~~~~~~
A task for searching articles using Bing's search engine. Features:

* Supports both news and web search types
* Configurable results per keyword
* Stealth browser automation to avoid detection

.. important::
   To save found articles, the stream **must** have a source configured in the admin panel. 
   Without a configured source, the task will find articles but won't be able to save them 
   to the database.

Configuration example:

.. code-block:: python

    {
        "keywords": ["climate change", "renewable energy"],
        "max_results_per_keyword": 5,
        "search_type": "news",
        "debug": False
    }

Required Setup:
    1. Create a Source in the admin panel (e.g., "Bing News")
    2. Create a Stream and select the created source
    3. Configure the stream with the above settings

google_search
~~~~~~~~~~~
A task for searching articles using Google's search engine. Features:

* Supports both news and web search types
* Time-based filtering (days ago)
* Multiple keyword support
* Stealth browser automation

.. important::
   To save found articles, the stream **must** have a source configured in the admin panel. 
   Without a configured source, the task will find articles but won't be able to save them 
   to the database.

Required Setup:
    1. Create a Source in the admin panel (e.g., "Google News")
    2. Create a Stream and select the created source
    3. Configure the stream with the settings below

Configuration example:

.. code-block:: python

    {
        "keywords": ["climate change", "renewable energy"],
        "max_results_per_keyword": 5,
        "days_ago": 7,
        "search_type": "news",
        "debug": False
    }

Content Publishing Tasks
---------------------

doc_publisher
~~~~~~~~~~~
A task for publishing documents to Telegram channels. Features:

* Batch processing of documents
* Time window filtering
* HTML formatting support
* Error handling and logging

Configuration example:

.. code-block:: python

    {
        "channel_id": "-100123456789",
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        "time_window_minutes": 60,
        "batch_size": 10
    }

News Processing Tasks
------------------

news_stream
~~~~~~~~~
A task for processing news streams using AI agents. Features:

* Integration with Amazon Bedrock
* Customizable prompt templates
* Batch processing
* Support for saving to docs

Configuration example:

.. code-block:: python

    {
        "agent_id": 1,
        "time_window_minutes": 60,
        "max_items": 100,
        "save_to_docs": True
    }

Web Scraping Tasks
----------------

playwright
~~~~~~~~~
A task for extracting links from web pages using Playwright. Features:

* Configurable link selectors
* Stealth browser automation
* Automatic URL normalization

.. important::
   To save found articles, the stream **must** have a source configured in the admin panel. 
   Without a configured source, the task will find articles but won't be able to save them 
   to the database.

Required Setup:
    1. Create a Source in the admin panel
    2. Create a Stream and select the created source
    3. Configure the stream with the settings below

Configuration example:

.. code-block:: python

    {
        "url": "https://example.com",
        "link_selector": "a.article-link",
        "max_links": 100
    }

rss
~~~
A task for parsing RSS feeds. Features:

* Feed URL processing
* Entry limit configuration
* Automatic date parsing
* Duplicate handling

.. important::
   To save found articles, the stream **must** have a source configured in the admin panel. 
   Without a configured source, the task will find articles but won't be able to save them 
   to the database.

Required Setup:
    1. Create a Source in the admin panel (e.g., the RSS feed name)
    2. Create a Stream and select the created source
    3. Configure the stream with the settings below

Configuration example:

.. code-block:: python

    {
        "feed_url": "https://example.com/feed.xml",
        "max_entries": 100
    }

sitemap
~~~~~~~
A task for parsing XML sitemaps. Features:

* Support for sitemap index files
* Link limit configuration
* Last modification date handling
* Error handling for timeouts

.. important::
   To save found articles, the stream **must** have a source configured in the admin panel. 
   Without a configured source, the task will find articles but won't be able to save them 
   to the database.

Required Setup:
    1. Create a Source in the admin panel (e.g., the website name)
    2. Create a Stream and select the created source
    3. Configure the stream with the settings below

Configuration example:

.. code-block:: python

    {
        "sitemap_url": "https://example.com/sitemap.xml",
        "max_links": 100,
        "follow_next": False
    }

web
~~~
A task for scraping web articles using configurable selectors. Features:

* Custom header support
* Flexible selector configuration
* Error handling

Configuration example:

.. code-block:: python

    {
        "base_url": "https://example.com",
        "selectors": {
            "title": "h1.article-title",
            "content": "div.article-content",
            "date": "time.published-date"
        },
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    }

Telegram Tasks
------------

telegram
~~~~~~~
A task for monitoring Telegram channels. Features:

* Post limit configuration
* Automatic scrolling
* Message extraction
* Timestamp handling

Configuration example:

.. code-block:: python

    {
        "posts_limit": 20
    }

telegram_bulk_parser
~~~~~~~~~~~~~~~~~
A task for bulk parsing multiple Telegram channels. Features:

* Time window filtering
* Configurable scroll behavior
* Async processing
* Error handling per channel

Configuration example:

.. code-block:: python

    {
        "time_window_minutes": 120,
        "max_scrolls": 50,
        "wait_time": 5
    }

telegram_publisher
~~~~~~~~~~~~~~~
A task for publishing content to Telegram channels. Features:

* Batch processing
* Time window filtering
* Source type filtering
* Error handling per message

Configuration example:

.. code-block:: python

    {
        "channel_id": "-100123456789",
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        "batch_size": 10,
        "time_window_minutes": 10,
        "source_types": ["web", "telegram"]
    }

telegram_test
~~~~~~~~~~~
A task for testing Telegram channel connectivity. Features:

* Channel access verification
* Message sending test
* Detailed test results
* Random test messages

Configuration example:

.. code-block:: python

    {
        "channel_id": "-100123456789",
        "bot_token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
    }
