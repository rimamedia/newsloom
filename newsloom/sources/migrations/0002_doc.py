# Generated by Django 5.1.3 on 2024-12-12 15:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mediamanager', '0001_initial'),
        ('sources', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Doc',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link', models.URLField(unique=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('text', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('new', 'New'), ('edit', 'Edit'), ('publish', 'Publish')], default='new', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('media', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='docs', to='mediamanager.media')),
            ],
            options={
                'verbose_name': 'Doc',
                'verbose_name_plural': 'Docs',
                'ordering': ['-published_at'],
                'indexes': [models.Index(fields=['-published_at'], name='sources_doc_publish_395ed0_idx'), models.Index(fields=['link'], name='sources_doc_link_aa0efc_idx')],
            },
        ),
    ]
