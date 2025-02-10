Static Files Management
======================

NewLoom uses Django's static files system to handle CSS, JavaScript, images, and other static assets. This guide explains how to manage static files in both development and production environments.

Configuration
------------

The project's static files settings are configured in ``settings.py``:

.. code-block:: python

    STATIC_URL = '/static/'
    STATIC_ROOT = str(BASE_DIR / 'static')
    MEDIA_URL = '/media/'
    MEDIA_ROOT = str(BASE_DIR / 'media')

- ``STATIC_URL``: The URL prefix for serving static files (e.g., ``http://example.com/static/style.css``)
- ``STATIC_ROOT``: The directory where ``collectstatic`` will collect static files for production
- ``MEDIA_URL``: The URL prefix for user-uploaded files
- ``MEDIA_ROOT``: The directory where uploaded files are stored

Collecting Static Files
----------------------

In production environments, you need to collect all static files into a single directory for efficient serving. Django provides the ``collectstatic`` management command for this purpose:

.. code-block:: bash

    python manage.py collectstatic

This command:
1. Looks for static files in each app's ``static`` directory
2. Copies all found files to the ``STATIC_ROOT`` directory
3. Preserves the directory structure within ``STATIC_ROOT``

Static Files Organization
-----------------------

NewLoom follows Django's conventional static files organization:

App-specific Static Files
~~~~~~~~~~~~~~~~~~~~~~~~

Each Django app can have its own static files in an app-level ``static`` directory:

.. code-block:: text

    your_app/
        static/
            your_app/  # namespace to avoid naming conflicts
                css/
                    styles.css
                js/
                    script.js
                images/
                    logo.png

Project-wide Static Files
~~~~~~~~~~~~~~~~~~~~~~~

For static files that don't belong to a specific app, use the project-level static directory:

.. code-block:: text

    newsloom/
        static/
            css/
            js/
            images/

Production Setup
--------------

In production, static files should be served by a web server like Nginx for better performance.

Nginx Configuration
~~~~~~~~~~~~~~~~~

The project includes Nginx configurations for different environments. Here's an example of how static files are configured in ``nginx_ecs.conf``:

.. code-block:: nginx

    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /app/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

Development vs Production
~~~~~~~~~~~~~~~~~~~~~~~

- **Development**: Django's development server automatically serves static files
- **Production**: Use the following checklist:
    1. Run ``collectstatic`` during deployment
    2. Configure web server (Nginx) to serve files from ``STATIC_ROOT``
    3. Set ``DEBUG = False`` in settings
    4. Ensure proper file permissions on static directories

Security Considerations
~~~~~~~~~~~~~~~~~~~~

1. Never serve files from ``STATIC_ROOT`` in development
2. Keep ``DEBUG = False`` in production
3. Use proper file permissions on static and media directories
4. Configure proper Cache-Control headers
5. Consider using a CDN for better performance

Docker Environment
---------------

When running in Docker:

1. The ``collectstatic`` command is run during container build:

   .. code-block:: dockerfile

       RUN python manage.py collectstatic --noinput

2. Static files are served through Nginx as configured in ``nginx_ecs.conf``
3. Volumes are properly mounted to persist media files
