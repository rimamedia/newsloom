# NewLoom

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.1.3-green.svg)](https://www.djangoproject.com/)
[![GitHub issues](https://img.shields.io/github/issues/rimamedia/newsloom)](https://github.com/rimamedia/newsloom/issues)
[![GitHub stars](https://img.shields.io/github/stars/rimamedia/newsloom)](https://github.com/rimamedia/newsloom/stargazers)

NewLoom is a comprehensive news monitoring, aggregation, and publishing platform built with Django. It provides a robust system for:

- **News Monitoring**: Automated tracking of multiple news sources through various channels
- **Content Aggregation**: Intelligent scraping and parsing of news content from diverse sources
- **Content Processing**: Customizable processing pipelines for content transformation
- **Multi-Channel Publishing**: Automated distribution of processed content to various platforms

## Architecture

NewLoom is built on three main pillars:

1. **Django Backend**
   - Core data models and business logic
   - REST API endpoints using Django REST framework
   - WebSocket support via Django Channels
   - Admin interface for configuration

2. **Stream Scheduler**
   - Custom task scheduling and execution
   - Configurable processing pipelines
   - Error handling and retry mechanisms
   - Execution statistics tracking

3. **Integration Layer**
   - Playwright for JavaScript-heavy websites
   - Telegram API integration
   - Slack bot integration
   - Articlean content processing

## Prerequisites

- Python 3.8+
- Django 5.1.3
- PostgreSQL (recommended) or SQLite
- Playwright
- Additional requirements:
  - Django Channels (for WebSocket support)
  - Django REST framework (for API endpoints)
  - Django CORS headers (for cross-origin support)

## Features

- Multiple source type support (Web, Telegram, RSS, etc.)
- Real-time WebSocket communication
- RESTful API endpoints
- Configurable stream scheduling
- Built-in task scheduling and execution
- Playwright support for JavaScript-heavy websites
- Automatic content extraction and storage

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rimamedia/newsloom.git
   cd newsloom
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unix
   venv\Scripts\activate     # Windows
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. Run migrations:
   ```bash
   python manage.py migrate
   ```

7. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

8. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

1. Django Settings:
   - DJANGO_SECRET_KEY
   - DEBUG
   - ALLOWED_HOSTS

2. Database Configuration:
   - DB_NAME
   - DB_USER
   - DB_PASSWORD
   - DB_HOST
   - DB_PORT

3. Security Settings:
   - CSRF_TRUSTED_ORIGINS
   - CSRF_COOKIE_SECURE
   - CSRF_USE_SESSIONS

4. Integration Settings (as needed):
   - AWS credentials
   - Articlean API settings
   - Slack/Telegram tokens

### CORS Configuration

1. Add allowed origins in settings.py or .env:
   ```python
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:8000",
       "http://127.0.0.1:8000",
   ]
   ```

2. Configure CORS middleware:
   ```python
   MIDDLEWARE = [
       'corsheaders.middleware.CorsMiddleware',
       # ... other middleware
   ]
   ```

## Running the Project

1. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

2. Start the stream scheduler:
   ```bash
   python manage.py run_streams
   ```

## API Documentation

The API documentation is available at:
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

Authentication is required for most endpoints using:
- Token Authentication
- Session Authentication

## WebSocket Support

WebSocket endpoints are available for real-time updates:
- Chat: `ws://localhost:8000/ws/chat/`
- Stream Status: `ws://localhost:8000/ws/streams/`

## Docker Deployment

1. Build and start containers:
   ```bash
   docker-compose up -d --build
   ```

   This will:
   - Build the Docker image
   - Run collectstatic automatically
   - Configure Nginx to serve static files
   - Mount volumes for static and media files

2. Verify static files setup:
   ```bash
   docker-compose exec web ls /app/staticfiles
   ```

3. Create superuser in container:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

Note: Static and media files are managed through Docker volumes for persistence. The project uses Nginx to serve these files efficiently in both development and production environments.

## Creating Content Sources and Streams

### 1. Create a Source

1. Access the Django admin interface at http://localhost:8000/admin
2. Go to "Sources" section
3. Click "Add Source"
4. Fill in the required fields:
   - Name
   - Link (main website URL)
   - Type (Web, Telegram, RSS, etc.)

### 2. Create a Stream

1. In the Django admin, go to "Streams" section
2. Click "Add Stream"
3. Configure the stream:
   - Name
   - Stream Type
   - Source
   - Frequency
   - Configuration (JSON format)

## Error Handling

- Failed tasks are automatically logged
- Configurable retry mechanisms
- Detailed error reporting in admin interface
- Stream execution statistics tracking

## Security Notes

- Set DEBUG=False in production
- Configure proper CORS settings
- Use HTTPS in production
- Set secure cookie settings
- Configure CSRF protection
- Use environment variables for sensitive data

## Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Contact

RimaMedia - [@rimamedia](https://github.com/rimamedia)

Project Link: [https://github.com/rimamedia/newsloom](https://github.com/rimamedia/newsloom)
