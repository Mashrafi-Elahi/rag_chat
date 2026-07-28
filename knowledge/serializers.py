
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

    def validate_file(self, value):
        if value is None:
            return value

        ALLOWED_SOURCE_EXTENSIONS = {
            Document.SourceType.PDF: {"pdf"},
            Document.SourceType.DOCX: {"docx"},
            Document.SourceType.TXT: {"txt"},
            Document.SourceType.WEBSITE: set(),
        }
        MAX_UPLOAD_MB = 50

        source_type = self.initial_data.get("source_type", "")
        allowed = ALLOWED_SOURCE_EXTENSIONS.get(source_type, set())

        if allowed:
            ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
            if ext not in allowed:
                raise serializers.ValidationError(
                    f"File extension '.{ext}' is not allowed for source type '{source_type}'. "
                    f"Allowed extensions: {', '.join(allowed)}"
                )

        if value.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File size ({value.size // (1024 * 1024)} MB) exceeds the maximum allowed limit of {MAX_UPLOAD_MB} MB."
            )

        return value

    def validate(self, attrs):
        """
        Validation rules:
        - PDF/DOCX/TXT require a file.
        - WEBSITE requires a URL.
        """

        instance = self.instance
        source_type = attrs.get(
            "source_type",
            instance.source_type if instance else None,
        )
        file = attrs.get("file", instance.file if instance else None)
        source_url = attrs.get(
            "source_url",
            instance.source_url if instance else None,
        )

        if source_type == Document.SourceType.WEBSITE:
            if not source_url:
                raise serializers.ValidationError(
                    {"source_url": "A website URL is required for WEBSITE source type."}
                )
        else:
            if not file:
                raise serializers.ValidationError(
                    {"file": f"A file is required for source type '{source_type}'."}
                )

        return attrs
