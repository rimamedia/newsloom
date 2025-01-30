# Generated by Django 5.1.5 on 2025-01-30 01:19

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_chatmessagedetail'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessagedetail',
            name='chat',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='message_details', to='chat.chat'),
        ),
        migrations.AddIndex(
            model_name='chatmessagedetail',
            index=models.Index(fields=['chat', 'timestamp'], name='chat_chatme_chat_id_b506e4_idx'),
        ),
        migrations.AddIndex(
            model_name='chatmessagedetail',
            index=models.Index(fields=['chat_message', 'sequence_number'], name='chat_chatme_chat_me_cfdcf1_idx'),
        ),
    ]
