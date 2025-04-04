# Generated by Django 5.1.5 on 2025-03-10 12:33
from django.apps.registry import Apps
from django.db import migrations


def forward(apps: Apps, schema_editor) -> None:
    from streams.services.periodic_tasks import stream_to_periodic_task
    Stream = apps.get_model("streams", "Stream")
    for stream in Stream.objects.all():
        stream_to_periodic_task(stream)

def reverse(apps: Apps, schema_editor) -> None:
    Stream = apps.get_model("streams", "Stream")
    from streams.services.periodic_tasks import get_periodic_task_by_stream
    for stream in Stream.objects.all():
        periodic_task = get_periodic_task_by_stream(stream)
        if periodic_task:
            periodic_task.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("streams", "0019_alter_stream_stream_type"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
