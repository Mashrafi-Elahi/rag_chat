import uuid

from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from .models import Document, KnowledgeBase
from .serializers import DocumentSerializer, KnowledgeBaseSerializer


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for user Knowledge Bases.

    Users can only access their own knowledge bases.
    """

    serializer_class = KnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only the authenticated user's knowledge bases.
        """
        return KnowledgeBase.objects.filter(
            owner=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        """
        Automatically assign the owner and generate a unique
        ChromaDB collection ID when creating a knowledge base.
        """
        serializer.save(
            owner=self.request.user,
            chroma_collection_id=f"kb_{uuid.uuid4().hex}",
        )


class DocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD for documents inside a knowledge base.

    GET    /api/knowledge/bases/{kb_id}/documents/
    POST   /api/knowledge/bases/{kb_id}/documents/
    GET    /api/knowledge/bases/{kb_id}/documents/{doc_id}/
    DELETE /api/knowledge/bases/{kb_id}/documents/{doc_id}/
    """

    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        kb_id = self.kwargs["base_id"]
        return Document.objects.filter(
            knowledge_base_id=kb_id,
            knowledge_base__owner=self.request.user,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        kb_id = self.kwargs["base_id"]
        serializer.save(knowledge_base_id=kb_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        document = serializer.instance

        # Trigger ingest pipeline synchronously
        try:
            from .services.ingest import ingest_document
            ingest_document(document)
            document.refresh_from_db()
        except Exception:
            document.refresh_from_db()

        headers = self.get_success_headers(serializer.data)
        return Response(
            DocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )