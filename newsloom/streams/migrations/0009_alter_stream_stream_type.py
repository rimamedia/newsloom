# Generated by Django 5.1.3 on 2024-12-02 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0008_alter_stream_stream_type_streamlog_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='stream_type',
            field=models.CharField(choices=[('sitemap_news', 'Sitemap News Parser'), ('sitemap_blog', 'Sitemap Blog Parser'), ('playwright_link_extractor', 'Playwright Link Extractor'), ('rss_feed', 'RSS Feed Parser'), ('web_article', 'Web Article Scraper'), ('telegram_channel', 'Telegram Channel Monitor'), ('telegram_publish', 'Telegram Links Publisher'), ('telegram_test', 'Telegram Test Publisher'), ('article_searcher', 'Article Content Searcher')], max_length=50),
        ),
    ]