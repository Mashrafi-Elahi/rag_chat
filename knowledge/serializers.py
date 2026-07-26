
from rest_framework import serializers

from .models import KnowledgeBase, Document


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBase
        fields = (
            "id",
            "owner",
            "name",
            "description",
            "chroma_collection_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "chroma_collection_id",
            "created_at",
            "updated_at",
        )


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
            "id",
            "knowledge_base",
            "title",
            "source_type",
            "file",
            "source_url",
            "status",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "knowledge_base",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        """
        Validation rules:
        - PDF/DOCX/TXT require a file.
        - WEBSITE requires a URL.
        """

        source_type = attrs.get("source_type")

        file = attrs.get("file")
        source_url = attrs.get("source_url")

        if source_type == Document.SourceType.WEBSITE:
            if not source_url:
                raise serializers.ValidationError(
                    {"source_url": "A website URL is required."}
                )

        else:
            if not file:
                raise serializers.ValidationError(
                    {"file": "A file is required for this source type."}
                )

        return attrs