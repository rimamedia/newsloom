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
    curl \
    # Dependencies for Playwright/Chromium in container
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install CloudWatch agent based on architecture
RUN arch=$(dpkg --print-architecture) && \
    if [ "$arch" = "amd64" ]; then \
        curl -O https://s3.amazonaws.com/amazoncloudwatch-agent/debian/amd64/latest/amazon-cloudwatch-agent.deb && \
        dpkg -i amazon-cloudwatch-agent.deb && \
        rm amazon-cloudwatch-agent.deb; \
    elif [ "$arch" = "arm64" ]; then \
        curl -O https://s3.amazonaws.com/amazoncloudwatch-agent/debian/arm64/latest/amazon-cloudwatch-agent.deb && \
        dpkg -i amazon-cloudwatch-agent.deb && \
        rm amazon-cloudwatch-agent.deb; \
    else \
        echo "Unsupported architecture: $arch"; \
    fi

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/mediafiles

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers with system dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright
RUN mkdir -p /app/ms-playwright && \
    playwright install --with-deps chromium && \
    chmod -R 777 /app/ms-playwright

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
