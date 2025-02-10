NewLoom Documentation
===================

NewLoom is a Django-based platform designed for comprehensive news monitoring, content aggregation, and multi-channel publishing. It provides a robust framework for automating the entire news processing pipeline, from source monitoring to content distribution.

Getting Started
-------------

Initial Setup
~~~~~~~~~~~~

1. Create and activate a virtual environment::

    python -m venv venv
    source venv/bin/activate  # Unix
    venv\Scripts\activate     # Windows

2. Install dependencies::

    pip install -r requirements.txt

3. Install Playwright browsers::

    playwright install

4. Run database migrations::

    python manage.py migrate

5. Create a superuser::

    python manage.py createsuperuser 

6. Collect static files::

    python manage.py collectstatic

7. Start the development server::

    python manage.py runserver


Django Documentation References
~~~~~~~~~~~~~~~~~~~~~~~~~~

- `Django Documentation <https://docs.djangoproject.com/>`_
- `Django Models <https://docs.djangoproject.com/en/stable/topics/db/models/>`_
- `Django Admin Interface <https://docs.djangoproject.com/en/stable/ref/contrib/admin/>`_
- `Django Migrations <https://docs.djangoproject.com/en/stable/topics/migrations/>`_
- `Django Settings <https://docs.djangoproject.com/en/stable/ref/settings/>`_

Core Functionality
----------------

* **News Monitoring**
    - Automated tracking of multiple news sources
    - Support for websites, RSS feeds, and Telegram channels
    - Configurable monitoring frequencies
    - Real-time content detection

* **Content Processing**
    - Automated content extraction and parsing
    - Customizable processing pipelines
    - Support for various content formats
    - Error handling and retry mechanisms

* **Publishing System**
    - Multi-channel content distribution
    - Configurable publishing rules
    - Automated scheduling
    - Publishing status tracking

* **Chat Interface**
    - Web-based chat interface
    - Slack integration
    - Thread-based conversations
    - Context-aware responses

Technical Architecture
--------------------

* **Django Framework**
    - Robust data models and ORM
    - Admin interface for configuration
    - API endpoints for integration
    - Authentication and permissions

* **Integration Features**
    - Playwright for JavaScript rendering
    - RSS feed parsing
    - Telegram API integration
    - Customizable source adapters
    - Slack bot integration

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tasks/index
   schemas/index
   agents/index
   cases/index
   chat/slack_integration
   api/index
   deployment/index

Quick Links
----------

* :doc:`tasks/creating_tasks`
* :doc:`schemas/creating_schemas`
* :doc:`tasks/examples`
* :doc:`schemas/examples`
* :doc:`chat/slack_integration`
* :doc:`api/authentication`

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
