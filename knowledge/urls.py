from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet, KnowledgeBaseViewSet

router = DefaultRouter()

router.register(
    r"bases",
    KnowledgeBaseViewSet,
    basename="knowledge-base",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "bases/<uuid:base_id>/documents/",
        DocumentViewSet.as_view({"get": "list", "post": "create"}),
        name="knowledge-base-documents",
    ),
    path(
        "bases/<uuid:base_id>/documents/<uuid:id>/",
        DocumentViewSet.as_view({"delete": "destroy"}),
        name="knowledge-base-document-detail",
    ),
]