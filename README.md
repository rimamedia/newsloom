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

The system leverages Django's powerful ORM and admin interface for configuration management, while a built-in scheduler handles task execution. This combination enables reliable handling of large-scale news monitoring and distribution workflows.

## Key Components

- **Source Management**: Configure and manage multiple news sources (websites, RSS feeds, Telegram channels)
- **Stream Processing**: Define custom processing workflows using stream tasks
- **Content Storage**: Efficient storage and indexing of news content using Django models
- **Publishing System**: Automated content distribution to configured channels
- **Monitoring Dashboard**: Track processing status and system health through Django admin

## Architecture

NewLoom is built on two main pillars:

1. **Django Backend**: Handles data models, API endpoints, and admin interface
2. **Stream Scheduler**: Manages task scheduling and execution
3. **Playwright Integration**: Enables reliable scraping of JavaScript-heavy websites

## Features

- Multiple source type support (Web, Telegram, RSS, etc.)
- Configurable stream scheduling
- Built-in task scheduling and execution
- Playwright support for JavaScript-heavy websites
- Automatic content extraction and storage

## Prerequisites

- Python 3.8+
- Django 5.1.3
- Playwright
- PostgreSQL
- Redis (optional, for caching)

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

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
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

## Docker Deployment

1. Build and start containers:
   ```bash
   docker-compose up -d --build
   ```

2. Create superuser in container:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

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
   - Stream Type (sitemap_news, playwright_link_extractor, etc.)
   - Source (select from previously created sources)
   - Frequency
   - Configuration (JSON format)

### Stream Configuration Examples

#### Sitemap News Parser Configuration
```json
{
    "sitemap_url": "https://example.com/sitemap.xml",
    "max_links": 100,
    "follow_next": false
}
```

#### Playwright Link Extractor Configuration
```json
{
    "url": "https://example.com",
    "link_selector": "article a.headline",
    "max_links": 100
}
```

#### RSS Feed Parser Configuration
```json
{
    "feed_url": "https://example.com/feed.xml",
    "max_entries": 100
}
```

## Monitoring

- Stream status and logs can be viewed in the Django admin interface
- Stream execution logs are stored in the StreamLog model
- Check the console output of the run_streams command for real-time processing information

## Error Handling

- Failed tasks are automatically logged in the StreamLog model
- Streams with failed tasks are marked with 'failed' status
- The scheduler will attempt to retry failed tasks based on configuration

## Development Notes

1. Add new task types:
   - Create a new task function in streams/tasks/
   - Add the task type to Stream.TYPE_CHOICES
   - Create a configuration schema in streams/schemas/
   - Register the task in TASK_MAPPING in streams/tasks/__init__.py

2. Custom task implementation should include:
   - Task parameters (stream_id, configuration)
   - Task function implementation
   - Proper error handling
   - Task completion logging

## Security Notes

- The project includes Django's default security middleware
- Ensure to update SECRET_KEY and set DEBUG=False in production
- Configure proper database credentials in production
- Use environment variables for sensitive configuration
- Implement proper authentication for production deployment
- Regular security updates for all dependencies
- Proper rate limiting for web scraping tasks
- Secure storage of sensitive configuration data

## Best Practices

1. Source Management:
   - Verify source URLs before creation
   - Set appropriate update frequencies
   - Monitor source reliability

2. Stream Configuration:
   - Start with conservative scraping limits
   - Test configurations in development first
   - Monitor resource usage

3. Task Scheduling:
   - Avoid overlapping task schedules
   - Set reasonable retry intervals
   - Monitor task completion times

4. Error Management:
   - Regular log review
   - Set up error notifications
   - Document error resolution steps

## License

MIT License

Copyright (c) 2024 RimaMedia

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Contact

RimaMedia - [@rimamedia](https://github.com/rimamedia)

Project Link: [https://github.com/rimamedia/newsloom](https://github.com/rimamedia/newsloom)

This README provides a basic guide to get started with NewLoom. For production deployment, additional configuration and security measures should be implemented based on specific requirements and environment.

## Development Setup

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

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

5. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Update variables as needed
   ```bash
   cp .env.example .env
   ```

6. Run migrations:
   ```bash
   python manage.py migrate
   ```

7. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

8. Start development servers:
   ```bash
   # Terminal 1: Django server
   python manage.py runserver

   # Terminal 2: Stream scheduler
   python manage.py run_streams
   ```

9. Access the application:
   - Admin interface: http://localhost:8000/admin
   - Home page: http://localhost:8000

For more detailed information, refer to:
- [Django Documentation](https://docs.djangoproject.com/)
- [Playwright Python Documentation](https://playwright.dev/python/)
