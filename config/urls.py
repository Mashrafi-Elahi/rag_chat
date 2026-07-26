from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView





urlpatterns = [
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