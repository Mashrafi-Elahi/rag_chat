import uuid

from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Document, KnowledgeBase
from .serializers import DocumentSerializer, KnowledgeBaseSerializer
from .services.ingest import ingest_document


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


class DocumentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, kb_id):
        kb = get_object_or_404(
            KnowledgeBase,
            id=kb_id,
            owner=request.user
        )

        documents = Document.objects.filter(knowledge_base=kb)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request, kb_id):
        kb = get_object_or_404(
            KnowledgeBase,
            id=kb_id,
            owner=request.user
        )

        serializer = DocumentSerializer(data=request.data)

        if serializer.is_valid():
            document = serializer.save(knowledge_base=kb)
            ingest_document(document)
            document.refresh_from_db()

            return Response(
                DocumentSerializer(document).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class DocumentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, kb_id, doc_id):
        return get_object_or_404(
            Document,
            id=doc_id,
            knowledge_base__id=kb_id,
            knowledge_base__owner=request.user,
        )

    def get(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        serializer = DocumentSerializer(document)
        return Response(serializer.data)

    def put(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        serializer = DocumentSerializer(document, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        serializer = DocumentSerializer(
            document,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        document.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )