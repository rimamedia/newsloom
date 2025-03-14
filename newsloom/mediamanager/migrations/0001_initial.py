# Generated by Django 5.1.3 on 2024-11-26 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sources', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sources', models.ManyToManyField(blank=True, to='sources.source')),
            ],
            options={
                'verbose_name': 'Media',
                'verbose_name_plural': 'Media',
                'ordering': ['name'],
            },
        ),
    ]
