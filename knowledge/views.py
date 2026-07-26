import uuid

from rest_framework import permissions, viewsets

from .models import KnowledgeBase
from .serializers import KnowledgeBaseSerializer


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