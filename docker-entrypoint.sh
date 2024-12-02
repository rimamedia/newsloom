#!/bin/bash

# Wait for database
echo "Waiting for database..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start supervisor
echo "Starting supervisor..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf