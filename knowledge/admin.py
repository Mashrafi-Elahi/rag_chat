from django.contrib import admin

from .models import Document, KnowledgeBase


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "chroma_collection_id", "created_at")
    search_fields = ("name", "owner__email")
    list_filter = ("created_at",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "knowledge_base", "source_type", "status", "chunk_count", "created_at")
    list_filter = ("source_type", "status", "created_at")
    search_fields = ("title", "source_url")
