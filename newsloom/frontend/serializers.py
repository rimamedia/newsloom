from agents.models import Agent
from chat.models import Chat, ChatMessage
from django.contrib.auth import get_user_model
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
from streams.tasks import TASK_CONFIG_EXAMPLES


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


class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "password")


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


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        """Meta configuration for SourceSerializer."""

        model = Source
        fields = ["id", "name", "link", "type", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


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


class StreamSerializer(serializers.ModelSerializer):
    """Serializer for Stream model with source and media update capabilities."""

    source = SourceSerializer(read_only=True)
    media = MediaSerializer(read_only=True)

    configuration_examples = serializers.SerializerMethodField(read_only=True)

    source_id = serializers.PrimaryKeyRelatedField(
        queryset=Source.objects.all(),
        source="source",
        required=False,
        allow_null=True,
        write_only=True,
    )
    media_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(),
        source="media",
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        """Meta configuration for StreamSerializer."""

        model = Stream
        fields = [
            "id",
            "name",
            "stream_type",
            "source",
            "media",
            "source_id",
            "media_id",
            "frequency",
            "configuration",
            "status",
            "last_run",
            "next_run",
            "created_at",
            "updated_at",
            "version",
            "configuration_examples",
        ]
        read_only_fields = ["created_at", "updated_at", "last_run", "next_run"]

    def get_configuration_examples(self, obj):
        return TASK_CONFIG_EXAMPLES


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
    media = MediaSerializer(read_only=True)

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


class NewsCreateSerializer(serializers.ModelSerializer):
    source = serializers.PrimaryKeyRelatedField(queryset=Source.objects.all())
    
    class Meta:
        """Meta configuration for NewsCreateSerializer."""
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


class SourceIdSerializer(serializers.Serializer):
    source_ids = serializers.ListSerializer(child=serializers.PrimaryKeyRelatedField(queryset=Source.objects.all()))


class StatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class StatusWithResultResponseSerializer(StatusResponseSerializer):
    result = serializers.JSONField()


class ChatMessageRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    chat_id = serializers.PrimaryKeyRelatedField(queryset=Chat.objects.all(), required=False)


class ChatMessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    chat_id = serializers.PrimaryKeyRelatedField(queryset=Chat.objects.all(), required=False)
    response = serializers.CharField()
    timestamp = serializers.DateTimeField(required=False)
