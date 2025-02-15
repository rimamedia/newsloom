REST API Endpoints
=================

NewLoom provides a RESTful API using Django REST Framework. This section documents the available endpoints and their usage.

Authentication
------------

All API endpoints require authentication. The following authentication methods are supported:

- Token Authentication (``Authorization: Token <your-token>``)
- Session Authentication (for browser-based access)

For details on obtaining tokens and authentication setup, see :doc:`authentication`.

Common Headers
------------

- ``Content-Type: application/json``
- ``Accept: application/json``
- ``Authorization: Token <your-token>``

Pagination
---------

API responses are paginated by default with the following structure:

.. code-block:: json

    {
        "count": 100,
        "next": "http://api.example.org/items/?page=2",
        "previous": null,
        "results": []
    }

Configuration:
    - Default page size: 10
    - Maximum page size: 100
    - Page size parameter: ``?page_size=20``

Sources API
---------

List Sources
~~~~~~~~~~

.. http:get:: /api/sources/

    Get a list of all sources.

    **Example request**:

    .. sourcecode:: http

        GET /api/sources/ HTTP/1.1
        Host: example.com
        Authorization: Token <your-token>

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "count": 2,
            "next": null,
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "name": "Example News",
                    "link": "https://example.com",
                    "type": "web"
                },
                {
                    "id": 2,
                    "name": "Tech Feed",
                    "link": "https://techfeed.com/rss",
                    "type": "rss"
                }
            ]
        }

Create Source
~~~~~~~~~~~

.. http:post:: /api/sources/

    Create a new source.

    **Example request**:

    .. sourcecode:: http

        POST /api/sources/ HTTP/1.1
        Host: example.com
        Authorization: Token <your-token>
        Content-Type: application/json

        {
            "name": "New Source",
            "link": "https://newsource.com",
            "type": "web"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

        {
            "id": 3,
            "name": "New Source",
            "link": "https://newsource.com",
            "type": "web"
        }

Streams API
---------

List Streams
~~~~~~~~~~

.. http:get:: /api/streams/

    Get a list of all streams.

    **Example request**:

    .. sourcecode:: http

        GET /api/streams/ HTTP/1.1
        Host: example.com
        Authorization: Token <your-token>

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "name": "News Monitor",
                    "stream_type": "web_scraper",
                    "source": 1,
                    "configuration": {
                        "url": "https://example.com",
                        "link_selector": "a.article-link",
                        "max_links": 100
                    },
                    "status": "active"
                }
            ]
        }

Create Stream
~~~~~~~~~~~

.. http:post:: /api/streams/

    Create a new stream.

    **Example request**:

    .. sourcecode:: http

        POST /api/streams/ HTTP/1.1
        Host: example.com
        Authorization: Token <your-token>
        Content-Type: application/json

        {
            "name": "New Stream",
            "stream_type": "rss",
            "source": 2,
            "configuration": {
                "feed_url": "https://example.com/feed.xml",
                "max_entries": 100
            }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 201 Created
        Content-Type: application/json

        {
            "id": 2,
            "name": "New Stream",
            "stream_type": "rss",
            "source": 2,
            "configuration": {
                "feed_url": "https://example.com/feed.xml",
                "max_entries": 100
            },
            "status": "active"
        }

News API
-------

List News Articles
~~~~~~~~~~~~~~~

.. http:get:: /api/news/

    Get a list of news articles.

    **Example request**:

    .. sourcecode:: http

        GET /api/news/ HTTP/1.1
        Host: example.com
        Authorization: Token <your-token>

    **Query Parameters**:
        - source (optional): Filter by source ID
        - status (optional): Filter by status
        - from_date (optional): Filter by date (YYYY-MM-DD)
        - to_date (optional): Filter by date (YYYY-MM-DD)

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "count": 1,
            "next": null,
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "title": "Example Article",
                    "link": "https://example.com/article",
                    "text": "Article content...",
                    "source": 1,
                    "created_at": "2024-02-05T12:00:00Z"
                }
            ]
        }

Error Responses
-------------

The API uses standard HTTP status codes and provides detailed error messages:

400 Bad Request
~~~~~~~~~~~~~

.. sourcecode:: http

    HTTP/1.1 400 Bad Request
    Content-Type: application/json

    {
        "error": "Invalid request",
        "detail": {
            "field_name": [
                "This field is required."
            ]
        }
    }

401 Unauthorized
~~~~~~~~~~~~~

.. sourcecode:: http

    HTTP/1.1 401 Unauthorized
    Content-Type: application/json

    {
        "detail": "Authentication credentials were not provided."
    }

404 Not Found
~~~~~~~~~~~

.. sourcecode:: http

    HTTP/1.1 404 Not Found
    Content-Type: application/json

    {
        "detail": "Not found."
    }

Rate Limiting
-----------

API endpoints are rate limited to prevent abuse:

- Authenticated requests: 1000 requests per hour
- Anonymous requests: 100 requests per hour

Rate limit headers are included in responses:

.. sourcecode:: http

    X-RateLimit-Limit: 1000
    X-RateLimit-Remaining: 999
    X-RateLimit-Reset: 1612345678
