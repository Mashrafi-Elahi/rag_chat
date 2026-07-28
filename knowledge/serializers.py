from rest_framework import serializers

from .models import KnowledgeBase, Document


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = (
            "id",
            "owner",
            "name",
            "description",
            "chroma_collection_id",
            "document_count",
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

    def get_document_count(self, obj):
        return obj.documents.count()


class DocumentSerializer(serializers.ModelSerializer):

    ALLOWED_SOURCE_EXTENSIONS = {
        "pdf": {"pdf"},
        "docx": {"docx"},
        "txt": {"txt"},
        "website": set(),
    }

    MAX_UPLOAD_MB = 50

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
        """
        Validate uploaded files:
        - Only allow pdf/docx/txt
        - Limit file size
        """

        if value is None:
            return value

        # Get extension
        if "." in value.name:
            extension = value.name.rsplit(".", 1)[-1].lower()
        else:
            extension = ""

        # Get source type from request data
        source_type = self.initial_data.get("source_type")

        allowed_extensions = self.ALLOWED_SOURCE_EXTENSIONS.get(
            source_type,
            set()
        )

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                {
                    "file": (
                        f"File type '.{extension}' is not allowed for "
                        f"source type '{source_type}'. "
                        f"Allowed: {', '.join(allowed_extensions)}"
                    )
                }
            )

        # Check size
        max_size = self.MAX_UPLOAD_MB * 1024 * 1024

        if value.size > max_size:
            raise serializers.ValidationError(
                {
                    "file": (
                        f"File size exceeds the "
                        f"{self.MAX_UPLOAD_MB}MB limit."
                    )
                }
            )

        return value

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
                    {
                        "source_url": "A website URL is required."
                    }
                )

        else:

            if not file:
                raise serializers.ValidationError(
                    {
                        "file": "A file is required for this source type."
                    }
                )

        return attrs