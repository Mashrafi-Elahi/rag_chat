from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import ChatMessageListCreateView, ChatSessionViewSet

router = DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    # Login / Token route added inside the chat app
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # Session & Message routes
    path("", include(router.urls)),
    path(
        "sessions/<uuid:session_id>/messages/",
        ChatMessageListCreateView.as_view(),
        name="chat-messages",
    ),
]