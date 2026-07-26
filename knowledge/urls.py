from django.urls import path
from .views import DocumentListCreateAPIView, DocumentDetailAPIView

urlpatterns = [
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