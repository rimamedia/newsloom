Use Cases
=========

This section provides detailed examples of common workflows and use cases in NewLoom, demonstrating how different components work together.

Telegram News Processing Pipeline
-------------------------------

This example demonstrates how to set up a pipeline for processing news from Telegram channels and republishing them.

Prerequisites
~~~~~~~~~~~~

Before setting up the pipeline, ensure you have:

* Telegram API credentials configured
* Access to source Telegram channels
* Target Telegram channel for publishing

Step 1: Media Setup
~~~~~~~~~~~~~~~~~

First, create a media profile that defines the style and format for the rewritten content:

1. Navigate to Admin > Media Manager > Add Media
2. Configure:
   * Name: "Telegram News Format"
   * Add example posts that demonstrate your desired writing style

Step 2: Source Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the source Telegram channels:

1. Go to Admin > Sources > Add Source
2. For each channel:
   * Name: Channel's name
   * Type: "Telegram Channel"
   * Link: Channel username/ID

Important: Ensure that you associate sources with the media profile created in Step 1.

Step 3: Input Stream (Telegram Parser)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a stream to monitor and parse Telegram channels:

1. Go to Admin > Streams > Add Stream
2. Configure:
   * Name: "Telegram Channel Monitor"
   * Stream Type: "telegram_bulk_parser"
   * Source: Select your configured Telegram source
   * Frequency: Choose monitoring frequency (e.g., "15min")
   * Configuration:
     .. code-block:: json

        {
            "limit": 100,
            "parse_links": true,
            "save_media": true
        }

This stream will regularly check the source channels and create Doc objects for new posts.

Step 4: Processing Stream
~~~~~~~~~~~~~~~~~~~~~~

Create a stream to process the collected posts:

1. Add new stream:
   * Name: "News Processor"
   * Stream Type: "news_stream"
   * Media: Select your "Telegram News Format" media
   * Frequency: "5min"
   * Configuration:
     .. code-block:: json

        {
            "prompt_template": "Analyze and rewrite this news item in our style: {content}",
            "max_tokens": 1000
        }

This stream processes new Doc objects using the configured prompt and generates rewritten content.

Step 5: Publishing Stream
~~~~~~~~~~~~~~~~~~~~~~

Finally, create a stream to publish the processed content:

1. Add new stream:
   * Name: "Telegram Publisher"
   * Stream Type: "doc_publisher"
   * Media: Select your "Telegram News Format" media
   * Frequency: "5min"
   * Configuration:
     .. code-block:: json

        {
            "channel": "@your_channel_username",
            "include_source": true
        }

Important Considerations
~~~~~~~~~~~~~~~~~~~~~

* **Stream Dependencies**: The streams process content in sequence:
    1. telegram_bulk_parser creates Doc objects from source channels
    2. news_stream processes these Doc objects
    3. doc_publisher publishes the processed content

* **Media Configuration**: The media profile is essential for:
    - Defining content style through examples
    - Maintaining consistent output format
    - Guiding AI processing

* **Monitoring**: The admin interface provides:
    - Stream execution status tracking
    - Processing logs
    - Error messages for troubleshooting

This pipeline demonstrates NewLoom's ability to:
    - Monitor Telegram channels
    - Process content using AI
    - Maintain consistent publishing style
    - Automate the entire workflow

.. toctree::
   :maxdepth: 2
   :caption: More Examples:
