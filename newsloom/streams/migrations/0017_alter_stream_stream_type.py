# Generated by Django 5.1.3 on 2025-01-16 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0016_alter_stream_stream_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='stream_type',
            field=models.CharField(choices=[('sitemap_news', 'Sitemap News Parser'), ('sitemap_blog', 'Sitemap Blog Parser'), ('playwright_link_extractor', 'Playwright Link Extractor'), ('rss_feed', 'RSS Feed Parser'), ('web_article', 'Web Article Scraper'), ('telegram_channel', 'Telegram Channel Monitor'), ('telegram_publish', 'Telegram Links Publisher'), ('article_searcher', 'Article Content Searcher'), ('bing_search', 'Bing Search'), ('google_search', 'Google Search'), ('telegram_bulk_parser', 'Telegram Bulk Parser'), ('news_stream', 'News Stream Processor'), ('doc_publisher', 'Doc Publisher'), ('google_doc_creator', 'Google Doc Creator'), ('telegram_doc_publisher', 'Telegram Doc Publisher'), ('articlean', 'Articlean Processor'), ('web_scraper', 'Web Content Scraper')], max_length=50),
        ),
    ]
