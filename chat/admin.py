from django.contrib import admin

from .models import ChatMessage, ChatSession


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "knowledge_base", "created_at", "updated_at")
    search_fields = ("title", "user__email")
    list_filter = ("created_at",)
    list_select_related = ("user", "knowledge_base")  # prevents N+1 on list page
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "created_at")
    list_filter = ("role", "created_at")
