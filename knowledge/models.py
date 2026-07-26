import uuid

from django.conf import settings
from django.db import models


class KnowledgeBase(models.Model):
    """
    A user-owned knowledge collection.

    Embeddings live in ChromaDB (see chroma_collection_id).
    This table stores metadata only — never vectors.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_bases",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # ChromaDB collection name/id — not an embedding vector
    chroma_collection_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    A single source inside a knowledge base (file or website).

    Extracted text chunks + embeddings are stored in ChromaDB.
    PostgreSQL/SQLite only keeps file/url metadata and processing status.
    """

    class SourceType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"
        TXT = "txt", "TXT"
        WEBSITE = "website", "Website"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    file = models.FileField(upload_to="documents/%Y/%m/%d/", blank=True, null=True)
    source_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    # How many chunks were written to ChromaDB (metadata only)
    chunk_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.source_type})"
