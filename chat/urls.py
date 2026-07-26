# pyrefly: ignore [missing-import]
from django.urls import path, include
# pyrefly: ignore [missing-import]
from rest_framework.routers import DefaultRouter

from .views import ChatSessionViewSet, ChatMessageListCreateView

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