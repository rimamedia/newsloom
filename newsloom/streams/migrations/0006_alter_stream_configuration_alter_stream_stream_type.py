# Generated by Django 5.1.3 on 2024-11-29 01:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0005_alter_stream_stream_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='configuration',
            field=models.JSONField(help_text='Stream-specific configuration parameters in JSON format.'),
        ),
        migrations.AlterField(
            model_name='stream',
            name='stream_type',
            field=models.CharField(choices=[('sitemap_news', 'Sitemap News Parser'), ('sitemap_blog', 'Sitemap Blog Parser'), ('playwright_link_extractor', 'Playwright Link Extractor'), ('rss_feed', 'RSS Feed Parser'), ('web_article', 'Web Article Scraper'), ('telegram_channel', 'Telegram Channel Monitor'), ('telegram_publish', 'Telegram Links Publisher')], max_length=50),
        ),
    ]
