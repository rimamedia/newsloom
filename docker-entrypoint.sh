#!/bin/bash

# Set Django settings module
export DJANGO_SETTINGS_MODULE=newsloom.settings

# Wait for database
echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

# Create and apply database migrations
echo "Creating database migrations..."
python manage.py makemigrations

echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Setup crawl4ai
echo "Setting up crawl4ai..."
crawl4ai-setup

# Start supervisor
echo "Starting supervisor..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
