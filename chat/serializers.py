"""
chat/serializers.py

Responsible only for:
- ORM <-> JSON conversion
- Validation
- Ownership rules
"""

from rest_framework import serializers

from knowledge.models import KnowledgeBase

from .models import ChatMessage, ChatSession
from .services.rag import generate_rag_response


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Read serializer for chat messages.
    """

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "content",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "role",
            "created_at",
        ]


class ChatSessionSerializer(serializers.ModelSerializer):

    message_count = serializers.SerializerMethodField()

    knowledge_base = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.all(),
        required=False,
        allow_null=True,
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


    def validate_knowledge_base(self, value):
        """
        Ensure user owns selected knowledge base.
        """

        if value is not None:

            request = self.context.get("request")

            if request and value.owner_id != request.user.id:
                raise serializers.ValidationError(
                    "You do not own this knowledge base."
                )

        return value


    def create(self, validated_data):

        validated_data["user"] = (
            self.context["request"].user
        )

        return super().create(validated_data)



class ChatSessionDetailSerializer(ChatSessionSerializer):

    messages = ChatMessageSerializer(
        many=True,
        read_only=True
    )

    class Meta(ChatSessionSerializer.Meta):

        fields = ChatSessionSerializer.Meta.fields + [
            "messages"
        ]



class CreateMessageSerializer(serializers.Serializer):

    content = serializers.CharField(
        max_length=10000,
        allow_blank=False
    )


    def create(self, validated_data):

        session = self.context["session"]

        user_content = validated_data["content"]


        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )


        reply_content = generate_rag_response(
            session,
            user_content
        )


        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=reply_content,
        )


        session.save(
            update_fields=[
                "updated_at"
            ]
        )


        return {
            "user_message": ChatMessageSerializer(
                user_msg
            ).data,

            "assistant_message": ChatMessageSerializer(
                assistant_msg
            ).data,
        }