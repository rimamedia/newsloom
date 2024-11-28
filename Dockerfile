FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies and Nginx
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/mediafiles

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy the Django project
COPY newsloom /app/newsloom

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# Set the working directory to where manage.py is
WORKDIR /app/newsloom

# Collect static files
RUN python manage.py collectstatic --noinput

# Create log directory and files with proper permissions
RUN mkdir -p /var/log && \
    touch /var/log/gunicorn.err.log /var/log/gunicorn.out.log \
        /var/log/luigi_worker.err.log /var/log/luigi_worker.out.log \
        /var/log/nginx.err.log /var/log/nginx.out.log && \
    chown -R appuser:appuser /var/log && \
    chmod 755 /var/log && \
    chmod 664 /var/log/*.log

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make sure supervisor has access to its own files
RUN mkdir -p /var/run/supervisor /var/log/supervisor && \
    chown -R appuser:appuser /var/run/supervisor /var/log/supervisor && \
    chmod 755 /var/run/supervisor /var/log/supervisor

# Set permissions for static and media files
RUN chown -R appuser:appuser /app/staticfiles /app/mediafiles

# Set the working directory ownership
RUN chown -R appuser:appuser /app

# Create nginx directories and set permissions
RUN mkdir -p /var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx && \
    chown -R appuser:appuser /var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx && \
    chmod 755 /var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx

# Expose Nginx port
EXPOSE 80

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
