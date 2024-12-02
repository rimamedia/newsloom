# Generated by Django 5.1.3 on 2024-12-02 15:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0007_luigitasklog_output_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stream',
            name='stream_type',
            field=models.CharField(choices=[('sitemap_news', 'Sitemap News Parser'), ('sitemap_blog', 'Sitemap Blog Parser'), ('playwright_link_extractor', 'Playwright Link Extractor'), ('rss_feed', 'RSS Feed Parser'), ('web_article', 'Web Article Scraper'), ('telegram_channel', 'Telegram Channel Monitor'), ('telegram_publish', 'Telegram Links Publisher'), ('telegram_test', 'Telegram Test Publisher')], max_length=50),
        ),
        migrations.CreateModel(
            name='StreamLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('running', 'Running')], default='running', max_length=20)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('result', models.JSONField(blank=True, help_text='Task execution results in JSON format', null=True)),
                ('stream', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='streams.stream')),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.DeleteModel(
            name='LuigiTaskLog',
        ),
        migrations.AddIndex(
            model_name='streamlog',
            index=models.Index(fields=['stream', 'status'], name='streams_str_stream__95fe98_idx'),
        ),
        migrations.AddIndex(
            model_name='streamlog',
            index=models.Index(fields=['started_at'], name='streams_str_started_1d2218_idx'),
        ),
    ]