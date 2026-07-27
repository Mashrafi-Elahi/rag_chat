"""
chat/serializers.py

Serializers are responsible ONLY for:
  - Translating between ORM objects and JSON.
  - Validating HTTP input data.
  - Enforcing field-level ownership rules.

All RAG / LLM / embedding logic lives in chat.services.rag.
"""

from rest_framework import serializers

from knowledge.models import KnowledgeBase

from .models import ChatMessage, ChatSession
from .services.rag import generate_rag_response


class ChatMessageSerializer(serializers.ModelSerializer):
    """Read serializer for a single chat message."""

    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    """
    List / create serializer for chat sessions.

    - `knowledge_base` is optional; when supplied the caller must own it.
    - `message_count` is a computed read-only field.
    """

    message_count = serializers.SerializerMethodField(read_only=True)
    knowledge_base = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = ChatSession
        fields = [
            "id",
            "title",
            "knowledge_base",
            "created_at",
            "updated_at",
            "message_count",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "message_count",
        ]

    def get_message_count(self, obj):
        return obj.messages.count()

    def validate_knowledge_base(self, value: KnowledgeBase | None):
        """Ensure the authenticated user owns the knowledge base they're linking."""
        if value is None:
            return value

        request = self.context.get("request")
        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You do not own this knowledge base."
            )
        return value

    def create(self, validated_data):
        # Owner is always the authenticated request user — never trusted from input.
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ChatSessionDetailSerializer(ChatSessionSerializer):
    """Retrieve serializer — includes the full message list."""

    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ["messages"]


class CreateMessageSerializer(serializers.Serializer):
    """
    Write-only serializer for posting a new user message.

    On save:
      1. Persists the user message.
      2. Delegates to the RAG service for the assistant reply.
      3. Persists the assistant message.
      4. Returns both messages so the view can respond with the full turn.
    """

    content = serializers.CharField(max_length=10_000, allow_blank=False)

    def create(self, validated_data):
        session: ChatSession = self.context["session"]
        user_content = validated_data["content"]

        # 1. Persist the user message.
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )

        # 2. Generate the assistant reply via the RAG service.
        #    This is the ONLY call to business logic from within a serializer.
        reply_content = generate_rag_response(session, user_content)

        # 3. Persist the assistant message.
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=reply_content,
        )

        # 4. Bump the session's updated_at timestamp.
        session.save(update_fields=["updated_at"])

        return {
            "user_message": ChatMessageSerializer(user_msg).data,
            "assistant_message": ChatMessageSerializer(assistant_msg).data,
        }