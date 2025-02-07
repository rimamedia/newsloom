from agents.models import Agent
from chat.models import Chat, ChatMessage
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import User
from mediamanager.models import Examples, Media
from rest_framework import serializers
from sources.models import Doc, News, Source
from streams.models import (
    Stream,
    StreamExecutionStats,
    StreamLog,
    TelegramDocPublishLog,
    TelegramPublishLog,
)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        """Meta configuration for RegisterSerializer."""

        model = get_user_model()
        fields = ("id", "username", "password", "email", "first_name", "last_name")
        extra_kwargs = {"password": {"write_only": True}, "email": {"required": True}}

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for UserSerializer."""

        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["email"]


class ChatMessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        """Meta configuration for ChatMessageSerializer."""

        model = ChatMessage
        fields = ["id", "chat", "user", "message", "response", "timestamp"]
        read_only_fields = ["user", "timestamp"]


class ChatSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        """Meta configuration for ChatSerializer."""

        model = Chat
        fields = ["id", "user", "title", "created_at", "updated_at", "messages"]
        read_only_fields = ["user", "created_at", "updated_at"]


class StreamSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for StreamSerializer."""

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
        """Meta configuration for StreamLogSerializer."""

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
        """Meta configuration for StreamExecutionStatsSerializer."""

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
        """Meta configuration for TelegramPublishLogSerializer."""

        model = TelegramPublishLog
        fields = ["id", "news", "media", "published_at"]


class TelegramDocPublishLogSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for TelegramDocPublishLogSerializer."""

        model = TelegramDocPublishLog
        fields = ["id", "doc", "media", "published_at"]


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for SourceSerializer."""

        model = Source
        fields = ["id", "name", "link", "type", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class NewsSerializer(serializers.ModelSerializer):
    source = SourceSerializer(read_only=True)

    class Meta:
        """Meta configuration for NewsSerializer."""

        model = News
        fields = [
            "id",
            "source",
            "link",
            "title",
            "text",
            "created_at",
            "published_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class DocSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for DocSerializer."""

        model = Doc
        fields = [
            "id",
            "media",
            "link",
            "google_doc_link",
            "title",
            "text",
            "status",
            "created_at",
            "published_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for AgentSerializer."""

        model = Agent
        fields = [
            "id",
            "name",
            "description",
            "provider",
            "system_prompt",
            "user_prompt_template",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_user_prompt_template(self, value):
        if "{news}" not in value:
            raise serializers.ValidationError(
                "Prompt template must contain {news} placeholder"
            )
        return value


class ExamplesSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for ExamplesSerializer."""

        model = Examples
        fields = ["id", "media", "text", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class MediaSerializer(serializers.ModelSerializer):
    examples = ExamplesSerializer(many=True, read_only=True)
    sources = SourceSerializer(many=True, read_only=True)

    class Meta:
        """Meta configuration for MediaSerializer."""

        model = Media
        fields = ["id", "name", "sources", "examples", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
