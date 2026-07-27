"""
chat/tests.py

Unit tests for the chat app.

Coverage:
  - ChatSession: create, list, retrieve, delete (ownership enforced)
  - ChatMessage: list messages, post message
  - Ownership: user A cannot access user B's sessions
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from chat.models import ChatMessage, ChatSession

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email, password="StrongPass123!"):
    return User.objects.create_user(email=email, password=password)


def make_session(user, title="Test Session"):
    return ChatSession.objects.create(user=user, title=title)


# ---------------------------------------------------------------------------
# ChatSession CRUD
# ---------------------------------------------------------------------------

class ChatSessionCreateTests(APITestCase):
    """POST /api/chat/sessions/"""

    def setUp(self):
        self.user = make_user("alice@example.com")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/chat/sessions/"

    def test_create_session_no_kb(self):
        """A session without a knowledge base is created successfully."""
        response = self.client.post(self.url, {"title": "My Chat"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "My Chat")
        self.assertIsNone(response.data["knowledge_base"])

    def test_create_session_unauthenticated(self):
        """Unauthenticated request returns 401."""
        self.client.logout()
        response = self.client.post(self.url, {"title": "My Chat"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_session_sets_owner_from_token(self):
        """The session owner is always taken from the JWT — not from request body."""
        response = self.client.post(self.url, {"title": "Ownership Test"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ChatSession.objects.get(id=response.data["id"])
        self.assertEqual(session.user, self.user)


class ChatSessionListTests(APITestCase):
    """GET /api/chat/sessions/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        make_session(self.alice, "Alice Session")
        make_session(self.bob, "Bob Session")
        self.client.force_authenticate(user=self.alice)

    def test_list_returns_only_own_sessions(self):
        """User only sees their own sessions — never another user's."""
        response = self.client.get("/api/chat/sessions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [s["title"] for s in response.data["results"]]
        self.assertIn("Alice Session", titles)
        self.assertNotIn("Bob Session", titles)


class ChatSessionRetrieveTests(APITestCase):
    """GET /api/chat/sessions/{id}/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        self.alice_session = make_session(self.alice, "Alice Only")
        self.bob_session = make_session(self.bob, "Bob Only")

    def test_retrieve_own_session(self):
        """Owner can retrieve their session."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"/api/chat/sessions/{self.alice_session.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Alice Only")

    def test_retrieve_other_users_session_returns_404(self):
        """Accessing another user's session returns 404 — not 403."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"/api/chat/sessions/{self.bob_session.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ChatSessionDeleteTests(APITestCase):
    """DELETE /api/chat/sessions/{id}/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        self.alice_session = make_session(self.alice)
        self.bob_session = make_session(self.bob)

    def test_delete_own_session(self):
        """Owner can delete their session."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.delete(f"/api/chat/sessions/{self.alice_session.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatSession.objects.filter(id=self.alice_session.id).exists())

    def test_delete_other_users_session_returns_404(self):
        """Cannot delete another user's session."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.delete(f"/api/chat/sessions/{self.bob_session.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# ChatMessage
# ---------------------------------------------------------------------------

class ChatMessageListTests(APITestCase):
    """GET /api/chat/sessions/{session_id}/messages/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.session = make_session(self.alice)
        ChatMessage.objects.create(
            session=self.session, role=ChatMessage.Role.USER, content="Hello"
        )
        ChatMessage.objects.create(
            session=self.session, role=ChatMessage.Role.ASSISTANT, content="Hi!"
        )
        self.client.force_authenticate(user=self.alice)

    def test_list_messages(self):
        """All messages in the session are returned in order."""
        response = self.client.get(
            f"/api/chat/sessions/{self.session.id}/messages/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["role"], ChatMessage.Role.USER)
        self.assertEqual(response.data[1]["role"], ChatMessage.Role.ASSISTANT)

    def test_list_messages_other_users_session_returns_404(self):
        """Cannot list messages from another user's session."""
        bob = make_user("bob@example.com")
        self.client.force_authenticate(user=bob)
        response = self.client.get(
            f"/api/chat/sessions/{self.session.id}/messages/"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ChatMessageCreateTests(APITestCase):
    """POST /api/chat/sessions/{session_id}/messages/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.session = make_session(self.alice)
        self.client.force_authenticate(user=self.alice)
        self.url = f"/api/chat/sessions/{self.session.id}/messages/"

    @patch("chat.services.rag.generate_rag_response", return_value="Mocked reply")
    def test_post_message_creates_user_and_assistant_messages(self, _mock_rag):
        """
        Posting a message creates both a user message and an assistant reply.
        The RAG service is mocked so the test does not require OpenRouter or ChromaDB.
        """
        response = self.client.post(self.url, {"content": "What is RAG?"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user_message", response.data)
        self.assertIn("assistant_message", response.data)
        self.assertEqual(response.data["user_message"]["content"], "What is RAG?")
        self.assertEqual(response.data["assistant_message"]["content"], "Mocked reply")
        self.assertEqual(ChatMessage.objects.filter(session=self.session).count(), 2)

    def test_post_empty_content_returns_400(self):
        """Empty message content is rejected with 400."""
        response = self.client.post(self.url, {"content": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_message_unauthenticated_returns_401(self):
        """Unauthenticated request is rejected with 401."""
        self.client.logout()
        response = self.client.post(self.url, {"content": "Hello"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
