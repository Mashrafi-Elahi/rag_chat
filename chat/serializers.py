# pyrefly: ignore [missing-import]
from rest_framework import serializers

from knowledge.models import KnowledgeBase
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField(read_only=True)

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

    def validate_knowledge_base(self, value: KnowledgeBase):
        """Make sure the user owns the knowledge base."""
        request = self.context["request"]
        if value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You do not own this knowledge base."
            )
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ChatSessionDetailSerializer(ChatSessionSerializer):
    """Used for retrieve – includes the full message history."""
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ["messages"]


class CreateMessageSerializer(serializers.Serializer):
    """Input for POST /sessions/{id}/messages/"""
    content = serializers.CharField(max_length=10_000, allow_blank=False)

    def create(self, validated_data):
        session: ChatSession = self.context["session"]
        user_content = validated_data["content"]

        # 1. Save the user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )

        # 2. Placeholder assistant reply (replace in Step 7)
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=(
                "This is a placeholder reply. "
                "Real RAG + OpenRouter will be added in Step 7."
            ),
        )

        # Touch updated_at
        session.save(update_fields=["updated_at"])

        return {
            "user_message": user_msg,
            "assistant_message": assistant_msg,
        }