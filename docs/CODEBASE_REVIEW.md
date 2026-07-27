# KnowledgeNest AI — Complete DRF Codebase Review

**Reviewer:** Senior Software Engineer / Technical Architect  
**Project:** KnowledgeNest AI (RAG Chat Application)  
**Stack:** Django 6 + Django REST Framework + JWT + ChromaDB  
**Review Date:** 2026-07-27  
**Codebase State:** Scaffold complete — HTTP layer (serializers, views, URLs) not yet implemented

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Review](#2-architecture-review)
3. [Strengths](#3-strengths)
4. [Weaknesses](#4-weaknesses)
5. [Bug Report](#5-bug-report)
6. [Missing Features](#6-missing-features)
7. [Security Findings](#7-security-findings)
8. [Performance Findings](#8-performance-findings)
9. [API Review](#9-api-review)
10. [Code Quality Review](#10-code-quality-review)
11. [Step-by-Step Learning Guide](#11-step-by-step-learning-guide)
12. [Prioritized Improvement Roadmap](#12-prioritized-improvement-roadmap)
13. [Refactoring Recommendations](#13-refactoring-recommendations)
14. [Production Readiness Checklist](#14-production-readiness-checklist)
15. [Learning Notes](#15-learning-notes)
16. [Action Plan](#16-action-plan)

---

## 1. Executive Summary

The project has a solid, well-thought-out foundation. The data model is clean, the architecture
decision to separate SQL metadata from ChromaDB vectors is correct and production-grade, and the
documentation is comprehensive for a learning project. The admin layer is complete and usable.

However, the entire HTTP layer — serializers, views, and URL routes — has not been implemented
yet. Additionally, the existing settings contain several issues that would be dangerous if carried
into a deployed environment without change.

| Area | Status |
|------|--------|
| Models + Migrations | Complete |
| Admin | Complete |
| Settings / Config | Complete (with issues to fix) |
| JWT token endpoints | Working |
| Serializers | Not implemented |
| Views / ViewSets | Not implemented |
| URL routes (accounts/knowledge/chat) | Not implemented |
| Services (ingest / RAG) | Not implemented |
| Tests | Not implemented |

**Overall completion: ~20% of a production-ready system.**  
**Next action: implement Step 2 — accounts serializers, views, and URLs.**

---

## 2. Architecture Review

### 2.1 Folder Structure

```
rag_chat/
├── config/          # Project-wide: settings, root URLs, JWT wiring
├── accounts/        # Custom User model — email-based auth
├── knowledge/       # KnowledgeBase + Document models
├── chat/            # ChatSession + ChatMessage models
├── docs/            # Architecture + testing guides
├── manage.py
├── requirements.txt
└── .env.example
```

Each Django app owns exactly one business domain. This is the correct pattern.

### 2.2 How the Layers Connect

```
Client HTTP Request
        │
        ▼
config/urls.py          → dispatches to the right app URL file
        │
        ▼
accounts/views.py       → checks permission (JWT / AllowAny)
knowledge/views.py      → calls serializer
chat/views.py           → calls model queryset (filtered by request.user)
        │
        ▼
Serializer              → validates input, shapes output JSON
        │
        ▼
Model / QuerySet        → SQL operations (always scoped to request.user)
        │
        ├── SQLite / PostgreSQL   (metadata + chat history)
        └── ChromaDB              (vectors + chunk text — ingest/query only)
        │
        ▼
JSON Response → Client
```

### 2.3 Database Responsibility Split

| Store | Owns | Never stores |
|-------|------|--------------|
| SQL (Django models) | Users, KB names, file paths, status, chat history | Embedding float arrays |
| ChromaDB | Vectors, chunk text, chunk metadata | Passwords, JWT tokens, full user tables |

This split is the single most important architectural decision in the project. It is correct.

### 2.4 Primary Key Strategy

| Model | PK Type | Reason |
|-------|---------|--------|
| `User` | `BigAutoField` (integer) | Inherited from `AbstractUser` |
| `KnowledgeBase` | `UUIDField` | Prevents ID enumeration in URLs |
| `Document` | `UUIDField` | Prevents ID enumeration in URLs |
| `ChatSession` | `UUIDField` | Prevents ID enumeration in URLs |
| `ChatMessage` | `UUIDField` | Prevents ID enumeration in URLs |

**Inconsistency:** `User` uses an integer PK while all domain models use UUID. This is because
`AbstractUser` sets the PK to `BigAutoField` by default. Accept this inconsistency — changing it
now requires a complex migration. For future projects, use `AbstractBaseUser` if you need a UUID
user PK from the start.

---

## 3. Strengths

### 3.1 Correct Hybrid Storage Architecture
The separation of SQL (metadata) and ChromaDB (vectors) mirrors how production RAG systems are
built. Beginners often try to store embeddings in PostgreSQL as JSON arrays — this project correctly
forbids that from the start.

### 3.2 Custom User Model with Email Authentication
Setting `AUTH_USER_MODEL = "accounts.User"` before the first migration is the correct Django
approach. Changing the user model after migrations exist is painful and error-prone. Getting this
right from the beginning shows good architectural planning.

### 3.3 UUID Primary Keys on Domain Models
UUIDs prevent sequential ID guessing. A user cannot discover another user's knowledge base by
incrementing an integer. This is a meaningful security improvement over auto-increment integers.

### 3.4 TextChoices Enums
Using `Document.Status.PENDING` instead of the raw string `"pending"` prevents typos, enables
IDE autocomplete, and makes refactoring safe. This is the modern Django 3.0+ pattern.

### 3.5 Consistent FK Reference Pattern
All foreign keys to the user model use `settings.AUTH_USER_MODEL` instead of importing
`accounts.User` directly. This is the required DRF pattern — it prevents circular imports and
works even if the auth model is swapped later.

### 3.6 `related_name` on Every ForeignKey
```python
owner = models.ForeignKey(..., related_name="knowledge_bases")
```
This enables clean reverse lookups: `user.knowledge_bases.all()`, `kb.documents.all()`,
`session.messages.all()`. Without `related_name`, you'd use the ugly auto-generated
`knowledgebase_set` syntax.

### 3.7 Comprehensive Documentation
The `README.md`, `GUIDE.md`, `docs/VECTOR_DB.md`, and `docs/API_TESTING.md` form a complete
learning path. This level of documentation is unusual and valuable.

### 3.8 Admin Layer
All three apps have properly configured, usable admin classes with search, filtering, and
appropriate inline displays (`ChatMessageInline` on `ChatSessionAdmin`).

---

## 4. Weaknesses

### 4.1 Entire HTTP Layer Is Missing
Serializers, views, and URL routes do not exist yet. The project cannot handle any API request
beyond JWT token issuance.

### 4.2 Settings Have Production-Unsafe Defaults
Three settings default to dangerous values if environment variables are not set. See Section 5
(Bug Report) for full details.

### 4.3 No Services Layer
`knowledge/services/` and `chat/services/` directories are described in the README but do not
exist. All ingest and RAG logic will need a home when Steps 6–7 are implemented.

### 4.4 Redundant Name Fields on User
`AbstractUser` provides `first_name` and `last_name`. The custom `User` model adds `full_name`.
All three columns exist in the database (confirmed in the migration) but only `full_name` is
intended for use. The other two are unused dead columns.

### 4.5 No Token Blacklisting
There is no way to log users out. A stolen JWT remains valid for 60 minutes (access) or 7 days
(refresh) with no mechanism to invalidate it.

### 4.6 No Tests
All three `tests.py` files contain only the default placeholder comment. There is no test coverage
for any model, view, serializer, or service.

### 4.7 No File Upload Validation
`Document.file` is a `FileField` with no restriction on file type or size. Any file can be
uploaded.

---

## 5. Bug Report

---

### BUG-001 — Insecure Default SECRET_KEY

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | `config/settings.py:20` |
| **Status** | Exists in current codebase |

**What the problem is:**
```python
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me-in-production")
```
If the `SECRET_KEY` environment variable is not set, Django uses the hardcoded fallback. In
production, this means JWT tokens, session cookies, CSRF tokens, and password reset links are all
signed with a publicly known key.

**Why it happens:**
Developers add a fallback so the project runs during development without configuration. The
convenience becomes a critical vulnerability in deployment.

**How to identify it in the future:**
Search settings files for `os.getenv("SECRET_KEY", ...)`. Any non-empty string default is a
security issue.

**The correct approach:**
```python
import sys

_secret = os.getenv("SECRET_KEY")
if not _secret:
    if any(cmd in sys.argv for cmd in ("runserver", "test", "shell")):
        _secret = "dev-only-insecure-do-not-deploy"
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(50))\""
        )
SECRET_KEY = _secret
```

**Why this is better:**
The application refuses to start in production without a real secret key. The error message tells
the developer exactly how to fix it. Development still works without configuration.

**Django concept:**
`SECRET_KEY` is used internally to sign cookies, generate CSRF tokens, create password reset
tokens, and sign JWTs (via `djangorestframework-simplejwt`). A leaked key lets an attacker forge
valid tokens for any user ID they choose.

---

### BUG-002 — DEBUG Defaults to True

| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | `config/settings.py:21` |
| **Status** | Exists in current codebase |

**What the problem is:**
```python
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
```
If `DEBUG` is not set in the environment, it defaults to `True`. In debug mode, Django exposes
full stack traces (including local variable values, settings, and database queries) in error
responses. Sensitive data is leaked on every unhandled exception.

**Why it happens:**
Same convenience-over-security pattern as BUG-001.

**The correct approach:**
```python
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
```
Default to `False`. The `.env.example` already shows `DEBUG=True` for local development — that
is correct. But the code-level default must be safe.

**Django concept:**
With `DEBUG=True`, Django renders a beautiful HTML error page with the full traceback, all request
headers, and all local variables at every frame. This page is useful for developers but catastrophic
in production — it exposes your database schema, file paths, environment variables, and business
logic to anyone who can trigger an error.

---

### BUG-003 — No JWT Token Blacklisting (Logout Impossible)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | `config/settings.py:136-141` |
| **Status** | Missing feature + wrong configuration |

**What the problem is:**
```python
SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS": False,   # ← refresh tokens never expire on use
    ...
}
```
JWTs are stateless — once issued, they are valid until expiry. There is no blacklist, no logout
endpoint, and no way to invalidate a token. A stolen access token is valid for 60 minutes. A
stolen refresh token is valid for 7 days.

**Why it happens:**
JWT's stateless nature is often presented as purely beneficial. Developers forget that logout
requires server-side state to track invalidated tokens.

**The correct approach:**

Step 1 — Add to `INSTALLED_APPS` in `config/settings.py`:
```python
"rest_framework_simplejwt.token_blacklist",
```

Step 2 — Run migration:
```bash
python manage.py migrate
```

Step 3 — Update `SIMPLE_JWT`:
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,        # issue new refresh token on each refresh call
    "BLACKLIST_AFTER_ROTATION": True,     # old refresh token becomes immediately invalid
    "AUTH_HEADER_TYPES": ("Bearer",),
}
```

Step 4 — Add a logout view (when you build the accounts app):
```python
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TokenError:
            return Response(
                {"detail": "Invalid or already blacklisted token."},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**Why this is better:**
Each refresh token can only be used once. If a refresh token is stolen and used by an attacker,
the legitimate user's next refresh call will fail (the old token is blacklisted). Users can
explicitly log out and invalidate their session immediately.

**Django concept:**
`rest_framework_simplejwt.token_blacklist` stores invalidated token JTI (JWT ID) values in a
database table. On every token refresh request, the middleware checks this table. If the JTI is
blacklisted, the request is rejected with 401.

**Common mistake:**
Thinking that short access token lifetimes solve this problem. Even a 5-minute access token gives
an attacker a 5-minute window. Token blacklisting + rotation is the correct defense.

---

### BUG-004 — CORS Allows All Origins in Debug Mode

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | `config/settings.py:144` |
| **Status** | Exists in current codebase |

**What the problem is:**
```python
CORS_ALLOW_ALL_ORIGINS = DEBUG
```
Any website on the internet can make cross-origin requests to your API when `DEBUG=True`.

**The correct approach:**
```python
CORS_ALLOW_ALL_ORIGINS = False  # always False

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]
```

**Django/Web concept:**
CORS (Cross-Origin Resource Sharing) is a browser security feature that prevents JavaScript on
`evil.com` from calling your API using a logged-in user's credentials. It is a defense-in-depth
measure — it does not replace authentication, but it limits the attack surface for cross-site
request forgery (CSRF) attacks from malicious websites.

---

### BUG-005 — No File Upload Validation

| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | `knowledge/models.py:63` |
| **Status** | Missing validation |

**What the problem is:**
```python
file = models.FileField(upload_to="documents/%Y/%m/%d/", blank=True, null=True)
```
There is no restriction on file type or size. A user could upload a 1 GB binary, an executable,
a script, or any other file. The model layer has no validation.

**Why it happens:**
`FileField` is intentionally generic at the model level. Business rule validation belongs in the
serializer layer, which does not exist yet.

**The correct approach — add to `DocumentSerializer` when you build it:**
```python
ALLOWED_SOURCE_EXTENSIONS = {
    "pdf": {"pdf"},
    "docx": {"docx"},
    "txt": {"txt"},
    "website": set(),  # no file needed
}
MAX_UPLOAD_MB = 50

class DocumentSerializer(serializers.ModelSerializer):

    def validate_file(self, value):
        if value is None:
            return value

        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        source_type = self.initial_data.get("source_type", "")
        allowed = ALLOWED_SOURCE_EXTENSIONS.get(source_type, set())

        if ext not in allowed:
            raise serializers.ValidationError(
                f"File type '.{ext}' is not allowed for source_type '{source_type}'. "
                f"Allowed: {allowed}"
            )

        if value.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File size {value.size // (1024*1024)}MB exceeds the {MAX_UPLOAD_MB}MB limit."
            )

        return value
```

**Why the serializer is the right place:**
Serializer validation runs before any business logic or database writes. Invalid files are
rejected before they touch the filesystem.

**Security concept:**
Accepting arbitrary file uploads without validation opens several attack vectors:
- **Storage exhaustion** — uploading many large files fills the disk.
- **Path traversal** — malicious filenames can escape the upload directory (Django mitigates this
  with `upload_to`, but explicit extension checks add defense-in-depth).
- **Content type confusion** — a file named `evil.txt` with executable content.

---

### BUG-006 — Redundant Name Fields on User Model

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **File** | `accounts/models.py:32`, `accounts/migrations/0001_initial.py:26-27` |
| **Status** | Design inconsistency |

**What the problem is:**
`AbstractUser` provides `first_name` and `last_name`. The custom `User` model adds `full_name`.
All three columns exist in the database (confirmed by the migration). Only `full_name` is intended
for use.

**Why it happens:**
Adding `full_name` to `AbstractUser` without removing the inherited fields creates overlap.

**Pragmatic fix for now:**
The migration is applied. Do not add a new migration just to remove `first_name`/`last_name` —
the effort is not worth it at this stage. Instead, never expose `first_name` or `last_name` in
serializers. Use only `full_name`.

**For a future project:**
Use `AbstractBaseUser` instead of `AbstractUser` when you need a fully custom user model. It
provides a blank slate with only `password`, `last_login`, and `is_active` — no inherited name
fields, no inherited `username`.

---

## 6. Missing Features

### 6.1 Complete Build List (by Priority)

#### Accounts App — Build First

| Missing Item | Type | Description |
|-------------|------|-------------|
| `accounts/serializers.py` | Serializers | `SignupSerializer` (write-only password) + `UserSerializer` (read-only profile) |
| `SignupView` | View | `CreateAPIView`, `AllowAny`, returns user profile on success |
| `MeView` | View | `RetrieveAPIView`, `IsAuthenticated`, returns `request.user` |
| `LogoutView` | View | Blacklists refresh token, returns 204 |
| `accounts/urls.py` routes | URLs | `/signup/`, `/me/`, `/logout/` |

#### Knowledge App

| Missing Item | Type | Description |
|-------------|------|-------------|
| `knowledge/serializers.py` | Serializers | `KnowledgeBaseSerializer`, `DocumentSerializer` |
| `KnowledgeBaseViewSet` | ViewSet | Full CRUD, queryset scoped to `request.user` |
| `DocumentViewSet` | ViewSet | Nested under KB, file upload + URL, ownership check on parent KB |
| `knowledge/urls.py` routes | URLs | Router-based nested routes |
| Cross-field validation | Serializer | File required for file types; URL required for website |
| `knowledge/services/ingest.py` | Service | Text extract → chunk → embed → ChromaDB (Step 6) |

#### Chat App

| Missing Item | Type | Description |
|-------------|------|-------------|
| `chat/serializers.py` | Serializers | `ChatSessionSerializer`, `ChatMessageSerializer` |
| `ChatSessionViewSet` | ViewSet | CRUD, scoped to `request.user` |
| `MessageViewSet` | ViewSet | Nested under session, ownership check |
| `chat/services/rag.py` | Service | Embed question → query Chroma → call OpenRouter (Step 7) |

#### Project-Level (config/)

| Missing Item | Type | Description |
|-------------|------|-------------|
| `config/exceptions.py` | Exception handler | Consistent JSON error format for all errors |
| Logging configuration | Settings | Structured log output |
| Throttle classes | Settings | Rate limiting on all endpoints |
| Swagger / drf-yasg | Settings + URLs | API documentation UI |
| `rest_framework_simplejwt.token_blacklist` | Installed app | Enable logout |

### 6.2 Missing Production-Ready Features (Beyond Learning Steps)

| Feature | Why It Matters |
|---------|----------------|
| Password change endpoint | Users must be able to change passwords |
| Password reset by email | Users must be able to recover accounts |
| Email verification on signup | Prevents fake account creation |
| API versioning | Allows breaking changes without destroying existing clients |
| `django-filter` integration | Filtering knowledge bases and documents by fields |
| Search on list endpoints | `?search=` query param for knowledge base names |
| Ordering on list endpoints | `?ordering=-created_at` for client-controlled sorting |
| Response envelope | Consistent `{"status": "success", "data": {...}}` wrapper |

---

## 7. Security Findings

### 7.1 Security Summary Table

| Finding | Severity | File | Status |
|---------|----------|------|--------|
| Insecure default SECRET_KEY | Critical | `config/settings.py:20` | Fix immediately |
| No token blacklisting / logout | High | `config/settings.py:136` | Fix before deployment |
| No file upload validation | High | `knowledge/models.py:63` | Fix when building Step 4 |
| DEBUG defaults to True | High | `config/settings.py:21` | Fix immediately |
| CORS allows all origins in debug | Medium | `config/settings.py:144` | Fix before deployment |
| No rate limiting | Medium | `config/settings.py` (REST_FRAMEWORK) | Add before deployment |
| No HTTPS security headers | Medium | `config/settings.py` | Add for production |
| Refresh tokens never rotate | Medium | `config/settings.py:139` | Fix with BUG-003 |
| first_name/last_name unused but exposed | Low | `accounts/models.py` | Never include in serializers |

### 7.2 Object-Level Permission Pattern (Most Important Security Concept)

When you build every view in this project, the ownership filter is the most critical security
control. Without it, any authenticated user can read, modify, or delete any other user's data.

**The pattern to use in every ViewSet:**

```python
class KnowledgeBaseViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = KnowledgeBaseSerializer

    def get_queryset(self):
        # This single filter is your ownership check for LIST, RETRIEVE, UPDATE, DELETE
        return KnowledgeBase.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # The client never sends owner — the server sets it
        serializer.save(
            owner=self.request.user,
            chroma_collection_id=f"kb_{uuid.uuid4().hex}"
        )
```

**Why `get_queryset()` is the right place:**
DRF calls `get_queryset()` for every action — list, retrieve, update, partial_update, and destroy.
Putting the ownership filter there means it applies everywhere automatically. You cannot
accidentally forget it on one action.

**Result of a correct ownership filter:**
- `GET /api/knowledge/bases/` — returns only the authenticated user's knowledge bases.
- `GET /api/knowledge/bases/{other_users_id}/` — returns 404 (not 403). The user doesn't even
  know the resource exists. This is the secure pattern — 403 would confirm the resource exists.
- `DELETE /api/knowledge/bases/{other_users_id}/` — returns 404.

**Common mistake — filtering only in list but not in retrieve/update/destroy:**
```python
# WRONG — user can still access any resource by ID
def list(self, request):
    queryset = KnowledgeBase.objects.filter(owner=request.user)  # only on list!
    ...

# CORRECT — filter in get_queryset() protects all actions
def get_queryset(self):
    return KnowledgeBase.objects.filter(owner=self.request.user)
```

### 7.3 Recommended Production Security Settings

Add to `config/settings.py` for production deployments:

```python
if not DEBUG:
    # Force HTTPS
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000       # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Secure cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
```

### 7.4 Rate Limiting (Missing)

Add to `REST_FRAMEWORK` in `config/settings.py`:

```python
REST_FRAMEWORK = {
    ...existing keys...,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",    # unauthenticated (signup, token)
        "user": "200/minute",   # authenticated requests
    },
}
```

For tighter control on auth endpoints, create a custom throttle class:

```python
# accounts/throttles.py
from rest_framework.throttling import AnonRateThrottle

class SignupThrottle(AnonRateThrottle):
    rate = "5/minute"  # max 5 signup attempts per minute per IP

class LoginThrottle(AnonRateThrottle):
    rate = "10/minute"  # max 10 login attempts per minute per IP
```

---

## 8. Performance Findings

### 8.1 No Implemented Views = No Existing N+1 Problems

Because views are not implemented, there are no active query patterns to analyze. However, the
following N+1 risks exist by design in the data model and must be addressed when views are built.

### 8.2 Anticipated N+1 Risks and Their Fixes

**Knowledge Base List — document count:**
```python
# Will cause N+1 (one COUNT query per knowledge base):
for kb in KnowledgeBase.objects.filter(owner=request.user):
    print(kb.documents.count())   # ← one extra query per KB

# Fix — annotate in a single query:
from django.db.models import Count

queryset = KnowledgeBase.objects.filter(owner=request.user).annotate(
    document_count=Count("documents")
)
```

**Chat Session List — knowledge base name:**
```python
# Will cause N+1 (one query per session to load the KB):
for session in ChatSession.objects.filter(user=request.user):
    print(session.knowledge_base.name)   # ← one extra query per session

# Fix — join in a single query:
queryset = ChatSession.objects.filter(user=request.user).select_related("knowledge_base")
```

**Document Admin — knowledge base name:**
```python
# In DocumentAdmin.list_display, "knowledge_base" triggers one query per document row.
# Fix in admin:
class DocumentAdmin(admin.ModelAdmin):
    list_select_related = ("knowledge_base",)   # add this line
```

### 8.3 How to Detect N+1 Queries

**Tool 1 — Django shell:**
```python
from django.db import connection, reset_queries
from django.conf import settings
settings.DEBUG = True
reset_queries()

# Run your queryset here
qs = list(KnowledgeBase.objects.filter(owner=user))
for kb in qs:
    _ = kb.owner.email   # trigger the potential N+1

print(f"Query count: {len(connection.queries)}")
for q in connection.queries:
    print(q["sql"])
```

**Tool 2 — django-debug-toolbar:**
Install in development only. The SQL panel shows every query executed per request, grouped by
duplicate patterns. Repeated queries with only the `WHERE id = X` changing indicate N+1.

**Rule of thumb:**
Any time you access a related object attribute inside a loop, you have a potential N+1. The fix
is `select_related()` for ForeignKey/OneToOne fields, or `prefetch_related()` for
ManyToMany/reverse FK fields.

| Pattern | Fix |
|---------|-----|
| `obj.fk_field.attribute` inside loop | `select_related("fk_field")` on queryset |
| `obj.reverse_fk_set.all()` inside loop | `prefetch_related("reverse_fk_set")` on queryset |
| `obj.m2m_field.all()` inside loop | `prefetch_related("m2m_field")` on queryset |

### 8.4 Synchronous Document Processing

The GUIDE explicitly acknowledges synchronous document processing for learning. The ingest
pipeline (text extract → chunk → embed → write to ChromaDB) runs inside the HTTP request cycle.
For large files, this will cause request timeouts.

**Acceptable for Steps 1–7 of the learning guide.**

**Migration path when you outgrow sync:**
1. Extract the ingest logic into `knowledge/services/ingest.py` (thin view principle).
2. When throughput becomes a problem, wrap the service call with Celery:
   ```python
   # Before (sync):
   ingest_document(doc)

   # After (async — only change this one line):
   ingest_document_task.delay(doc.id)
   ```
   The service logic itself does not change.

### 8.5 Database Index Recommendations

```python
# knowledge/models.py — add to Document.Meta:
class Meta:
    ordering = ["-created_at"]
    indexes = [
        models.Index(fields=["status"], name="document_status_idx"),
        # Useful for: Document.objects.filter(status="pending") in a reprocess command
    ]
```

---

## 9. API Review

### 9.1 Currently Working Endpoints

| Method | Path | Auth | Status |
|--------|------|------|--------|
| POST | `/api/auth/token/` | Public | Working — returns access + refresh |
| POST | `/api/auth/token/refresh/` | Public | Working — returns new access token |
| ANY | `/admin/` | Session | Working — full model admin |

### 9.2 Endpoints to Build (Full API Map)

#### Auth / Accounts

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|--------------|-------|
| POST | `/api/accounts/signup/` | Public | 201, 400 | Email + password + optional full_name |
| GET | `/api/accounts/me/` | JWT | 200, 401 | Returns id, email, full_name, date_joined |
| POST | `/api/accounts/logout/` | JWT | 204, 400 | Blacklists refresh token |

#### Knowledge Bases

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|--------------|-------|
| GET | `/api/knowledge/bases/` | JWT | 200, 401 | Paginated, owner-scoped list |
| POST | `/api/knowledge/bases/` | JWT | 201, 400, 401 | Server generates chroma_collection_id |
| GET | `/api/knowledge/bases/{id}/` | JWT | 200, 401, 404 | 404 if not owner |
| PATCH | `/api/knowledge/bases/{id}/` | JWT | 200, 400, 401, 404 | Partial update: name, description |
| DELETE | `/api/knowledge/bases/{id}/` | JWT | 204, 401, 404 | Also deletes Chroma collection (Step 6+) |

#### Documents (Nested Under Knowledge Base)

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|--------------|-------|
| GET | `/api/knowledge/bases/{id}/documents/` | JWT | 200, 401, 404 | 404 if KB not owned by user |
| POST | `/api/knowledge/bases/{id}/documents/` | JWT | 201, 400, 401, 404 | multipart for file; JSON for website |
| GET | `/api/knowledge/bases/{id}/documents/{doc_id}/` | JWT | 200, 401, 404 | Document detail |
| DELETE | `/api/knowledge/bases/{id}/documents/{doc_id}/` | JWT | 204, 401, 404 | Also deletes Chroma chunks (Step 6+) |

#### Chat

| Method | Path | Auth | Status Codes | Notes |
|--------|------|------|--------------|-------|
| GET | `/api/chat/sessions/` | JWT | 200, 401 | Paginated, user-scoped |
| POST | `/api/chat/sessions/` | JWT | 201, 400, 401 | Requires owned knowledge_base_id |
| GET | `/api/chat/sessions/{id}/` | JWT | 200, 401, 404 | Session detail |
| DELETE | `/api/chat/sessions/{id}/` | JWT | 204, 401, 404 | |
| GET | `/api/chat/sessions/{id}/messages/` | JWT | 200, 401, 404 | Ordered by created_at |
| POST | `/api/chat/sessions/{id}/messages/` | JWT | 201, 400, 401, 404 | Sends user message; returns assistant reply |

### 9.3 HTTP Status Code Guide

| Situation | Code | Why |
|-----------|------|-----|
| Resource created | 201 | Distinguishes creation from update in client code |
| Successful read or update | 200 | Standard |
| Successful delete or logout | 204 | Success with no response body |
| Validation failed | 400 | Client sent invalid data — client must fix the request |
| No token or invalid token | 401 | Not authenticated |
| Valid token, but not allowed | 403 | Authenticated but not authorized for this action |
| Resource not found (or not owned) | 404 | Use 404 for "not mine" too — don't confirm the resource exists |
| Wrong HTTP method | 405 | DRF returns this automatically with ViewSets |

### 9.4 Request / Response Format Examples

**Signup — POST `/api/accounts/signup/`**
```json
// Request
{"email": "user@example.com", "password": "SecurePass123", "full_name": "Jane Doe"}

// Success 201
{"id": 1, "email": "user@example.com", "full_name": "Jane Doe", "date_joined": "2026-07-27T..."}

// Error 400
{"email": ["user with this email address already exists."], "password": ["This password is too common."]}
```

**Create Knowledge Base — POST `/api/knowledge/bases/`**
```json
// Request
{"name": "Research Papers", "description": "ML papers collection"}

// Success 201
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Research Papers",
    "description": "ML papers collection",
    "chroma_collection_id": "kb_a1b2c3d4e5f6...",
    "created_at": "2026-07-27T10:00:00Z"
}
```

**Send Chat Message — POST `/api/chat/sessions/{id}/messages/`**
```json
// Request
{"content": "What is the main contribution of the attention mechanism paper?"}

// Success 201 (placeholder in Step 5; real RAG answer in Step 7)
{
    "id": "...",
    "session": "...",
    "role": "assistant",
    "content": "Based on the documents in your knowledge base, ...",
    "created_at": "2026-07-27T10:01:00Z"
}
```

---

## 10. Code Quality Review

### 10.1 Models

| Component | Quality | Notes |
|-----------|---------|-------|
| `User` | Good | Correct email auth pattern; unused inherited name fields |
| `UserManager` | Good | Correct use of `set_password`, `normalize_email` |
| `KnowledgeBase` | Good | UUID PK, correct FK ref, good field choices |
| `Document` | Good | `TextChoices` enums, good field structure |
| `ChatSession` | Good | UUID PK, correct relationships |
| `ChatMessage` | Good | Simple, correct |

**Minor model improvements to make now:**

```python
# knowledge/models.py — add index for status queries
class Document(models.Model):
    ...
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="document_status_idx"),
        ]
```

```python
# accounts/models.py — add verbose_name to Meta
class User(AbstractUser):
    ...
    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "user"
        verbose_name_plural = "users"
```

### 10.2 Admin

| Component | Quality | Notes |
|-----------|---------|-------|
| `UserAdmin` | Good | Correct fieldsets, filter_horizontal |
| `KnowledgeBaseAdmin` | Good | Useful list_display and search |
| `DocumentAdmin` | Good | Good filters; missing `list_select_related` |
| `ChatSessionAdmin` | Good | `ChatMessageInline` is excellent UX |
| `ChatMessageAdmin` | Good | Simple and appropriate |

**Fix for `DocumentAdmin`:**
```python
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "knowledge_base", "source_type", "status", "chunk_count", "created_at")
    list_filter = ("source_type", "status", "created_at")
    search_fields = ("title", "source_url")
    list_select_related = ("knowledge_base",)  # ← add this to prevent N+1 in admin list
```

### 10.3 Settings

| Setting | Quality | Notes |
|---------|---------|-------|
| `SECRET_KEY` | Bug | Insecure default — see BUG-001 |
| `DEBUG` | Bug | Unsafe default — see BUG-002 |
| `DATABASES` | Good | Clear SQLite/PostgreSQL switch |
| `REST_FRAMEWORK` | Partial | Missing throttle classes and exception handler |
| `SIMPLE_JWT` | Partial | Missing token blacklist — see BUG-003 |
| `CORS` | Bug | Too permissive — see BUG-004 |
| `MEDIA_ROOT` | Good | Correctly configured |
| `AUTH_PASSWORD_VALIDATORS` | Good | All four standard validators active |

**Missing REST_FRAMEWORK settings to add:**
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Add these:
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "200/minute",
    },
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
}
```

### 10.4 Serializers (Not Yet Implemented)

When you build serializers, follow these rules:

1. **Always declare `read_only_fields`** for server-generated fields:
   ```python
   class Meta:
       read_only_fields = ("id", "owner", "chroma_collection_id", "created_at", "updated_at")
   ```

2. **Use `write_only=True` for sensitive input fields:**
   ```python
   password = serializers.CharField(write_only=True)
   ```

3. **Put cross-field validation in `validate()`** (not `validate_fieldname()`):
   ```python
   def validate(self, data):
       if data["source_type"] != "website" and not data.get("file"):
           raise serializers.ValidationError({"file": "Required for this source type."})
       return data
   ```

4. **Never use `ModelSerializer` fields for password output.** Use a separate read serializer.

### 10.5 Views (Not Yet Implemented)

When you build views, follow these rules:

1. **Always use `ModelViewSet` or generic views** — never `APIView` unless you have a specific
   reason (like the message endpoint that does RAG logic).

2. **Always override `get_queryset()`** — never use the default `queryset` attribute on views
   that return user-scoped data.

3. **Keep views thin:**
   ```python
   # Good — view delegates to service
   def perform_create(self, serializer):
       doc = serializer.save(...)
       ingest_document(doc)   # service handles all ingest logic

   # Bad — business logic in the view
   def perform_create(self, serializer):
       doc = serializer.save(...)
       text = extract_pdf(doc.file.path)
       chunks = split_text(text)
       embeddings = embed(chunks)
       chroma_client.add(...)
       doc.status = "ready"
       doc.save()
   ```

4. **Always declare `permission_classes` explicitly** — even if it matches the global default.
   Explicit is better than implicit.

### 10.6 Tests (Not Yet Implemented)

All three `tests.py` files are empty. The minimum test suite you should write for each endpoint:

```python
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import User

class SignupTests(APITestCase):

    def test_signup_success(self):
        """Valid signup creates a user and returns 201."""
        response = self.client.post(reverse("signup"), {
            "email": "new@example.com",
            "password": "StrongPass123",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        self.assertNotIn("password", response.data)  # password never in response

    def test_signup_duplicate_email(self):
        """Duplicate email returns 400."""
        User.objects.create_user(email="exists@example.com", password="Pass123")
        response = self.client.post(reverse("signup"), {
            "email": "exists@example.com",
            "password": "Pass123",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_weak_password(self):
        """Common/weak password is rejected."""
        response = self.client.post(reverse("signup"), {
            "email": "test@example.com",
            "password": "password",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_requires_auth(self):
        """Unauthenticated request to /me returns 401."""
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_own_profile(self):
        """Authenticated user receives their own profile."""
        user = User.objects.create_user(email="me@example.com", password="Pass123")
        self.client.force_authenticate(user=user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
```

Test every endpoint for:
- Happy path (valid data + valid auth)
- No auth → 401
- Another user's resource → 404
- Invalid input → 400 with field errors

---

## 11. Step-by-Step Learning Guide

### Guide 1 — How to Build the Accounts API (Step 2)

**Goal:** Understand serializers and views by building signup + me endpoints.

#### Part A — Understand What You Are Building

Three operations:
1. A new user sends email + password → account created → returns profile.
2. A user sends email + password → receives JWT tokens.
3. A user sends a JWT → receives their profile.

Operation 2 is already handled by `/api/auth/token/` (SimplJWT). You build operations 1 and 3.

#### Part B — Build `accounts/serializers.py`

**Concept:** A serializer is a translator. It translates between Python objects (Django models)
and JSON (HTTP request/response bodies). It also validates incoming data.

**Why two serializers?**
- `SignupSerializer`: accepts password (write-only), returns nothing sensitive.
- `UserSerializer`: returns safe fields, never password.

Using one serializer for both forces you to add confusing conditionals. Two serializers, each
with one job, is the correct Single Responsibility Principle application.

```python
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User


class SignupSerializer(serializers.ModelSerializer):
    """Input serializer for user creation."""

    password = serializers.CharField(
        write_only=True,              # field accepted in input, never in output
        min_length=8,
        validators=[validate_password] # runs AUTH_PASSWORD_VALIDATORS from settings
    )

    class Meta:
        model = User
        fields = ("email", "password", "full_name")

    def create(self, validated_data):
        # CRITICAL: use create_user, never User.objects.create()
        # create_user calls set_password() which hashes the password
        # create() would store the raw password string in the database
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Read-only serializer — safe fields only, never password."""

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "date_joined")
        read_only_fields = ("id", "email", "full_name", "date_joined")
```

**Common mistake 1:** Forgetting `write_only=True` on password. Without it, the password hash
appears in the signup response body — a security leak.

**Common mistake 2:** Using `User.objects.create(password=raw_password)`. This stores the
raw password string. Anyone who can read the database (backups, breach) has every user's password.
`create_user()` calls `set_password()` which runs the password through Django's hashing framework
(PBKDF2 by default).

#### Part C — Build `accounts/views.py`

**Concept:** A view receives an HTTP request, uses a serializer to validate input and shape
output, and returns an HTTP response. DRF's generic views do the boilerplate for you.

```python
from rest_framework import generics, permissions
from .serializers import SignupSerializer, UserSerializer


class SignupView(generics.CreateAPIView):
    """
    POST /api/accounts/signup/
    Public — no JWT required.
    """
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    # AllowAny overrides the global IsAuthenticated default from settings


class MeView(generics.RetrieveAPIView):
    """
    GET /api/accounts/me/
    JWT required — returns the authenticated user's profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # request.user is the authenticated user — guaranteed by JWT middleware
        # No queryset needed; we don't look up by ID
        return self.request.user
```

**Why `generics.CreateAPIView`?**
It handles the entire POST lifecycle:
1. Receives the request body.
2. Instantiates the serializer with the request data.
3. Calls `is_valid(raise_exception=True)` — returns 400 automatically if invalid.
4. Calls `perform_create(serializer)`.
5. Returns a 201 response with the serialized output.

You get all of that for free. The only thing you override is `serializer_class` and
`permission_classes`.

**Why `permission_classes = [AllowAny]` on signup?**
The global `DEFAULT_PERMISSION_CLASSES` in settings is `IsAuthenticated`. A new user doesn't have
a JWT yet. You must explicitly override the permission to allow unauthenticated access.

**DRF permission order:**
1. Global `DEFAULT_PERMISSION_CLASSES` from settings (applied to every view).
2. View-level `permission_classes` attribute (overrides the global setting for that view).
3. You can also use `@permission_classes` decorator on function-based views.

#### Part D — Wire `accounts/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("me/", views.MeView.as_view(), name="me"),
]
```

`.as_view()` converts the class into a callable that Django's URL router can call.

#### Part E — Test the Endpoint Sequence

```
1. POST /api/accounts/signup/
   Body: {"email": "test@example.com", "password": "StrongPass123!"}
   Expected: 201 {"id": 1, "email": "test@example.com", "full_name": "", "date_joined": "..."}
   Check: password is NOT in the response body.

2. POST /api/auth/token/
   Body: {"email": "test@example.com", "password": "StrongPass123!"}
   Expected: 200 {"access": "...", "refresh": "..."}
   Note: field is "email", not "username" — the custom USERNAME_FIELD makes this work.

3. GET /api/accounts/me/
   Header: Authorization: Bearer <paste access token here>
   Expected: 200 {"id": 1, "email": "test@example.com", ...}

4. GET /api/accounts/me/  (without header)
   Expected: 401 {"detail": "Authentication credentials were not provided."}

5. POST /api/accounts/signup/
   Body: {"email": "test@example.com", "password": "123"}  (duplicate + weak)
   Expected: 400 with field-level errors for both email and password.
```

---

### Guide 2 — How to Build Knowledge Base CRUD (Step 3)

**Concept:** ViewSet + Router pattern for standard CRUD operations.

#### Understanding ViewSet vs APIView vs Generic View

| Class | Use When | Provides |
|-------|----------|----------|
| `APIView` | Non-standard logic, custom actions | Nothing; you write all HTTP method handlers |
| `generics.ListCreateAPIView` | Only list + create needed | `get()` and `post()` handlers |
| `ModelViewSet` | Full CRUD on a model | list, create, retrieve, update, partial_update, destroy |

For knowledge bases, you need full CRUD → use `ModelViewSet`.

#### The Router — Why It Replaces Manual URL Patterns

```python
# Without router — you'd write all these manually:
path("bases/", KnowledgeBaseListCreateView.as_view()),
path("bases/<uuid:pk>/", KnowledgeBaseDetailView.as_view()),

# With router — one line generates all of the above:
router = DefaultRouter()
router.register("bases", KnowledgeBaseViewSet, basename="knowledgebase")
```

The router registers these URL patterns automatically:
- `GET /bases/` → `list` action
- `POST /bases/` → `create` action
- `GET /bases/{id}/` → `retrieve` action
- `PUT /bases/{id}/` → `update` action
- `PATCH /bases/{id}/` → `partial_update` action
- `DELETE /bases/{id}/` → `destroy` action

#### The ViewSet Pattern

```python
import uuid
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import KnowledgeBase
from .serializers import KnowledgeBaseSerializer


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KnowledgeBaseSerializer

    def get_queryset(self):
        # OWNERSHIP ENFORCEMENT — every action uses this queryset
        # A user never sees another user's knowledge bases
        return KnowledgeBase.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Server sets owner and generates the Chroma collection ID
        # Client never sends these — they'd be ignored if they tried
        serializer.save(
            owner=self.request.user,
            chroma_collection_id=f"kb_{uuid.uuid4().hex}"
        )
```

---

### Guide 3 — How to Build Nested Document Routes (Step 4)

**Concept:** Nested resources require extra ownership checks at two levels:
1. The parent knowledge base must belong to the authenticated user.
2. The document must belong to that knowledge base.

```python
class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
    # PATCH/PUT excluded — documents are not updated after creation

    def _get_knowledge_base(self):
        """Look up parent KB and verify ownership. Raises 404 if not found/owned."""
        return get_object_or_404(
            KnowledgeBase,
            pk=self.kwargs["kb_pk"],         # from the URL: /bases/{kb_pk}/documents/
            owner=self.request.user          # ownership enforced here
        )

    def get_queryset(self):
        kb = self._get_knowledge_base()
        return Document.objects.filter(knowledge_base=kb)

    def perform_create(self, serializer):
        kb = self._get_knowledge_base()
        serializer.save(knowledge_base=kb, status=Document.Status.PENDING)
```

**URL pattern for nested routes:**
```python
# knowledge/urls.py
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter  # pip install drf-nested-routers
# OR manually:
from django.urls import path, include

router = DefaultRouter()
router.register("bases", KnowledgeBaseViewSet, basename="knowledgebase")

# Manual nesting without a package:
urlpatterns = router.urls + [
    path(
        "bases/<uuid:kb_pk>/documents/",
        DocumentListCreateView.as_view(),
        name="document-list"
    ),
    path(
        "bases/<uuid:kb_pk>/documents/<uuid:pk>/",
        DocumentDetailView.as_view(),
        name="document-detail"
    ),
]
```

---

### Guide 4 — Understanding the DRF Request Lifecycle

Every API call goes through this exact sequence. Understanding it tells you where to add
validation, business logic, and error handling.

```
1. URL dispatch
   config/urls.py matches the path → dispatches to the correct view class

2. Authentication
   JWT middleware extracts the token from the Authorization header
   Looks up the user → sets request.user
   If token is invalid/missing: request.user = AnonymousUser

3. Permission check
   View's permission_classes are evaluated
   IsAuthenticated: raises 401 if request.user is not authenticated
   AllowAny: always passes

4. Content negotiation
   DRF determines the parser (JSON / multipart) and renderer (JSON / browsable API)

5. View dispatch
   For ViewSets: determines which action (list/create/retrieve/etc.) based on HTTP method
   Calls get_queryset() — your ownership filter runs here

6. Serializer validation (for write operations)
   Instantiates serializer with request.data
   Calls is_valid(raise_exception=True)
   Runs field-level validators → validate_fieldname() methods → validate() method
   If any validation fails: returns 400 with error details automatically

7. Business logic
   Calls perform_create() / perform_update() / perform_destroy()
   Your code here: set owner, generate IDs, call services

8. Response serialization
   Serializer.data converts the saved object to a Python dict
   Renderer converts dict → JSON string

9. HTTP Response
   Status code + JSON body returned to client
```

**Key insight:** If you raise a `serializers.ValidationError` in step 6, the client gets a 400
with your error message and the view code in step 7 never runs. DRF handles all of this for you.

---

## 12. Prioritized Improvement Roadmap

### Phase 1 — Fix Settings Issues (Do Before Any Development)

| Task | File | Priority |
|------|------|----------|
| Fix SECRET_KEY to raise if not set | `config/settings.py` | Critical |
| Change DEBUG default to False | `config/settings.py` | High |
| Add token_blacklist to INSTALLED_APPS | `config/settings.py` | High |
| Set ROTATE_REFRESH_TOKENS = True | `config/settings.py` | High |
| Add throttle classes to REST_FRAMEWORK | `config/settings.py` | Medium |
| Add custom exception handler | `config/settings.py` + new file | Medium |
| Lock CORS to specific origins | `config/settings.py` | Medium |

### Phase 2 — Build the HTTP Layer (GUIDE Steps 2–5)

| Task | Step | Dependency |
|------|------|------------|
| accounts/serializers.py | Step 2 | None |
| accounts/views.py (Signup, Me) | Step 2 | Serializers |
| accounts/urls.py | Step 2 | Views |
| knowledge/serializers.py | Step 3 | None |
| knowledge/views.py (KnowledgeBase) | Step 3 | Serializers |
| knowledge/urls.py | Step 3 | Views |
| Document serializer + view | Step 4 | KB views working |
| chat/serializers.py + views + urls | Step 5 | Knowledge working |

### Phase 3 — Build the RAG Pipeline (GUIDE Steps 6–7)

| Task | Step | Dependency |
|------|------|------------|
| `knowledge/services/ingest.py` | Step 6 | Documents API working |
| Trigger ingest from document create view | Step 6 | Ingest service |
| ChromaDB cleanup on document/KB delete | Step 6 | Ingest service |
| `chat/services/rag.py` | Step 7 | Ingest working |
| Integrate RAG into message view | Step 7 | RAG service |

### Phase 4 — Quality and Production Readiness

| Task | When |
|------|------|
| Write tests for all endpoints | After each endpoint is built |
| Add Swagger / drf-yasg | After first few endpoints |
| Add `list_select_related` to admin classes | Now |
| Add DB indexes for status fields | Now |
| Add password change endpoint | Phase 3 |
| Switch to PostgreSQL | Before production |
| Add HTTPS security headers | Before production |
| Add structured logging | Before production |

---

## 13. Refactoring Recommendations

### 13.1 Create a Custom Exception Handler

```python
# config/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Wrap all DRF error responses in a consistent JSON envelope:
    {
        "status": "error",
        "status_code": 400,
        "errors": { ... }   ← original DRF error structure
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "status": "error",
            "status_code": response.status_code,
            "errors": response.data,
        }

    return response
```

Register it in `config/settings.py`:
```python
"EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
```

**Why this matters:** Without a custom handler, DRF returns different error structures for
different error types. Authentication errors look different from validation errors, which look
different from permission errors. A custom handler gives every error response the same shape,
making client-side error handling predictable.

### 13.2 Create a Base ViewSet

Once you have multiple ViewSets, extract the common ownership pattern into a base class:

```python
# config/mixins.py
from rest_framework import viewsets, permissions


class OwnedModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that scopes all querysets to the authenticated user.
    Subclasses must define owner_field (the ForeignKey to the user model).
    """
    permission_classes = [permissions.IsAuthenticated]
    owner_field = "owner"   # override in subclass if FK name differs

    def get_queryset(self):
        return super().get_queryset().filter(
            **{self.owner_field: self.request.user}
        )

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user})
```

Then your ViewSets become:
```python
class KnowledgeBaseViewSet(OwnedModelViewSet):
    serializer_class = KnowledgeBaseSerializer
    queryset = KnowledgeBase.objects.all()

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user,
            chroma_collection_id=f"kb_{uuid.uuid4().hex}"
        )
```

### 13.3 Services Directory Structure

Create these directories and files as you reach each GUIDE step:

```
knowledge/
└── services/
    ├── __init__.py
    ├── ingest.py       # Step 6: extract → chunk → embed → ChromaDB
    └── chroma.py       # Step 6: ChromaDB client wrapper

chat/
└── services/
    ├── __init__.py
    └── rag.py          # Step 7: embed query → retrieve chunks → OpenRouter → response
```

Each service file should contain plain functions (or a class if state is needed). Views call
services; services never import from views.

---

## 14. Production Readiness Checklist

### Foundation
- [x] Custom User model with email auth
- [x] JWT authentication configured
- [x] Separate apps per domain
- [x] UUID primary keys for domain models
- [x] Admin configured for all models
- [x] Environment-based configuration
- [x] Migrations created and applied

### Settings — Fix Before Deployment
- [ ] `SECRET_KEY` raises `RuntimeError` if not set
- [ ] `DEBUG` defaults to `False`
- [ ] Token blacklist app added and migrated
- [ ] `ROTATE_REFRESH_TOKENS = True`
- [ ] `CORS_ALLOW_ALL_ORIGINS = False` with explicit allowed origins
- [ ] Rate limiting (throttle classes) configured
- [ ] Custom exception handler registered
- [ ] HTTPS security headers (`SECURE_SSL_REDIRECT`, `HSTS`, etc.)
- [ ] Logging configuration

### HTTP Layer — Must Build
- [ ] All serializers (accounts, knowledge, chat)
- [ ] All views / ViewSets
- [ ] All URL routes
- [ ] Ownership enforcement in every `get_queryset()`
- [ ] File upload validation (extension + size)
- [ ] Cross-field validation (file required for file types; URL required for website)
- [ ] Logout endpoint

### RAG Pipeline — Must Build
- [ ] `knowledge/services/ingest.py`
- [ ] `chat/services/rag.py`
- [ ] ChromaDB cleanup on document/KB delete
- [ ] `Document.status` transitions enforced in service
- [ ] Error handling: `status=failed` with `error_message` on ingest failure

### Quality
- [ ] Tests for every endpoint (happy path + 401 + 404 + 400)
- [ ] API documentation (Swagger / drf-yasg)
- [ ] Admin `list_select_related` for N+1 prevention
- [ ] DB index on `Document.status`

### Infrastructure (Before Launch)
- [ ] PostgreSQL (not SQLite)
- [ ] Static files served by WhiteNoise or S3
- [ ] `ALLOWED_HOSTS` set to production domain only
- [ ] Reverse proxy (nginx) with HTTPS certificate
- [ ] Automated backups for the SQL database
- [ ] ChromaDB persistence directory backed up

---

## 15. Learning Notes

### Note 1 — `request.user` Is Your Security Anchor

In any authenticated view, `request.user` is guaranteed to be the authenticated user (set by the
JWT middleware). Never trust user IDs sent in request bodies for ownership decisions — those can
be spoofed by the client. Always build ownership checks around `request.user`.

```python
# NEVER do this (client-controlled):
knowledge_base = KnowledgeBase.objects.get(id=request.data["knowledge_base_id"])

# ALWAYS do this (server-enforced):
knowledge_base = get_object_or_404(
    KnowledgeBase,
    id=request.data["knowledge_base_id"],
    owner=request.user   # ← ownership enforced, not trusted
)
```

### Note 2 — Model Layer vs Serializer Layer Validation

Django has two validation layers:

| Layer | Runs When | Use For |
|-------|-----------|---------|
| Serializer | `serializer.is_valid()` — before DB write | HTTP input validation, business rules |
| Model | `model.full_clean()` — at DB write | Database constraints, last-resort checks |

Always prefer serializer-level validation. It gives better error messages, runs earlier, and is
designed for HTTP error responses. Model validation is a fallback, not the primary defense.

### Note 3 — The N+1 Detection Mindset

Any time you see `obj.related_field.something` inside a loop or list, ask: "Is this accessing
the database once per iteration?" If yes, that's an N+1 problem. The fix:

- **ForeignKey / OneToOne access:** `queryset.select_related("field_name")`
- **Reverse FK / ManyToMany access:** `queryset.prefetch_related("field_name")`

The difference:
- `select_related` performs a SQL JOIN — one query total.
- `prefetch_related` performs two queries but handles the join in Python — needed when JOIN
  would produce duplicate rows (ManyToMany, reverse FK to multiple objects).

### Note 4 — ChromaDB vs SQL — The Bright Line

The most important design rule in this project:

| Question | Answer | Store |
|----------|--------|-------|
| Who owns this knowledge base? | User FK | SQL |
| What is the document's processing status? | Status field | SQL |
| What was the conversation history? | ChatMessage rows | SQL |
| Which text chunks are semantically similar to this question? | Vector similarity | ChromaDB |
| What is the embedding of this text? | Float array | ChromaDB |

Violating this line — for example, adding an `embedding` ArrayField to a Django model — creates
severe performance problems (SQL is not optimized for vector similarity) and architectural
confusion.

### Note 5 — The Thin View Principle

Views are coordinators, not implementers. A view's job is:
1. Check authentication and permissions (DRF does this).
2. Validate input (serializer does this).
3. Call the right service or queryset.
4. Return the response (DRF does this).

Business logic (text extraction, embedding, LLM calls, complex calculations) goes in service
functions, not views. This makes views readable, services testable in isolation, and the
application easier to evolve.

### Note 6 — Why UUID PKs Prevent ID Enumeration

With integer PKs:
```
GET /api/knowledge/bases/1/   → works
GET /api/knowledge/bases/2/   → works (maybe another user's!)
GET /api/knowledge/bases/3/   → works
```
An attacker can iterate through all IDs to discover resources.

With UUID PKs:
```
GET /api/knowledge/bases/550e8400-e29b-41d4-a716-446655440000/   → works
GET /api/knowledge/bases/550e8400-e29b-41d4-a716-446655440001/   → 404 (not a valid UUID)
```
There are 2^122 possible UUID values. Guessing a valid one is computationally infeasible. The
ownership filter in `get_queryset()` is still required — UUIDs are not a substitute for access
control, but they add defense-in-depth.

---

## 16. Action Plan

### Immediate (Before Any Feature Development)

```bash
# 1. Fix settings security issues
# Edit config/settings.py:
#   - SECRET_KEY: raise RuntimeError if not set
#   - DEBUG: default to False
#   - CORS: explicit allowed origins list
#   - REST_FRAMEWORK: add throttle classes
#   - SIMPLE_JWT: ROTATE_REFRESH_TOKENS = True

# 2. Add token blacklist
# Edit config/settings.py INSTALLED_APPS:
#   - Add "rest_framework_simplejwt.token_blacklist"
python manage.py migrate

# 3. Create config/exceptions.py with custom_exception_handler
# Register in REST_FRAMEWORK settings
```

### Week 1 — Step 2 (Accounts API)

```
Day 1: Read accounts/models.py carefully. Understand every field.
Day 2: Write accounts/serializers.py (SignupSerializer + UserSerializer).
Day 3: Write accounts/views.py (SignupView + MeView).
Day 4: Wire accounts/urls.py. Test all 5 scenarios from Guide 1 Part E.
Day 5: Write tests in accounts/tests.py. Write LogoutView.
```

### Week 2 — Step 3 (Knowledge Bases)

```
Day 1: Write knowledge/serializers.py (KnowledgeBaseSerializer).
Day 2: Write knowledge/views.py (KnowledgeBaseViewSet).
Day 3: Wire knowledge/urls.py with DefaultRouter.
Day 4: Test all CRUD operations. Verify user A cannot see user B's data.
Day 5: Write tests in knowledge/tests.py.
```

### Week 3 — Step 4 (Documents)

```
Day 1: Extend knowledge/serializers.py (DocumentSerializer with validation).
Day 2: Write DocumentViewSet with nested URL support.
Day 3: Test file upload (PDF) via Postman with multipart/form-data.
Day 4: Test website URL document. Test cross-field validation.
Day 5: Write tests. Verify file type and size validation.
```

### Week 4 — Step 5 (Chat Placeholder)

```
Day 1: Write chat/serializers.py.
Day 2: Write ChatSessionViewSet + MessageViewSet (placeholder reply).
Day 3: Wire chat/urls.py.
Day 4: Full end-to-end test: signup → login → create KB → upload doc → chat.
Day 5: Write tests.
```

### Weeks 5–6 — Steps 6–7 (RAG Pipeline)

```
Week 5: Implement knowledge/services/ingest.py (text extract → chunk → embed → ChromaDB).
         Trigger ingest from document create. Verify Document.status becomes "ready".
Week 6: Implement chat/services/rag.py (embed query → Chroma search → OpenRouter → save reply).
         Full RAG chat test: question about uploaded PDF returns grounded answer.
```

---

*This document covers the complete codebase as of 2026-07-27. Update it as each section is implemented.*  
*Related docs: [GUIDE.md](../GUIDE.md) · [VECTOR_DB.md](VECTOR_DB.md) · [API_TESTING.md](API_TESTING.md) · [../README.md](../README.md)*
