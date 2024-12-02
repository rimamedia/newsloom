FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies, Nginx, and netcat
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    supervisor \
    nginx \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/mediafiles

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy the Django project
COPY newsloom /app/newsloom

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# Set the working directory to where manage.py is
WORKDIR /app/newsloom

# Collect static files
RUN python manage.py collectstatic --noinput

# Create log directory and files
RUN mkdir -p /var/log && \
    touch /var/log/gunicorn.err.log /var/log/gunicorn.out.log \
        /var/log/nginx.err.log /var/log/nginx.out.log \
        /var/log/stream_scheduler.err.log /var/log/stream_scheduler.out.log

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose Nginx port
EXPOSE 80

# Create a startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
