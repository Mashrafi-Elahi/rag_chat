from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# ---------------------------------------------------------------------------
# Swagger / ReDoc schema view
# ---------------------------------------------------------------------------
schema_view = get_schema_view(
    openapi.Info(
        title="KnowledgeNest Accounts API",
        default_version="v1",
        description="""
## KnowledgeNest — Accounts API

Full authentication and user-profile system for KnowledgeNest.

### How to authenticate in Swagger
1. Call **POST /api/accounts/login/** with your email and password.
2. Copy the `tokens.access` value from the response.
3. Click the **Authorize 🔒** button (top-right).
4. In the *apiKey* field, enter: `Bearer <paste_access_token_here>`
5. Click **Authorize** → protected endpoints will now work.

### Endpoints
| Group | Count |
|---|---|
| Authentication (register, login, forgot-password, change-password, logout) | 5 |
| User Profile (get, update, delete) | 3 |
| **Total** | **8** |
        """,
        contact=openapi.Contact(email="support@knowledgenest.ai"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ---------------------------------------------------------------------------
    # JWT token utilities
    # ---------------------------------------------------------------------------
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ---------------------------------------------------------------------------
    # App routes
    # ---------------------------------------------------------------------------
    path("api/accounts/", include("accounts.urls")),
    path("api/knowledge/", include("knowledge.urls")),
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
