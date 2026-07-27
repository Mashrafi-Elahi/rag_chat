from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentDetailAPIView, DocumentListCreateAPIView, KnowledgeBaseViewSet

router = DefaultRouter()

router.register(
    r"bases",
    KnowledgeBaseViewSet,
    basename="knowledge-base",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "bases/<uuid:kb_id>/documents/",
        DocumentListCreateAPIView.as_view(),
        name="document-list-create",
    ),
    path(
        "bases/<uuid:kb_id>/documents/<uuid:doc_id>/",
        DocumentDetailAPIView.as_view(),
        name="document-detail",
    ),
]