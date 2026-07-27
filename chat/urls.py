"""
chat/urls.py

Registers URL routes for the chat app ONLY:
  - /api/chat/sessions/              → ChatSessionViewSet (list, create, retrieve, destroy)
  - /api/chat/sessions/<id>/messages/ → ChatMessageListCreateView (list, create)

JWT token endpoints (token/, token/refresh/) are registered at the project
level in config/urls.py and do NOT belong in the chat app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatMessageListCreateView, ChatSessionViewSet

router = DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "sessions/<uuid:session_id>/messages/",
        ChatMessageListCreateView.as_view(),
        name="chat-messages",
    ),
]