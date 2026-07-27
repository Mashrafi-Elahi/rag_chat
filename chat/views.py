from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatSession
from .serializers import (
    ChatMessageSerializer,
    ChatSessionDetailSerializer,
    ChatSessionSerializer,
    CreateMessageSerializer,
)


class ChatSessionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET    /api/chat/sessions/
    POST   /api/chat/sessions/
    GET    /api/chat/sessions/{id}/
    DELETE /api/chat/sessions/{id}/
    """
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return ChatSession.objects.none()
        return (
            ChatSession.objects
            .filter(user=self.request.user)
            .select_related("knowledge_base")
            .prefetch_related("messages")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ChatSessionDetailSerializer
        return ChatSessionSerializer


class ChatMessageListCreateView(APIView):
    """
    GET  /api/chat/sessions/{session_id}/messages/
    POST /api/chat/sessions/{session_id}/messages/
    """
    permission_classes = [IsAuthenticated]

    def get_session(self, session_id):
        try:
            return ChatSession.objects.get(
                id=session_id,
                user=self.request.user,
            )
        except ChatSession.DoesNotExist:
            return None

    def get(self, request, session_id):
        session = self.get_session(session_id)
        if session is None:
            return Response(
                {"detail": "Session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = session.messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request, session_id):
        session = self.get_session(session_id)
        if session is None:
            return Response(
                {"detail": "Session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CreateMessageSerializer(
            data=request.data,
            context={"session": session, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(result, status=status.HTTP_201_CREATED)