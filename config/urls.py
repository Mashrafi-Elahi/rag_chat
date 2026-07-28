from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="RAG Chat API",
        default_version="v1",
        description="API documentation for the RAG Chat application",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "RAG Chat API",
        "docs": "/api/docs/",
    })


urlpatterns = [
    # 🩺 Health check / root
    path("", health_check, name="health-check"),

    # Admin
    path("admin/", admin.site.urls),

    # 🔐 Auth (JWT)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 👤 Accounts
    path("api/accounts/", include("accounts.urls")),

    # 📚 Knowledge (PDF/DOCX/TXT upload lives here)
    path("api/knowledge/", include("knowledge.urls")),

    # 💬 Chat
    path("api/chat/", include("chat.urls")),

    # ---------------------------------------------------------------------------
    # API documentation
    # Swagger UI  : /api/docs/
    # ReDoc        : /api/redoc/
    # OpenAPI JSON : /api/swagger.json
    # ---------------------------------------------------------------------------
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    path(
        "api/swagger.json",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
]

# 📁 Serve uploaded files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )