<<<<<<< HEAD
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatSessionViewSet
=======
# pyrefly: ignore [missing-import]
from django.urls import path, include
# pyrefly: ignore [missing-import]
from rest_framework.routers import DefaultRouter

from .views import ChatSessionViewSet, ChatMessageListCreateView
>>>>>>> 908f063ed97abdc05568b62841a142e503db4cb3

router = DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    path("", include(router.urls)),
<<<<<<< HEAD
=======
    path(
        "sessions/<uuid:session_id>/messages/",
        ChatMessageListCreateView.as_view(),
        name="chat-messages",
    ),
>>>>>>> 908f063ed97abdc05568b62841a142e503db4cb3
]