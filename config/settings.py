"""
Django settings for KnowledgeNest AI.

Keep this file beginner-friendly:
- SQLite by default (easy local start)
- Switch to PostgreSQL later via DATABASE_URL / env vars
- ChromaDB path is separate from the SQL database
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# BUG-001 FIX — SECRET_KEY must be set in production.
# Dev commands (runserver, test, shell) can use a fallback for convenience.
# Any other command (migrate, collectstatic, gunicorn) MUST have a real key.
# ---------------------------------------------------------------------------
_secret = os.getenv("SECRET_KEY")
if not _secret:
    if any(cmd in sys.argv for cmd in ("runserver", "test", "shell", "collectstatic")):
        _secret = "dev-only-insecure-do-not-deploy"
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(50))\""
        )
SECRET_KEY = _secret

# ---------------------------------------------------------------------------
# BUG-002 FIX — Default to False. .env sets DEBUG=True for local dev.
# ---------------------------------------------------------------------------
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # BUG-003 FIX — enables logout
    "corsheaders",
    "drf_yasg",
    # Local apps
    "accounts",
    "knowledge",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database — metadata only (users, knowledge bases, documents, chat history)
# Embeddings are NEVER stored here. They live in ChromaDB.
# ---------------------------------------------------------------------------
# Default: SQLite for local development.
# To use PostgreSQL later, set USE_POSTGRES=True and fill PG_* vars.
USE_POSTGRES = os.getenv("USE_POSTGRES", "False").lower() == "true"

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("PG_NAME", "knowledgenest"),
            "USER": os.getenv("PG_USER", "postgres"),
            "PASSWORD": os.getenv("PG_PASSWORD", ""),
            "HOST": os.getenv("PG_HOST", "localhost"),
            "PORT": os.getenv("PG_PORT", "5432"),
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Local media storage for uploaded PDF / DOCX / TXT files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user — email login/signup (must be set before first migrate)
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Django REST Framework + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Rate limiting — prevents brute-force and abuse
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "200/minute",
    },
    # Consistent error response shape
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# BUG-003 FIX — JWT with token rotation + blacklisting
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,           # issue new refresh on each refresh call
    "BLACKLIST_AFTER_ROTATION": True,         # old refresh token becomes invalid
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# BUG-004 FIX — CORS: never allow all origins; parse from env var
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

# ---------------------------------------------------------------------------
# Production security headers (only when DEBUG is off)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# AI / RAG settings
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_data"
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# ---------------------------------------------------------------------------
# Logging — structured output for production debugging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "knowledge": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "chat": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Swagger / drf-yasg — JWT Bearer Authorization button
# ---------------------------------------------------------------------------
SWAGGER_SETTINGS = {
    "VALIDATOR_URL": None,
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": (
                "JWT Authorization header.\n\n"
                "Format: **Bearer &lt;access_token&gt;**\n\n"
                "Get a token from POST /api/accounts/login/"
            ),
        }
    },
    "USE_SESSION_AUTH": False,
    "JSON_EDITOR": True,
    "SUPPORTED_SUBMIT_METHODS": [
        "get", "post", "put", "patch", "delete",
    ],
}