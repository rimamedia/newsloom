# Generated by Django 5.1.5 on 2025-01-18 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streams', '0017_alter_stream_stream_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='StreamExecutionStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('execution_start', models.DateTimeField(auto_now_add=True)),
                ('execution_end', models.DateTimeField(null=True)),
                ('streams_attempted', models.IntegerField(default=0)),
                ('streams_succeeded', models.IntegerField(default=0)),
                ('streams_failed', models.IntegerField(default=0)),
                ('total_execution_time', models.DurationField(null=True)),
            ],
            options={
                'ordering': ['-execution_start'],
                'indexes': [models.Index(fields=['execution_start'], name='streams_str_executi_df3746_idx')],
            },
        ),
    ]
