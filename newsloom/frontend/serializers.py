from chat.models import Chat, ChatMessage
from django.contrib.auth.models import User
from rest_framework import serializers
from streams.models import (
    Stream,
    StreamExecutionStats,
    StreamLog,
    TelegramDocPublishLog,
    TelegramPublishLog,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["email"]


class ChatMessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "chat", "user", "message", "response", "timestamp"]
        read_only_fields = ["user", "timestamp"]


class ChatSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Chat
        fields = ["id", "user", "title", "created_at", "updated_at", "messages"]
        read_only_fields = ["user", "created_at", "updated_at"]


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stream
        fields = [
            "id",
            "name",
            "stream_type",
            "source",
            "media",
            "frequency",
            "configuration",
            "status",
            "last_run",
            "next_run",
            "created_at",
            "updated_at",
            "version",
        ]


class StreamLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamLog
        fields = [
            "id",
            "stream",
            "status",
            "started_at",
            "completed_at",
            "error_message",
            "result",
        ]


class StreamExecutionStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamExecutionStats
        fields = [
            "id",
            "execution_start",
            "execution_end",
            "streams_attempted",
            "streams_succeeded",
            "streams_failed",
            "total_execution_time",
        ]


class TelegramPublishLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramPublishLog
        fields = ["id", "news", "media", "published_at"]


class TelegramDocPublishLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramDocPublishLog
        fields = ["id", "doc", "media", "published_at"]
