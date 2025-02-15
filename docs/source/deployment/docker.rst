Docker Deployment
===============

NewLoom can be deployed using Docker and Docker Compose. This guide explains the Docker setup, including how static files are handled in a containerized environment.

Docker Setup
-----------

The project includes several Docker-related files:

- ``Dockerfile``: Main container configuration
- ``docker-compose.yml``: Multi-container orchestration
- ``dev-nginx.conf``: Nginx configuration for development
- ``nginx_ecs.conf``: Nginx configuration for production (AWS ECS)
- ``supervisord.docker.conf``: Supervisor configuration for process management

Static Files in Docker
-------------------

Static files in Docker are handled in three stages:

1. Build Time
~~~~~~~~~~~~

During container build, static files are collected automatically:

.. code-block:: dockerfile

    # Create directories for static and media files
    RUN mkdir -p /app/staticfiles /app/mediafiles

    # Collect static files
    RUN python manage.py collectstatic --noinput

2. Runtime
~~~~~~~~~

Static and media files are managed through Docker volumes:

.. code-block:: yaml

    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles

This ensures:
- Static files persist between container restarts
- Multiple containers can share the same files
- Files survive container updates

3. Serving
~~~~~~~~~

Nginx serves static files directly:

.. code-block:: nginx

    # Serve static files
    location /static/ {
        alias /app/newsloom/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Serve media files
    location /media/ {
        alias /app/mediafiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

Development vs Production
----------------------

Development
~~~~~~~~~~

In development:
- Static files are mounted from local directory
- Nginx has autoindex enabled
- More verbose error logging
- CSRF and security settings are relaxed

.. code-block:: yaml

    volumes:
      - ./newsloom:/app/newsloom
      - ./docs:/app/docs
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles

Production
~~~~~~~~~

In production:
- Use production Nginx configuration
- Disable autoindex and debug settings
- Enable SSL/TLS
- Proper security headers
- Consider using CDN for static files

Running with Docker Compose
------------------------

1. Build and start services:

   .. code-block:: bash

       docker-compose up -d --build

2. Verify static files:

   .. code-block:: bash

       docker-compose exec web ls /app/staticfiles

3. Check Nginx configuration:

   .. code-block:: bash

       docker-compose exec web nginx -t

4. View logs:

   .. code-block:: bash

       docker-compose logs -f web

Troubleshooting
-------------

Common Issues:

1. Static files not appearing:
   - Verify collectstatic ran during build
   - Check volume mounts
   - Inspect Nginx configuration
   - Check file permissions

2. Media upload issues:
   - Verify media volume is mounted
   - Check directory permissions
   - Ensure proper Nginx configuration

3. Performance issues:
   - Enable Nginx caching
   - Consider using CDN
   - Optimize static files
   - Use compression

Best Practices
------------

1. Volume Management:
   - Use named volumes for persistence
   - Regular backups of media files
   - Clean up unused volumes

2. Security:
   - Proper file permissions
   - Secure headers in Nginx
   - Regular security updates
   - Environment-specific configurations

3. Performance:
   - Enable Nginx caching
   - Use compression
   - Consider CDN for production
   - Optimize static files
