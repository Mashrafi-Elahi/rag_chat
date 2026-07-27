import os
import requests
import chromadb
from django.conf import settings
from rest_framework import serializers

from knowledge.models import KnowledgeBase
from .models import ChatMessage, ChatSession

# Cache the model instance globally so it loads only once when first used
_EMBEDDING_MODEL = None

def get_embedding_model():
    """Lazy loader to prevent PyTorch DLL blocks on Django startup/migrations."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDING_MODEL


def generate_rag_response(session, user_query: str) -> str:
    """
    1. Retrieve relevant text chunks from ChromaDB if a KnowledgeBase is linked.
    2. Build prompt with retrieved context.
    3. Call OpenRouter API for the assistant response.
    """
    context_text = ""

    # --- Step 1: ChromaDB Retrieval ---
    if session.knowledge_base and session.knowledge_base.chroma_collection_id:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        try:
            collection = chroma_client.get_collection(
                name=session.knowledge_base.chroma_collection_id
            )
            
            # Fetch lazy-loaded embedding model
            embedding_model = get_embedding_model()
            query_vector = embedding_model.encode(user_query).tolist()
            
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=3,
            )

            if results and results.get("documents"):
                retrieved_docs = results["documents"][0]
                context_text = "\n\n".join(retrieved_docs)
        except Exception:
            context_text = ""

    # --- Step 2: Build Prompt ---
    messages = []
    if context_text:
        system_prompt = (
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the context provided below. If the context does not contain enough "
            "information, state that clearly.\n\n"
            f"Context:\n{context_text}"
        )
    else:
        system_prompt = "You are a helpful AI assistant."

    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_query})

    # --- Step 3: OpenRouter API Call ---
    api_key = getattr(settings, "OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"))
    if not api_key:
        return "Error: OPENROUTER_API_KEY is missing from environment/settings."

    model_name = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-3.5-turbo")

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": messages,
            },
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"OpenRouter Error ({response.status_code}): {response.text}"

    except Exception as e:
        return f"Failed to reach OpenRouter: {str(e)}"


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField(read_only=True)
    knowledge_base = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.all(),
        required=False,
        allow_null=True,
        default=None,  # <-- Crucial fix for optional foreign keys
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

    def validate_knowledge_base(self, value: KnowledgeBase):
        if value is None:
            return value

        request = self.context.get("request")
        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You do not own this knowledge base."
            )
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ChatSessionDetailSerializer(ChatSessionSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ["messages"]


class CreateMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10_000, allow_blank=False)

    def create(self, validated_data):
        session: ChatSession = self.context["session"]
        user_content = validated_data["content"]

        # 1. Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )

        # 2. Generate RAG response directly via helper function above
        reply_content = generate_rag_response(session, user_content)

        # 3. Save assistant response
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=reply_content,
        )

        # Update chat session timestamp
        session.save(update_fields=["updated_at"])

        return {
            "user_message": ChatMessageSerializer(user_msg).data,
            "assistant_message": ChatMessageSerializer(assistant_msg).data,
        }