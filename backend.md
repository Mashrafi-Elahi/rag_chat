Project Path: rag-chat-app

Source Tree:

```txt
rag-chat-app
├── Dockerfile
├── GUIDE.md
├── README.md
├── accounts
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── api.json
├── backend.md
├── chat
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   ├── 0002_alter_chatsession_knowledge_base.py
│   │   └── __init__.py
│   ├── models.py
│   ├── serializers.py
│   ├── services
│   │   ├── __init__.py
│   │   └── rag.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── config
│   ├── __init__.py
│   ├── asgi.py
│   ├── exceptions.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docker-compose.yml
├── docs
│   ├── API_DOCKER_GUIDE.md
│   ├── API_Integration_guide.md
│   ├── API_TESTING.md
│   ├── CODEBASE_REVIEW.md
│   ├── VECTOR_DB.md
│   └── schema.mmd
├── knowledge
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   ├── 0002_document_document_status_idx.py
│   │   └── __init__.py
│   ├── models.py
│   ├── script_chroma.py
│   ├── script_chroma_add.py
│   ├── script_chroma_query.py
│   ├── script_chunker.py
│   ├── script_embedder.py
│   ├── script_extractor.py
│   ├── script_ingest.py
│   ├── serializers.py
│   ├── services
│   │   ├── chroma.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── extractor.py
│   │   └── ingest.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── manage.py
├── railway.json
└── requirements.txt

```

`Dockerfile`:

```
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY . .

RUN python manage.py collectstatic --noinput

RUN mkdir -p /app/chroma_db \
    && adduser --disabled-password --gecos "" django-user \
    && chown -R django-user:django-user /app


USER django-user


EXPOSE 8000


CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
```
`GUIDE.md`:

```md
# KnowledgeNest AI — Beginner DRF Guide

Learn how to build the REST API yourself, step by step.
This guide explains **what to build and in what order**. It does not paste finished code — you write that following Django REST Framework docs and this project’s models.

---

## Big picture

```
Upload PDF / DOCX / TXT  or  add Website URL
              ↓
     Extract text → chunk → embed
              ↓
   ChromaDB (vectors)     SQLite/PostgreSQL (metadata + chat)
              ↓
     User chats → retrieve chunks → OpenRouter answers
```

**Hard rule:** embedding vectors live only in **ChromaDB**. The SQL database stores users, profiles, knowledge bases, document metadata, and chat history.

No Celery. No Redis. No Qdrant. Keep the stack small.

---

## What is already done for you

| Piece | Status |
|-------|--------|
| Django project + apps (`accounts`, `knowledge`, `chat`) | Done |
| Models + migrations | Done |
| JWT settings + token URLs | Done |
| Media / CORS / env basics | Done |
| Serializers, ViewSets, ingest, RAG | **You build these** |

Schema diagram: [`docs/schema.mmd`](docs/schema.mmd)

---

## DRF mental model (read this once)

Before coding endpoints, understand these layers:

1. **Model** — tables (already designed).
2. **Serializer** — turns models ↔ JSON; validates input.
3. **View / ViewSet** — handles HTTP methods; uses serializers + queryset.
4. **URL** — maps paths to views.
5. **Permission / Auth** — who may call the endpoint (JWT here).

Typical flow for every feature:

```
URL  →  ViewSet  →  Serializer  →  Model  →  Database
                 ↘  (later) services for Chroma / OpenRouter
```

Always ask: *Which model? Who owns the row? What JSON goes in/out?*

---

## Learning path (do in order)

### Step 0 — Environment & smoke test

- Activate the project virtualenv.
- Install `requirements.txt`, copy `.env.example` → `.env`.
- Run migrations and start the server.
- Create a superuser; open `/admin/`.
- Obtain a JWT from `POST /api/auth/token/` with **email** + password; confirm `access` + `refresh`.

**Checkpoint:** server runs; admin works; you can get a token.

> If `python manage.py` cannot find Django inside Cursor, use:  
> `.venv/bin/python manage.py runserver`

---

### Step 1 — Read the models

Open and understand (do not change yet):

- `accounts.User` — email login/signup (`USERNAME_FIELD = email`), optional `full_name`
- `knowledge.KnowledgeBase` — owner + `chroma_collection_id` (string link to Chroma, not a vector)
- `knowledge.Document` — file or URL + `status` / `chunk_count`
- `chat.ChatSession` / `chat.ChatMessage` — conversation history

**Checkpoint:** you can explain each field in plain language and why vectors are not in SQL.

---

### Step 2 — Auth API (`accounts`)

**Goal:** signup with email + password; login with email + password → JWT; fetch current user.

Auth contract (one model, no Profile table):

| Action | Input | Result |
|--------|-------|--------|
| Signup | `email`, `password`, optional `full_name` | Creates `User` via `create_user` |
| Login | `email`, `password` | JWT `access` + `refresh` |
| Me | Bearer token | Safe user fields (`id`, `email`, `full_name`, …) |

Learn / practice:

- `AllowAny` for signup; `IsAuthenticated` for “me”
- Call `User.objects.create_user(...)` — never save raw passwords
- Token body uses **email** (not username) because `USERNAME_FIELD = "email"`
- Return only safe fields (never `password`)

**Checkpoint:** signup → login (token with email) → `GET` current user works with `Authorization: Bearer …`.

---

### Step 3 — Knowledge bases CRUD

**Goal:** each user manages only their own knowledge bases.

Learn / practice:

- `ModelViewSet` + router
- Filtering queryset by `request.user`
- On create: set `owner`; generate a unique `chroma_collection_id` string
- Read-only fields vs writable fields in the serializer

**Checkpoint:** create / list / update / delete bases; another user’s base is never visible.

---

### Step 4 — Documents (upload + website)

**Goal:** add sources under a knowledge base.

Learn / practice:

- Nested routes (documents under a base id)
- File upload with `multipart/form-data` vs JSON for website URLs
- Serializer validation: file required for pdf/docx/txt; URL required for website
- Ownership check on the parent knowledge base
- Leave `status=pending` for now (processing comes later)

**Checkpoint:** upload a PDF and add a website URL; both appear in admin with correct `source_type`.

---

### Step 5 — Chat sessions & messages (without RAG)

**Goal:** save conversations; return a placeholder assistant reply.

Learn / practice:

- Create session tied to a knowledge base you own
- List messages for a session
- POST a user message; persist user + assistant rows
- Placeholder assistant text is fine until Step 7

**Checkpoint:** full message history round-trip in the database.

---

### Step 6 — Ingest into ChromaDB (sync)

**Goal:** when a document is created, process it in the same request (or a simple management command). No Celery.

Deep dive: **[docs/VECTOR_DB.md](docs/VECTOR_DB.md)** (what Chroma stores, collections, ingest/query flows, checklists).

Learn / practice:

- Extract text (PDF / DOCX / TXT / HTML)
- Chunk text
- Embed with Sentence Transformers
- Write vectors + chunk text into the Chroma collection named by `chroma_collection_id`
- Store Chroma metadata: `document_id`, `knowledge_base_id`, chunk index
- Update `Document.status = ready` and `chunk_count` only in SQL

**Checkpoint:** Chroma has chunks; SQL document is `ready`; SQL has **no** embedding columns.

---

### Step 7 — RAG chat via OpenRouter

**Goal:** real answers grounded in the user’s knowledge base.

See also: [docs/VECTOR_DB.md](docs/VECTOR_DB.md) → “Retrieve + answer”.

Learn / practice:

- Embed the user question
- Query Chroma top-k chunks for that collection
- Build a prompt: context + question
- Call OpenRouter (OpenAI-compatible API)
- Save the assistant reply as `ChatMessage`

**Checkpoint:** asking about an uploaded doc returns an answer that uses that content.

---

## API map (target)

Use this as your contract while building. Implement one group per step.

### Auth

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/accounts/signup/` | Public | Create user (email + password) |
| POST | `/api/auth/token/` | Public | Login with email + password → JWT |
| POST | `/api/auth/token/refresh/` | Public | Refresh access token |
| GET | `/api/accounts/me/` | JWT | Current user |

### Knowledge

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/knowledge/bases/` | JWT | List my knowledge bases |
| POST | `/api/knowledge/bases/` | JWT | Create knowledge base |
| GET | `/api/knowledge/bases/{id}/` | JWT | Retrieve one |
| PATCH | `/api/knowledge/bases/{id}/` | JWT | Update name/description |
| DELETE | `/api/knowledge/bases/{id}/` | JWT | Delete base (+ related docs) |
| GET | `/api/knowledge/bases/{id}/documents/` | JWT | List sources |
| POST | `/api/knowledge/bases/{id}/documents/` | JWT | Upload file or add URL |
| GET | `/api/knowledge/bases/{id}/documents/{doc_id}/` | JWT | Document detail |
| DELETE | `/api/knowledge/bases/{id}/documents/{doc_id}/` | JWT | Remove source |

### Chat

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/chat/sessions/` | JWT | List my sessions |
| POST | `/api/chat/sessions/` | JWT | Start session on a KB |
| GET | `/api/chat/sessions/{id}/` | JWT | Session detail |
| DELETE | `/api/chat/sessions/{id}/` | JWT | Delete session |
| GET | `/api/chat/sessions/{id}/messages/` | JWT | Message history |
| POST | `/api/chat/sessions/{id}/messages/` | JWT | Ask question → assistant reply |

---

## Learning checklist

Mark these off as you go.

### Foundations
- [ ] Virtualenv + dependencies installed
- [ ] `.env` configured
- [ ] Migrations applied; admin opens
- [ ] JWT token obtained and used in `Authorization` header
- [ ] Can explain Model → Serializer → View → URL

### Accounts
- [ ] Signup creates a user with email + hashed password
- [ ] Login accepts `email` + `password` and returns JWT
- [ ] `/me` returns authenticated user data only (no password)

### Knowledge
- [ ] CRUD for knowledge bases (owner-scoped)
- [ ] `chroma_collection_id` generated on create
- [ ] Document file upload works
- [ ] Website URL document works
- [ ] Validation rejects missing file/URL by `source_type`

### Chat
- [ ] Create session on owned knowledge base
- [ ] List and post messages
- [ ] User + assistant messages stored

### RAG
- [ ] Read [docs/VECTOR_DB.md](docs/VECTOR_DB.md)
- [ ] Text extraction for pdf / docx / txt / website
- [ ] Chunks embedded into ChromaDB
- [ ] Document status becomes `ready`
- [ ] Chat retrieves chunks and calls OpenRouter
- [ ] Confirmed: no embedding vectors in SQLite/PostgreSQL
- [ ] Delete document/KB also cleans Chroma

### Quality habits
- [ ] Every queryset filtered by ownership
- [ ] Errors return clear JSON (`status`, validation messages)
- [ ] Manual test of each row in the API map above

---

## Suggested study order inside DRF

1. Serializers (fields, `create`, `validate`)
2. Generic views / ViewSets / APIView
3. Routers and URL design
4. Permissions + JWT authentication
5. File uploads (`MultiPartParser`)
6. Thin views + service functions for ingest/RAG

Official docs: [Django REST framework](https://www.django-rest-framework.org/)

---

## Common pitfalls

| Mistake | Better approach |
|---------|-----------------|
| Saving vectors in SQL | Use ChromaDB only |
| Showing all users’ rows | Filter by `request.user` |
| Uploading files as JSON | Use multipart form data |
| Building Celery too early | Sync ingest is enough to learn |
| Skipping auth on “private” routes | Default permission is authenticated |

---

## Next move

1. Finish **Step 0** and **Step 1**.
2. Implement **Step 2** (accounts) using serializers + views — no copy-paste from this file.
3. Tick the checklist as each checkpoint passes.

For how a developer should day-to-day work in this repo, see [README.md](README.md).  
For Swagger (drf-yasg) and Postman testing, see [docs/API_TESTING.md](docs/API_TESTING.md).  
For ChromaDB / vectors, see [docs/VECTOR_DB.md](docs/VECTOR_DB.md).

```
`README.md`:

```md
# KnowledgeNest AI

Build a personal AI knowledge base from **PDF**, **DOCX**, **TXT**, or **website URLs**, then chat with that knowledge using **OpenRouter**.

This README is the **developer handbook**: architecture, pipeline, and how you should work day to day.

---

## Product in one paragraph

A user signs up, creates a knowledge base, uploads documents or pastes a website URL, waits until sources are processed, then opens a chat. Answers are grounded in their own content (RAG). Metadata and chat history live in SQL. Embedding vectors live in ChromaDB.

---

## Architecture (for learning)

### System overview

```text
                    ┌─────────────────────────────────────────┐
                    │              Client                      │
                    │   Browser / Postman / Swagger UI         │
                    └─────────────────┬───────────────────────┘
                                      │  HTTPS / JSON
                                      │  Authorization: Bearer <JWT>
                    ┌─────────────────▼───────────────────────┐
                    │         Django + DRF API                 │
                    │  accounts │ knowledge │ chat             │
                    └─────┬─────────────┬─────────────┬───────┘
                          │             │             │
              ┌───────────▼──┐   ┌──────▼──────┐  ┌───▼────────────┐
              │ SQLite /     │   │ Local media │  │ ChromaDB       │
              │ PostgreSQL   │   │ (uploads)   │  │ (vectors +     │
              │ metadata +   │   │ PDF/DOCX/TXT│  │  chunk text)   │
              │ chat history │   └─────────────┘  └───────┬────────┘
              └──────────────┘                            │
                                                          │ top-k chunks
                                                  ┌───────▼────────┐
                                                  │ OpenRouter LLM │
                                                  └────────────────┘
```

### Layer responsibilities

| Layer | Responsibility | Not responsible for |
|-------|----------------|---------------------|
| **DRF API** | Auth, validation, ownership, orchestration | Storing embedding arrays |
| **SQL (Django models)** | Users, KBs, document metadata, chat messages | Similarity search |
| **Local media** | Uploaded files on disk | Vectors |
| **ChromaDB** | Embeddings + chunk text + chunk metadata | Passwords, JWT, user tables |
| **Sentence Transformers** | Text → vector (ingest & query) | Chat answers |
| **OpenRouter** | Final natural-language answer | Permanent vector storage |

### App boundaries

```text
config/          settings, root URLs, JWT, media, (later Swagger)
accounts/        User (email login/signup), signup + me endpoints
knowledge/       KnowledgeBase, Document, ingest → Chroma
chat/            ChatSession, ChatMessage, retrieve → OpenRouter
```

One rule to remember:

> **SQL remembers what the user owns.  
> Chroma remembers what the text means.  
> OpenRouter answers using the text Chroma finds.**

---

## Pipelines (for learning)

### 1) Auth pipeline

```text
Signup (email + password + optional full_name)
        → create User (hashed password)
        → client calls Login
        → JWT access + refresh
        → client sends Authorization: Bearer <access>
        → Me / Knowledge / Chat endpoints
```

### 2) Knowledge ingest pipeline (upload → vectors)

```text
Create KnowledgeBase
        → save SQL row + chroma_collection_id (string)
                │
Upload PDF/DOCX/TXT  or  Add website URL
        → save Document (status=pending) + file/url metadata
                │
        Extract text → Chunk → Embed (Sentence Transformers)
                │
        Upsert into Chroma collection = chroma_collection_id
        (chunk text + vector + metadata: document_id, knowledge_base_id)
                │
        Update Document: status=ready, chunk_count=N
```

**Sync only** for learning — no Celery / Redis.

### 3) Chat / RAG pipeline (question → answer)

```text
Create ChatSession (user + knowledge_base)
        │
POST message (user question)
        → save ChatMessage(role=user) in SQL
        → embed question (same model as ingest)
        → query that KB’s Chroma collection (top_k chunks)
        → build prompt: rules + retrieved context + question
        → OpenRouter completion
        → save ChatMessage(role=assistant) in SQL
        → return answer to client
```

### 4) Request path inside Django (every API call)

```text
URL (config/urls.py → app urls)
  → View / ViewSet
      → Permission (JWT?)
      → Serializer (validate + shape JSON)
      → Model / QuerySet (filter by request.user)
      → optional Service (ingest / RAG)
  → JSON Response
```

### Pipeline vs GUIDE steps

| Pipeline | When you build it |
|----------|-------------------|
| Auth | GUIDE Step 2 |
| Knowledge CRUD + upload | GUIDE Steps 3–4 |
| Chat placeholder | GUIDE Step 5 |
| Ingest → Chroma | GUIDE Step 6 · [VECTOR_DB.md](docs/VECTOR_DB.md) |
| RAG → OpenRouter | GUIDE Step 7 |
| Swagger + Postman | Anytime after first endpoints · [API_TESTING.md](docs/API_TESTING.md) |

---

## Tech stack (keep it simple)

| Layer | Choice | Notes |
|-------|--------|--------|
| API framework | Django + Django REST Framework | One backend project |
| Auth | JWT (`djangorestframework-simplejwt`) | Email login via custom `User` |
| API docs | drf-yasg (Swagger) | See `docs/API_TESTING.md` |
| API testing | Postman | Collections + env vars |
| Metadata DB | SQLite (default) or PostgreSQL | Users, KBs, docs, chat |
| Vector store | ChromaDB | Embeddings + chunk text only |
| Embeddings | Sentence Transformers | Local model |
| LLM | OpenRouter | Chat completions |
| Files | Local `media/` | No S3 required for learning |
| Queues / cache | **None** | No Celery, Redis, Qdrant |

**Never store embedding vectors in PostgreSQL/SQLite.**

---

## Repository map

```
rag-chat-app/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md                 # This file — architecture, pipeline, workflow
├── GUIDE.md                  # Step-by-step API learning path
├── docs/
│   ├── schema.mmd            # ER diagram (Mermaid)
│   ├── VECTOR_DB.md          # ChromaDB / embeddings guide
│   └── API_TESTING.md        # Swagger (drf-yasg) + Postman
├── config/                   # Settings, root URLs
├── accounts/                 # Custom User (email auth)
├── knowledge/                # KnowledgeBase + Document
└── chat/                     # ChatSession + ChatMessage
```

| App | Owns | Your job |
|-----|------|----------|
| `config` | Settings, JWT, media, URL includes | Extend settings; add Swagger URLs when ready |
| `accounts` | `User` (email login/signup) | Signup, me serializers/views |
| `knowledge` | `KnowledgeBase`, `Document` | CRUD, upload, later ingest service |
| `chat` | `ChatSession`, `ChatMessage` | Sessions, messages, later RAG call |

---

## Data design (read before coding)

Open [`docs/schema.mmd`](docs/schema.mmd) in any Mermaid viewer (GitHub, VS Code Mermaid extension, mermaid.live).

Mental model:

- **`accounts.User`** — email + password (+ optional `full_name`); this is login/signup  
- **`KnowledgeBase`** — a collection; `chroma_collection_id` is only a **name/id string** pointing at Chroma  
- **`Document`** — one source (file path or URL) + processing `status` / `chunk_count`  
- **`ChatSession` / `ChatMessage`** — conversation history for the UI and debugging  

ChromaDB collections hold vectors and chunk text, tagged with `document_id` / `knowledge_base_id` in metadata.

---

## How a developer should work on this project

### 1. Set up once

```bash
cd rag-chat-app
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

If Django is “not found” after activating the venv (common in some IDE terminals), run:

```bash
.venv\Scripts\python.exe manage.py runserver
```

### 2. Follow the learning order (do not skip)

Treat features as vertical slices. Finish auth before knowledge; knowledge before chat; chat placeholder before RAG.

Full steps, API map, and checklist: **[GUIDE.md](GUIDE.md)**

Recommended daily rhythm:

1. Pick **one** checklist item from `GUIDE.md`.
2. Read the related model(s).
3. Add serializer → view/viewset → url.
4. Test with **Swagger** and/or **Postman** (see [docs/API_TESTING.md](docs/API_TESTING.md)).
5. Confirm ownership rules (user A never sees user B’s data).
6. Tick the checklist item.

### 3. Where to put new code

| Kind of code | Prefer |
|--------------|--------|
| JSON shape / validation | `serializers.py` in the app |
| HTTP / permissions / queryset | `views.py` |
| Routes | app `urls.py` + include from `config/urls.py` |
| Swagger schema URLs | `config/urls.py` |
| Text extract, chunk, embed, Chroma | `knowledge/services/` (create when needed) |
| OpenRouter + retrieval | `chat/services/` (create when needed) |
| One-off scripts | `manage.py` commands later if useful |

Keep views thin. Put RAG/ingest logic in services so endpoints stay readable.

### 4. Environment variables

Copy from `.env.example`. For early steps you only need `SECRET_KEY` and `DEBUG`. Add `OPENROUTER_API_KEY` when you reach chat RAG. Switch `USE_POSTGRES=True` only if you intentionally leave SQLite.

### 5. Migrations habit

After any model change:

```bash
python manage.py makemigrations
python manage.py migrate
```

Do not hand-edit migration files unless you know why.

### 6. Testing while learning

Prefer this loop:

1. Implement endpoint  
2. Smoke-test in Swagger  
3. Save request in Postman collection  
4. Cover happy path + `401` + validation errors  

Details: **[docs/API_TESTING.md](docs/API_TESTING.md)**

When you are comfortable, add APITestCase classes under each app’s `tests.py`.

### 7. Definition of done for a feature

A feature is done when:

- It appears in the API map in `GUIDE.md` and behaves as described
- Querysets are scoped to the authenticated user
- You can call it from Postman (and Swagger if configured)
- Admin still makes sense for that model
- No embedding arrays were added to SQL models

---

## Current implementation status

| Area | Status |
|------|--------|
| Project scaffold, settings, JWT token routes | Ready |
| Models: User (email auth), KnowledgeBase, Document, ChatSession, ChatMessage | Ready |
| Architecture + pipeline docs (this README) | Ready |
| Schema diagram (`docs/schema.mmd`) | Ready |
| Vector DB guide | Ready (`docs/VECTOR_DB.md`) |
| Swagger / Postman guide | Ready (`docs/API_TESTING.md`) |
| Account / knowledge / chat REST endpoints | To build (see GUIDE) |
| drf-yasg wired in project | To add (follow API_TESTING) |
| Chroma ingest + OpenRouter RAG | To build (GUIDE steps 6–7) |

---

## Architecture constraints (do not “improve” away)

- **SQL = metadata + chat only**
- **ChromaDB = vectors + chunk text**
- **Sync processing first** — no Celery/Redis until the product clearly needs them
- **Local media** for uploads during learning
- **One Chroma collection per knowledge base** (via `chroma_collection_id`)

---

## Useful URLs after `runserver`

| URL | Use |
|-----|-----|
| http://127.0.0.1:8000/admin/ | Inspect models |
| http://127.0.0.1:8000/api/auth/token/ | Obtain JWT |
| http://127.0.0.1:8000/api/… | Your endpoints as you add them |
| http://127.0.0.1:8000/swagger/ | Swagger UI (after you add drf-yasg) |

---

## Documentation index

| Doc | Audience | Contents |
|-----|----------|----------|
| [README.md](README.md) | Developers | Architecture, pipelines, workflow |
| [GUIDE.md](GUIDE.md) | Beginners | Step order, API map, learning checklist |
| [docs/VECTOR_DB.md](docs/VECTOR_DB.md) | Builders | ChromaDB, embeddings, ingest & retrieve |
| [docs/API_TESTING.md](docs/API_TESTING.md) | Builders | Swagger (drf-yasg) + Postman |
| [docs/schema.mmd](docs/schema.mmd) | Everyone | ER diagram (Mermaid) |

---

## Start here today

1. Skim **Architecture** and **Pipelines** above.  
2. Run the server and log into admin.  
3. Open `GUIDE.md` → complete Step 0 and Step 2 (accounts API).  
4. When you have a few endpoints, follow `docs/API_TESTING.md` for Swagger + Postman.

Build only what the current step needs. Resist adding microservices, queues, or extra vector databases.

```
`accounts\admin.py`:

```py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "full_name")
    list_filter = ("is_staff", "is_active", "is_superuser")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )

    # AbstractUser admin expects "username" — point it at email instead
    filter_horizontal = ("groups", "user_permissions")

```
`accounts\apps.py`:

```py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

```
`accounts\migrations\0001_initial.py`:

```py
# Generated by Django 6.0.7 on 2026-07-25 16:55

import accounts.models
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='email address')),
                ('full_name', models.CharField(blank=True, max_length=150)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'ordering': ['-date_joined'],
            },
            managers=[
                ('objects', accounts.models.UserManager()),
            ],
        ),
    ]

```
`accounts\models.py`:

```py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Create users with email + password (no username)."""

    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Single auth model for KnowledgeNest login / signup.

    Signup fields:  email, password, full_name (optional)
    Login fields:   email, password  →  JWT access + refresh

    No separate Profile table — keep auth simple.
    """

    username = None  # unused — email is the login id
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser only asks for email + password

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

```
`accounts\serializers.py`:

```py
from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Public fields returned for the authenticated user."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "email",
            "date_joined",
        ]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields that an authenticated user may update."""

    class Meta:
        model = User
        fields = ["full_name"]


class SignupSerializer(serializers.ModelSerializer):
    """Request body for registering a user."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "full_name",
        ]

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return email

    def validate(self, attrs):
        candidate_user = User(
            email=attrs.get("email", ""),
            full_name=attrs.get("full_name", ""),
        )
        password_validation.validate_password(
            attrs["password"],
            user=candidate_user,
        )
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
        )


class LoginSerializer(serializers.Serializer):
    """Request body for email/password login."""

    email = serializers.EmailField(
        help_text="Registered email address",
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        help_text="Account password",
    )

    def validate(self, attrs):
        email = User.objects.normalize_email(attrs["email"]).lower()
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is disabled."
            )

        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Request body for a password-reset request."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return User.objects.normalize_email(value).lower()


class ChangePasswordSerializer(serializers.Serializer):
    """Request body for changing the authenticated user's password."""

    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    def validate_new_password(self, value):
        user = self.context["request"].user
        password_validation.validate_password(value, user=user)
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Incorrect old password."}
            )

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different."}
            )

        return attrs


class LogoutSerializer(serializers.Serializer):
    """Validate that a refresh token belongs to the current user."""

    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError(
                "Invalid or expired refresh token."
            ) from exc

        request = self.context["request"]
        token_user_id = str(token.get("user_id", ""))

        if token_user_id != str(request.user.pk):
            raise serializers.ValidationError(
                "This refresh token does not belong to the authenticated user."
            )

        return value


class TokenResponseSerializer(serializers.Serializer):
    """JWT token pair returned by register and login."""

    refresh = serializers.CharField()
    access = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """Successful register/login response."""

    message = serializers.CharField()
    user = UserSerializer()
    tokens = TokenResponseSerializer()


class MessageResponseSerializer(serializers.Serializer):
    """Standard successful message response."""

    message = serializers.CharField()

```
`accounts\tests.py`:

```py
from django.test import TestCase

# Create your tests here.
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class AccountsApiSmokeTests(APITestCase):
    register_url = "/api/accounts/register/"
    login_url = "/api/accounts/login/"
    forgot_password_url = "/api/accounts/forgot-password/"
    change_password_url = "/api/accounts/change-password/"
    profile_url = "/api/accounts/profile/"
    logout_url = "/api/accounts/logout/"

    email = "smoke@example.com"
    password = "StrongPassword123!"
    new_password = "NewStrongPassword456!"

    def create_user(self):
        return User.objects.create_user(
            email=self.email,
            password=self.password,
            full_name="Smoke User",
        )

    def login(self, password=None):
        response = self.client.post(
            self.login_url,
            {
                "email": self.email,
                "password": password or self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["tokens"]

    def authenticate(self, access_token):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

    def test_register(self):
        response = self.client.post(
            self.register_url,
            {
                "email": self.email,
                "password": self.password,
                "full_name": "Smoke User",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.email).exists())
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    def test_duplicate_registration_is_rejected(self):
        self.create_user()

        response = self.client.post(
            self.register_url,
            {
                "email": self.email.upper(),
                "password": self.password,
                "full_name": "Duplicate User",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_and_invalid_login(self):
        self.create_user()

        valid_response = self.client.post(
            self.login_url,
            {"email": self.email, "password": self.password},
            format="json",
        )
        invalid_response = self.client.post(
            self.login_url,
            {"email": self.email, "password": "WrongPassword123!"},
            format="json",
        )

        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_has_generic_response(self):
        response = self.client.post(
            self.forgot_password_url,
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_change_password(self):
        user = self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        response = self.client.post(
            self.change_password_url,
            {
                "old_password": self.password,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.new_password))
        self.assertFalse(user.check_password(self.password))

    def test_profile_get_and_patch(self):
        self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        get_response = self.client.get(self.profile_url)
        patch_response = self.client.patch(
            self.profile_url,
            {"full_name": "Updated Smoke User"},
            format="json",
        )

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            patch_response.data["full_name"],
            "Updated Smoke User",
        )

    def test_logout(self):
        self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        response = self.client.post(
            self.logout_url,
            {"refresh": tokens["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_account(self):
        self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        response = self.client.delete(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(email=self.email).exists())
```
`accounts\urls.py`:

```py
from django.urls import path

from .views import (
    ChangePasswordView,
    DashboardSummaryView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    ProfileView,
    SignupView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", SignupView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard-summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
]
```
`accounts\views.py`:

```py
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    SignupSerializer,
    UserSerializer,
)

# ---------------------------------------------------------------------------
# Reusable Swagger response schemas
# ---------------------------------------------------------------------------
_token_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "access": openapi.Schema(type=openapi.TYPE_STRING, description="JWT access token"),
        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="JWT refresh token"),
    },
)

_user_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
        "full_name": openapi.Schema(type=openapi.TYPE_STRING),
        "date_joined": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
    },
)

_auth_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "user": _user_schema,
        "tokens": _token_schema,
    },
)

_message_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

_401_response = openapi.Response(
    description="Authentication required. Include `Authorization: Bearer <access_token>`.",
)
_400_response = openapi.Response(description="Validation error.")


# ---------------------------------------------------------------------------
# Authentication APIs
# ---------------------------------------------------------------------------

class SignupView(APIView):
    """
    POST /api/accounts/register/

    Create a new user account with email, password, and optional full_name.
    Returns JWT access and refresh tokens on success.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_register",
        operation_summary="Register a new user",
        operation_description=(
            "Create an account with **email**, **password**, and an optional **full_name**.\n\n"
            "On success, returns the created user data along with JWT `access` and `refresh` tokens.\n\n"
            "No `Authorization` header is required for this endpoint."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    example="user@gmail.com",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    minLength=8,
                    example="Password123!",
                ),
                "full_name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Test User",
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Account created successfully.",
                schema=_auth_response_schema,
                examples={
                    "application/json": {
                        "message": "Account created successfully.",
                        "user": {
                            "id": 1,
                            "email": "user@gmail.com",
                            "full_name": "Test User",
                            "date_joined": "2026-07-26T07:36:06Z",
                        },
                        "tokens": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                    }
                },
            ),
            400: _400_response,
        },
        security=[],  # public — no auth required
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Account created successfully.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/accounts/login/

    Authenticate a user using email and password.
    Returns JWT access and refresh tokens on success.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_login",
        operation_summary="Login",
        operation_description=(
            "Authenticate using **email** and **password**.\n\n"
            "Returns JWT `access` and `refresh` tokens.\n\n"
            "Use the `access` token in the `Authorization: Bearer <access_token>` header "
            "for all protected endpoints.\n\n"
            "No `Authorization` header is required for this endpoint."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    example="user@gmail.com",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    example="Password123!",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Login successful.",
                schema=_auth_response_schema,
                examples={
                    "application/json": {
                        "message": "Login successful.",
                        "user": {
                            "id": 1,
                            "email": "user@gmail.com",
                            "full_name": "Test User",
                            "date_joined": "2026-07-26T07:36:06Z",
                        },
                        "tokens": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                    }
                },
            ),
            400: openapi.Response(description="Invalid email or password."),
        },
        security=[],  # public — no auth required
    )
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """
    POST /api/accounts/forgot-password/

    Request a password-reset link by email.
    Always returns a generic message (does not reveal whether the email exists).
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_forgot_password",
        operation_summary="Forgot password",
        operation_description=(
            "Request a password-reset email.\n\n"
            "A **generic response** is always returned — whether or not the email is registered — "
            "to prevent account enumeration.\n\n"
            "Email delivery is a placeholder for now.\n\n"
            "No `Authorization` header is required for this endpoint."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    example="user@gmail.com",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Generic response sent regardless of whether the email exists.",
                schema=_message_schema,
                examples={
                    "application/json": {
                        "message": "Password reset email sent"
                    }
                },
            ),
            400: _400_response,
        },
        security=[],
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Generic response — never reveal whether the account exists.
        # Wire real email delivery later without changing this API contract.
        return Response(
            {"message": "Password reset email sent"},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    POST /api/accounts/change-password/

    Change the authenticated user's password.
    Requires a valid Bearer access token.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_change_password",
        operation_summary="Change password",
        operation_description=(
            "Change the current user's password.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header.\n\n"
            "The `old_password` must match the current password. "
            "The `new_password` must be different and pass Django's password validators."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["old_password", "new_password"],
            properties={
                "old_password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    example="Password123!",
                ),
                "new_password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    minLength=8,
                    example="NewPassword123!",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password changed successfully.",
                schema=_message_schema,
                examples={
                    "application/json": {"message": "Password changed successfully"}
                },
            ),
            400: openapi.Response(description="Old password incorrect or new password fails validation."),
            401: _401_response,
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        return Response(
            {"message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# User Profile APIs
# ---------------------------------------------------------------------------

class ProfileView(APIView):
    """
    GET    /api/accounts/profile/  → get current user's profile
    PATCH  /api/accounts/profile/  → update profile (full_name)
    DELETE /api/accounts/profile/  → delete the account permanently
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="profile_get",
        operation_summary="Get profile",
        operation_description=(
            "Return the authenticated user's profile data.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        responses={
            200: openapi.Response(
                description="User profile.",
                schema=_user_schema,
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@gmail.com",
                        "full_name": "Test User",
                        "date_joined": "2026-07-26T07:36:06Z",
                    }
                },
            ),
            401: _401_response,
        },
    )
    def get(self, request):
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="profile_update",
        operation_summary="Update profile",
        operation_description=(
            "Update the authenticated user's profile. Currently only **full_name** may be changed.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "full_name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Updated Name",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Profile updated.",
                schema=_user_schema,
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@gmail.com",
                        "full_name": "Updated Name",
                        "date_joined": "2026-07-26T07:36:06Z",
                    }
                },
            ),
            400: _400_response,
            401: _401_response,
        },
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="profile_delete",
        operation_summary="Delete account",
        operation_description=(
            "Permanently delete the authenticated user's account. **This action is irreversible.**\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        responses={
            200: openapi.Response(
                description="Account deleted.",
                schema=_message_schema,
                examples={
                    "application/json": {"message": "Account deleted successfully"}
                },
            ),
            401: _401_response,
        },
    )
    def delete(self, request):
        request.user.delete()
        return Response(
            {"message": "Account deleted successfully"},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutView(APIView):
    """
    POST /api/accounts/logout/

    Validate ownership of the refresh token and confirm logout.
    The client must delete its stored tokens after calling this endpoint.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_logout",
        operation_summary="Logout",
        operation_description=(
            "Validate that the provided refresh token belongs to the current user.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header.\n\n"
            "After a successful response, the **client must delete** its stored access and refresh tokens. "
            "Server-side blacklisting is not used in this implementation."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The JWT refresh token to invalidate.",
                    example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Logout successful.",
                schema=_message_schema,
                examples={
                    "application/json": {"message": "Logout successful"}
                },
            ),
            400: openapi.Response(description="Invalid or expired refresh token."),
            401: _401_response,
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        # Blacklist the refresh token so it cannot be reused
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except Exception:
            pass  # token was already validated in serializer

        return Response(
            {"message": "Logout successful"},
            status=status.HTTP_200_OK,
        )
from knowledge.models import KnowledgeBase, Document
from chat.models import ChatSession, ChatMessage


class DashboardSummaryView(APIView):
    """
    GET /api/accounts/dashboard-summary/

    Return counts of the authenticated user's knowledge bases,
    documents, chat sessions, and chat messages.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="dashboard_summary",
        operation_summary="Dashboard summary",
        operation_description=(
            "Return aggregate counts for the authenticated user: "
            "knowledge bases, documents, chat sessions, and messages.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        responses={200: _message_schema, 401: _401_response},
    )
    def get(self, request):
        user = request.user
        kb_ids = KnowledgeBase.objects.filter(user=user).values_list("id", flat=True)

        return Response(
            {
                "total_knowledge_bases": kb_ids.count(),
                "total_documents": Document.objects.filter(knowledge_base_id__in=kb_ids).count(),
                "total_chat_sessions": ChatSession.objects.filter(user=user).count(),
                "total_messages": ChatMessage.objects.filter(session__user=user).count(),
            },
            status=status.HTTP_200_OK,
        )
```
`api.json`:

```json
{
  "swagger": "2.0",
  "info": {
    "title": "RAG Chat API",
    "description": "API documentation for the RAG Chat application",
    "version": "v1"
  },
  "host": "127.0.0.1:8000",
  "schemes": [
    "http"
  ],
  "basePath": "/api",
  "consumes": [
    "application/json"
  ],
  "produces": [
    "application/json"
  ],
  "securityDefinitions": {
    "Bearer": {
      "type": "apiKey",
      "name": "Authorization",
      "in": "header",
      "description": "JWT Authorization header.\n\nFormat: **Bearer &lt;access_token&gt;**\n\nGet a token from POST /api/accounts/login/"
    }
  },
  "security": [
    {
      "Bearer": []
    }
  ],
  "paths": {
    "/accounts/change-password/": {
      "post": {
        "operationId": "auth_change_password",
        "summary": "Change password",
        "description": "Change the current user's password.\n\n**Authentication required** \u00e2\u20ac\u201d include `Authorization: Bearer <access_token>` in the header.\n\nThe `old_password` must match the current password. The `new_password` must be different and pass Django's password validators.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "required": [
                "old_password",
                "new_password"
              ],
              "type": "object",
              "properties": {
                "old_password": {
                  "type": "string",
                  "format": "password",
                  "example": "Password123!"
                },
                "new_password": {
                  "type": "string",
                  "format": "password",
                  "example": "NewPassword123!",
                  "minLength": 8
                }
              }
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Password changed successfully.",
            "schema": {
              "type": "object",
              "properties": {
                "message": {
                  "type": "string"
                }
              }
            },
            "examples": {
              "application/json": {
                "message": "Password changed successfully"
              }
            }
          },
          "400": {
            "description": "Old password incorrect or new password fails validation."
          },
          "401": {
            "description": "Authentication required. Include `Authorization: Bearer <access_token>`."
          }
        },
        "tags": [
          "Authentication"
        ]
      },
      "parameters": []
    },
    "/accounts/forgot-password/": {
      "post": {
        "operationId": "auth_forgot_password",
        "summary": "Forgot password",
        "description": "Request a password-reset email.\n\nA **generic response** is always returned \u00e2\u20ac\u201d whether or not the email is registered \u00e2\u20ac\u201d to prevent account enumeration.\n\nEmail delivery is a placeholder for now.\n\nNo `Authorization` header is required for this endpoint.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "required": [
                "email"
              ],
              "type": "object",
              "properties": {
                "email": {
                  "type": "string",
                  "format": "email",
                  "example": "user@gmail.com"
                }
              }
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Generic response sent regardless of whether the email exists.",
            "schema": {
              "type": "object",
              "properties": {
                "message": {
                  "type": "string"
                }
              }
            },
            "examples": {
              "application/json": {
                "message": "Password reset email sent"
              }
            }
          },
          "400": {
            "description": "Validation error."
          }
        },
        "tags": [
          "Authentication"
        ],
        "security": []
      },
      "parameters": []
    },
    "/accounts/login/": {
      "post": {
        "operationId": "auth_login",
        "summary": "Login",
        "description": "Authenticate using **email** and **password**.\n\nReturns JWT `access` and `refresh` tokens.\n\nUse the `access` token in the `Authorization: Bearer <access_token>` header for all protected endpoints.\n\nNo `Authorization` header is required for this endpoint.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "required": [
                "email",
                "password"
              ],
              "type": "object",
              "properties": {
                "email": {
                  "type": "string",
                  "format": "email",
                  "example": "user@gmail.com"
                },
                "password": {
                  "type": "string",
                  "format": "password",
                  "example": "Password123!"
                }
              }
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Login successful.",
            "schema": {
              "type": "object",
              "properties": {
                "message": {
                  "type": "string"
                },
                "user": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "integer"
                    },
                    "email": {
                      "type": "string",
                      "format": "email"
                    },
                    "full_name": {
                      "type": "string"
                    },
                    "date_joined": {
                      "type": "string",
                      "format": "date-time"
                    }
                  }
                },
                "tokens": {
                  "type": "object",
                  "properties": {
                    "access": {
                      "description": "JWT access token",
                      "type": "string"
                    },
                    "refresh": {
                      "description": "JWT refresh token",
                      "type": "string"
                    }
                  }
                }
              }
            },
            "examples": {
              "application/json": {
                "message": "Login successful.",
                "user": {
                  "id": 1,
                  "email": "user@gmail.com",
                  "full_name": "Test User",
                  "date_joined": "2026-07-26T07:36:06Z"
                },
                "tokens": {
                  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
              }
            }
          },
          "400": {
            "description": "Invalid email or password."
          }
        },
        "tags": [
          "Authentication"
        ],
        "security": []
      },
      "parameters": []
    },
    "/accounts/logout/": {
      "post": {
        "operationId": "auth_logout",
        "summary": "Logout",
        "description": "Validate that the provided refresh token belongs to the current user.\n\n**Authentication required** \u00e2\u20ac\u201d include `Authorization: Bearer <access_token>` in the header.\n\nAfter a successful response, the **client must delete** its stored access and refresh tokens. Server-side blacklisting is not used in this implementation.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "required": [
                "refresh"
              ],
              "type": "object",
              "properties": {
                "refresh": {
                  "description": "The JWT refresh token to invalidate.",
                  "type": "string",
                  "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
              }
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Logout successful.",
            "schema": {
              "type": "object",
              "properties": {
                "message": {
                  "type": "string"
                }
              }
            },
            "examples": {
              "application/json": {
                "message": "Logout successful"
              }
            }
          },
          "400": {
            "description": "Invalid or expired refresh token."
          },
          "401": {
            "description": "Authentication required. Include `Authorization: Bearer <access_token>`."
          }
        },
        "tags": [
          "Authentication"
        ]
      },
      "parameters": []
    },
    "/accounts/profile/": {
      "get": {
        "operationId": "profile_get",
        "summary": "Get profile",
        "description": "Return the authenticated user's profile data.\n\n**Authentication required** \u00e2\u20ac\u201d include `Authorization: Bearer <access_token>` in the header.",
        "parameters": [],
        "responses": {
          "200": {
            "description": "User profile.",
            "schema": {
              "type": "object",
              "properties": {
                "id": {
                  "type": "integer"
                },
                "email": {
                  "type": "string",
                  "format": "email"
                },
                "full_name": {
                  "type": "string"
                },
                "date_joined": {
                  "type": "string",
                  "format": "date-time"
                }
              }
            },
            "examples": {
              "application/json": {
                "id": 1,
                "email": "user@gmail.com",
                "full_name": "Test User",
                "date_joined": "2026-07-26T07:36:06Z"
              }
            }
          },
          "401": {
            "description": "Authentication required. Include `Authorization: Bearer <access_token>`."
          }
        },
        "tags": [
          "User Profile"
        ]
      },
      "patch": {
        "operationId": "profile_update",
        "summary": "Update profile",
        "description": "Update the authenticated user's profile. Currently only **full_name** may be changed.\n\n**Authentication required** \u00e2\u20ac\u201d include `Authorization: Bearer <access_token>` in the header.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "type": "object",
              "properties": {
                "full_name": {
                  "type": "string",
                  "example": "Updated Name"
                }
              }
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Profile updated.",
            "schema": {
              "type": "object",
              "properties": {
                "id": {
                  "type": "integer"
                },
                "email": {
                  "type": "string",
                  "format": "email"
                },
                "full_name": {
                  "type": "string"
                },
                "date_joined": {
                  "type": "string",
                  "format": "date-time"
                }
              }
            },
            "examples": {
              "application/json": {
                "id": 1,
                "email": "user@gmail.com",
                "full_name": "Updated Name",
                "date_joined": "2026-07-26T07:36:06Z"
              }
            }
          },
          "400": {
            "description": "Validation error."
          },
          "401": {
            "description": "Authentication required. Include `Authorization: Bearer <access_token>`."
          }
        },
        "tags": [
          "User Profile"
        ]
      },
      "delete": {
        "operationId": "profile_delete",
        "summary": "Delete account",
        "description": "Permanently delete the authenticated user's account. **This action is irreversible.**\n\n**Authentication required** \u00e2\u20ac\u201d include `Authorization: Bearer <access_token>` in the header.",
        "parameters": [],
        "responses": {
          "200": {
            "description": "Account deleted.",
            "schema": {
              "type": "object",
              "properties": {
                "message": {
                  "type": "string"
                }
              }
            },
            "examples": {
              "application/json": {
                "message": "Account deleted successfully"
              }
            }
          },
          "401": {
            "description": "Authentication required. Include `Authorization: Bearer <access_token>`."
          }
        },
        "tags": [
          "User Profile"
        ]
      },
      "parameters": []
    },
    "/accounts/register/": {
      "post": {
        "operationId": "auth_register",
        "summary": "Register a new user",
        "description": "Create an account with **email**, **password**, and an optional **full_name**.\n\nOn success, returns the created user data along with JWT `access` and `refresh` tokens.\n\nNo `Authorization` header is required for this endpoint.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "required": [
                "email",
                "password"
              ],
              "type": "object",
              "properties": {
                "email": {
                  "type": "string",
                  "format": "email",
                  "example": "user@gmail.com"
                },
                "password": {
                  "type": "string",
                  "format": "password",
                  "example": "Password123!",
                  "minLength": 8
                },
                "full_name": {
                  "type": "string",
                  "example": "Test User"
                }
              }
            }
          }
        ],
        "responses": {
          "201": {
            "description": "Account created successfully.",
            "schema": {
              "type": "object",
              "properties": {
                "message": {
                  "type": "string"
                },
                "user": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "integer"
                    },
                    "email": {
                      "type": "string",
                      "format": "email"
                    },
                    "full_name": {
                      "type": "string"
                    },
                    "date_joined": {
                      "type": "string",
                      "format": "date-time"
                    }
                  }
                },
                "tokens": {
                  "type": "object",
                  "properties": {
                    "access": {
                      "description": "JWT access token",
                      "type": "string"
                    },
                    "refresh": {
                      "description": "JWT refresh token",
                      "type": "string"
                    }
                  }
                }
              }
            },
            "examples": {
              "application/json": {
                "message": "Account created successfully.",
                "user": {
                  "id": 1,
                  "email": "user@gmail.com",
                  "full_name": "Test User",
                  "date_joined": "2026-07-26T07:36:06Z"
                },
                "tokens": {
                  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
              }
            }
          },
          "400": {
            "description": "Validation error."
          }
        },
        "tags": [
          "Authentication"
        ],
        "security": []
      },
      "parameters": []
    },
    "/auth/token/": {
      "post": {
        "operationId": "auth_token_create",
        "description": "Takes a set of user credentials and returns an access and refresh JSON web\ntoken pair to prove the authentication of those credentials.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/TokenObtainPair"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/TokenObtainPair"
            }
          }
        },
        "tags": [
          "auth"
        ]
      },
      "parameters": []
    },
    "/auth/token/refresh/": {
      "post": {
        "operationId": "auth_token_refresh_create",
        "description": "Takes a refresh type JSON web token and returns an access type JSON web\ntoken if the refresh token is valid.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/TokenRefresh"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/TokenRefresh"
            }
          }
        },
        "tags": [
          "auth"
        ]
      },
      "parameters": []
    },
    "/chat/sessions/": {
      "get": {
        "operationId": "chat_sessions_list",
        "description": "GET    /api/chat/sessions/\nPOST   /api/chat/sessions/\nGET    /api/chat/sessions/{id}/\nDELETE /api/chat/sessions/{id}/",
        "parameters": [
          {
            "name": "page",
            "in": "query",
            "description": "A page number within the paginated result set.",
            "required": false,
            "type": "integer"
          }
        ],
        "responses": {
          "200": {
            "description": "",
            "schema": {
              "required": [
                "count",
                "results"
              ],
              "type": "object",
              "properties": {
                "count": {
                  "type": "integer"
                },
                "next": {
                  "type": "string",
                  "format": "uri",
                  "x-nullable": true
                },
                "previous": {
                  "type": "string",
                  "format": "uri",
                  "x-nullable": true
                },
                "results": {
                  "type": "array",
                  "items": {
                    "$ref": "#/definitions/ChatSession"
                  }
                }
              }
            }
          }
        },
        "tags": [
          "chat"
        ]
      },
      "post": {
        "operationId": "chat_sessions_create",
        "description": "GET    /api/chat/sessions/\nPOST   /api/chat/sessions/\nGET    /api/chat/sessions/{id}/\nDELETE /api/chat/sessions/{id}/",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/ChatSession"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/ChatSession"
            }
          }
        },
        "tags": [
          "chat"
        ]
      },
      "parameters": []
    },
    "/chat/sessions/{id}/": {
      "get": {
        "operationId": "chat_sessions_read",
        "description": "GET    /api/chat/sessions/\nPOST   /api/chat/sessions/\nGET    /api/chat/sessions/{id}/\nDELETE /api/chat/sessions/{id}/",
        "parameters": [],
        "responses": {
          "200": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/ChatSessionDetail"
            }
          }
        },
        "tags": [
          "chat"
        ]
      },
      "delete": {
        "operationId": "chat_sessions_delete",
        "description": "GET    /api/chat/sessions/\nPOST   /api/chat/sessions/\nGET    /api/chat/sessions/{id}/\nDELETE /api/chat/sessions/{id}/",
        "parameters": [],
        "responses": {
          "204": {
            "description": ""
          }
        },
        "tags": [
          "chat"
        ]
      },
      "parameters": [
        {
          "name": "id",
          "in": "path",
          "required": true,
          "type": "string"
        }
      ]
    },
    "/chat/sessions/{session_id}/messages/": {
      "get": {
        "operationId": "chat_sessions_messages_list",
        "description": "GET  /api/chat/sessions/{session_id}/messages/\nPOST /api/chat/sessions/{session_id}/messages/",
        "parameters": [],
        "responses": {
          "200": {
            "description": ""
          }
        },
        "tags": [
          "chat"
        ]
      },
      "post": {
        "operationId": "chat_sessions_messages_create",
        "description": "GET  /api/chat/sessions/{session_id}/messages/\nPOST /api/chat/sessions/{session_id}/messages/",
        "parameters": [],
        "responses": {
          "201": {
            "description": ""
          }
        },
        "tags": [
          "chat"
        ]
      },
      "parameters": [
        {
          "name": "session_id",
          "in": "path",
          "required": true,
          "type": "string"
        }
      ]
    },
    "/chat/token/": {
      "post": {
        "operationId": "chat_token_create",
        "description": "Takes a set of user credentials and returns an access and refresh JSON web\ntoken pair to prove the authentication of those credentials.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/TokenObtainPair"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/TokenObtainPair"
            }
          }
        },
        "tags": [
          "chat"
        ]
      },
      "parameters": []
    },
    "/chat/token/refresh/": {
      "post": {
        "operationId": "chat_token_refresh_create",
        "description": "Takes a refresh type JSON web token and returns an access type JSON web\ntoken if the refresh token is valid.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/TokenRefresh"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/TokenRefresh"
            }
          }
        },
        "tags": [
          "chat"
        ]
      },
      "parameters": []
    },
    "/knowledge/bases/": {
      "get": {
        "operationId": "knowledge_bases_list",
        "summary": "CRUD operations for user Knowledge Bases.",
        "description": "Users can only access their own knowledge bases.",
        "parameters": [
          {
            "name": "page",
            "in": "query",
            "description": "A page number within the paginated result set.",
            "required": false,
            "type": "integer"
          }
        ],
        "responses": {
          "200": {
            "description": "",
            "schema": {
              "required": [
                "count",
                "results"
              ],
              "type": "object",
              "properties": {
                "count": {
                  "type": "integer"
                },
                "next": {
                  "type": "string",
                  "format": "uri",
                  "x-nullable": true
                },
                "previous": {
                  "type": "string",
                  "format": "uri",
                  "x-nullable": true
                },
                "results": {
                  "type": "array",
                  "items": {
                    "$ref": "#/definitions/KnowledgeBase"
                  }
                }
              }
            }
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "post": {
        "operationId": "knowledge_bases_create",
        "summary": "CRUD operations for user Knowledge Bases.",
        "description": "Users can only access their own knowledge bases.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        ],
        "responses": {
          "201": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "parameters": []
    },
    "/knowledge/bases/{id}/": {
      "get": {
        "operationId": "knowledge_bases_read",
        "summary": "CRUD operations for user Knowledge Bases.",
        "description": "Users can only access their own knowledge bases.",
        "parameters": [],
        "responses": {
          "200": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "put": {
        "operationId": "knowledge_bases_update",
        "summary": "CRUD operations for user Knowledge Bases.",
        "description": "Users can only access their own knowledge bases.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "patch": {
        "operationId": "knowledge_bases_partial_update",
        "summary": "CRUD operations for user Knowledge Bases.",
        "description": "Users can only access their own knowledge bases.",
        "parameters": [
          {
            "name": "data",
            "in": "body",
            "required": true,
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "",
            "schema": {
              "$ref": "#/definitions/KnowledgeBase"
            }
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "delete": {
        "operationId": "knowledge_bases_delete",
        "summary": "CRUD operations for user Knowledge Bases.",
        "description": "Users can only access their own knowledge bases.",
        "parameters": [],
        "responses": {
          "204": {
            "description": ""
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "parameters": [
        {
          "name": "id",
          "in": "path",
          "required": true,
          "type": "string"
        }
      ]
    },
    "/knowledge/bases/{kb_id}/documents/": {
      "get": {
        "operationId": "knowledge_bases_documents_list",
        "description": "",
        "parameters": [],
        "responses": {
          "200": {
            "description": ""
          }
        },
        "consumes": [
          "multipart/form-data",
          "application/x-www-form-urlencoded"
        ],
        "tags": [
          "knowledge"
        ]
      },
      "post": {
        "operationId": "knowledge_bases_documents_create",
        "description": "",
        "parameters": [],
        "responses": {
          "201": {
            "description": ""
          }
        },
        "consumes": [
          "multipart/form-data",
          "application/x-www-form-urlencoded"
        ],
        "tags": [
          "knowledge"
        ]
      },
      "parameters": [
        {
          "name": "kb_id",
          "in": "path",
          "required": true,
          "type": "string"
        }
      ]
    },
    "/knowledge/bases/{kb_id}/documents/{doc_id}/": {
      "get": {
        "operationId": "knowledge_bases_documents_read",
        "description": "",
        "parameters": [],
        "responses": {
          "200": {
            "description": ""
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "put": {
        "operationId": "knowledge_bases_documents_update",
        "description": "",
        "parameters": [],
        "responses": {
          "200": {
            "description": ""
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "patch": {
        "operationId": "knowledge_bases_documents_partial_update",
        "description": "",
        "parameters": [],
        "responses": {
          "200": {
            "description": ""
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "delete": {
        "operationId": "knowledge_bases_documents_delete",
        "description": "",
        "parameters": [],
        "responses": {
          "204": {
            "description": ""
          }
        },
        "tags": [
          "knowledge"
        ]
      },
      "parameters": [
        {
          "name": "kb_id",
          "in": "path",
          "required": true,
          "type": "string"
        },
        {
          "name": "doc_id",
          "in": "path",
          "required": true,
          "type": "string"
        }
      ]
    }
  },
  "definitions": {
    "TokenObtainPair": {
      "required": [
        "email",
        "password"
      ],
      "type": "object",
      "properties": {
        "email": {
          "title": "Email",
          "type": "string",
          "minLength": 1
        },
        "password": {
          "title": "Password",
          "type": "string",
          "minLength": 1
        }
      }
    },
    "TokenRefresh": {
      "required": [
        "refresh"
      ],
      "type": "object",
      "properties": {
        "refresh": {
          "title": "Refresh",
          "type": "string",
          "minLength": 1
        },
        "access": {
          "title": "Access",
          "type": "string",
          "readOnly": true,
          "minLength": 1
        }
      }
    },
    "ChatSession": {
      "type": "object",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string",
          "format": "uuid",
          "readOnly": true
        },
        "title": {
          "title": "Title",
          "type": "string",
          "maxLength": 255
        },
        "knowledge_base": {
          "title": "Knowledge base",
          "type": "string",
          "format": "uuid",
          "x-nullable": true
        },
        "created_at": {
          "title": "Created at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        },
        "updated_at": {
          "title": "Updated at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        },
        "message_count": {
          "title": "Message count",
          "type": "string",
          "readOnly": true
        }
      }
    },
    "ChatMessage": {
      "required": [
        "content"
      ],
      "type": "object",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string",
          "format": "uuid",
          "readOnly": true
        },
        "role": {
          "title": "Role",
          "type": "string",
          "enum": [
            "user",
            "assistant"
          ],
          "readOnly": true
        },
        "content": {
          "title": "Content",
          "type": "string",
          "minLength": 1
        },
        "created_at": {
          "title": "Created at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        }
      }
    },
    "ChatSessionDetail": {
      "type": "object",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string",
          "format": "uuid",
          "readOnly": true
        },
        "title": {
          "title": "Title",
          "type": "string",
          "maxLength": 255
        },
        "knowledge_base": {
          "title": "Knowledge base",
          "type": "string",
          "format": "uuid",
          "x-nullable": true
        },
        "created_at": {
          "title": "Created at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        },
        "updated_at": {
          "title": "Updated at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        },
        "message_count": {
          "title": "Message count",
          "type": "string",
          "readOnly": true
        },
        "messages": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/ChatMessage"
          },
          "readOnly": true
        }
      }
    },
    "KnowledgeBase": {
      "required": [
        "name"
      ],
      "type": "object",
      "properties": {
        "id": {
          "title": "Id",
          "type": "string",
          "format": "uuid",
          "readOnly": true
        },
        "owner": {
          "title": "Owner",
          "type": "integer",
          "readOnly": true
        },
        "name": {
          "title": "Name",
          "type": "string",
          "maxLength": 255,
          "minLength": 1
        },
        "description": {
          "title": "Description",
          "type": "string"
        },
        "chroma_collection_id": {
          "title": "Chroma collection id",
          "type": "string",
          "readOnly": true,
          "minLength": 1
        },
        "created_at": {
          "title": "Created at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        },
        "updated_at": {
          "title": "Updated at",
          "type": "string",
          "format": "date-time",
          "readOnly": true
        }
      }
    }
  }
}
```
`chat\admin.py`:

```py
from django.contrib import admin

from .models import ChatMessage, ChatSession


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "knowledge_base", "created_at", "updated_at")
    search_fields = ("title", "user__email")
    list_filter = ("created_at",)
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "created_at")
    list_filter = ("role", "created_at")

```
`chat\apps.py`:

```py
from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = 'chat'

```
`chat\migrations\0001_initial.py`:

```py
# Generated by Django 6.0.7 on 2026-07-25 16:55

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('knowledge', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('knowledge_base', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_sessions', to='knowledge.knowledgebase')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=20)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.chatsession')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]

```
`chat\migrations\0002_alter_chatsession_knowledge_base.py`:

```py
# Generated by Django 6.0.7 on 2026-07-26 09:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
        ("knowledge", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatsession",
            name="knowledge_base",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chat_sessions",
                to="knowledge.knowledgebase",
            ),
        ),
    ]

```
`chat\models.py`:

```py
import uuid

from django.conf import settings
from django.db import models

from knowledge.models import KnowledgeBase


class ChatSession(models.Model):
    """A conversation thread optionally tied to one knowledge base."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,   # <-- ALLOWS NULL IN DATABASE WHEN NO FILE IS UPLOADED
        blank=True,  # <-- ALLOWS BLANK/NONE IN SERIALIZERS & FORMS
    )
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Session {self.id}"


class ChatMessage(models.Model):
    """One message in a chat session (user question or assistant reply)."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
```
`chat\serializers.py`:

```py
"""
chat/serializers.py

Responsible only for:
- ORM <-> JSON conversion
- Validation
- Ownership rules
"""

from rest_framework import serializers

from knowledge.models import KnowledgeBase

from .models import ChatMessage, ChatSession
from .services.rag import generate_rag_response


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Read serializer for chat messages.
    """

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "role",
            "content",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "role",
            "created_at",
        ]


class ChatSessionSerializer(serializers.ModelSerializer):

    message_count = serializers.SerializerMethodField()

    knowledge_base = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ChatSession

        fields = [
            "id",
            "title",
            "knowledge_base",
            "created_at",
            "updated_at",
            "message_count",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "message_count",
        ]


    def get_message_count(self, obj):
        return obj.messages.count()


    def validate_knowledge_base(self, value):
        """
        Ensure user owns selected knowledge base.
        """

        if value is not None:

            request = self.context.get("request")

            if request and value.owner_id != request.user.id:
                raise serializers.ValidationError(
                    "You do not own this knowledge base."
                )

        return value


    def create(self, validated_data):

        validated_data["user"] = (
            self.context["request"].user
        )

        return super().create(validated_data)



class ChatSessionDetailSerializer(ChatSessionSerializer):

    messages = ChatMessageSerializer(
        many=True,
        read_only=True
    )

    class Meta(ChatSessionSerializer.Meta):

        fields = ChatSessionSerializer.Meta.fields + [
            "messages"
        ]



class CreateMessageSerializer(serializers.Serializer):

    content = serializers.CharField(
        max_length=10000,
        allow_blank=False
    )


    def create(self, validated_data):

        session = self.context["session"]

        user_content = validated_data["content"]


        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )


        reply_content = generate_rag_response(
            session,
            user_content
        )


        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=reply_content,
        )


        session.save(
            update_fields=[
                "updated_at"
            ]
        )


        return {
            "user_message": ChatMessageSerializer(
                user_msg
            ).data,

            "assistant_message": ChatMessageSerializer(
                assistant_msg
            ).data,
        }
```
`chat\services\__init__.py`:

```py
# chat/services package

```
`chat\services\rag.py`:

```py
import logging
import os

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


_EMBEDDING_MODEL = None



def get_embedding_model():

    global _EMBEDDING_MODEL


    if _EMBEDDING_MODEL is None:

        from sentence_transformers import SentenceTransformer


        model_name = os.getenv(
            "EMBEDDING_MODEL_NAME",
            "sentence-transformers/all-MiniLM-L6-v2",
        )


        _EMBEDDING_MODEL = SentenceTransformer(
            model_name
        )


        logger.info(
            "Embedding model '%s' loaded.",
            model_name
        )


    return _EMBEDDING_MODEL



def retrieve_context(
    chroma_collection_id,
    user_query,
    n_results=3
):

    import chromadb

    try:

        chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_PERSIST_DIR)
        )


        collection = chroma_client.get_collection(
            name=chroma_collection_id
        )


        model = get_embedding_model()


        query_vector = model.encode(
            user_query
        ).tolist()


        results = collection.query(
            query_embeddings=[
                query_vector
            ],
            n_results=n_results,
        )


        if results.get("documents"):

            return "\n\n".join(
                results["documents"][0]
            )


    except Exception:

        logger.exception(
            "ChromaDB retrieval failed."
        )


    return ""



def call_openrouter(
    messages,
    model,
    api_key
):

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",

            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },

            json={
                "model": model,
                "messages": messages,
            },

            timeout=30,
        )


    except requests.RequestException as exc:

        logger.exception(
            "OpenRouter network failure."
        )

        raise RuntimeError(
            str(exc)
        ) from exc



    if response.status_code != 200:

        logger.exception(
            "OpenRouter returned status %s",
            response.status_code
        )

        raise RuntimeError(
            f"OpenRouter error: {response.text}"
        )


    return response.json()["choices"][0]["message"]["content"]




def generate_rag_response(
    session,
    user_query
):

    context_text = ""


    kb = session.knowledge_base


    if kb and kb.chroma_collection_id:

        context_text = retrieve_context(
            kb.chroma_collection_id,
            user_query,
        )



    if context_text:

        system_prompt = (
            "Answer using only this context:\n\n"
            f"{context_text}"
        )

    else:

        system_prompt = (
            "You are a helpful AI assistant."
        )



    messages = [

        {
            "role": "system",
            "content": system_prompt,
        },

        {
            "role": "user",
            "content": user_query,
        },

    ]



    api_key = (
        getattr(settings, "OPENROUTER_API_KEY", None)
        or os.getenv("OPENROUTER_API_KEY")
    )



    if not api_key:

        logger.error(
            "OPENROUTER_API_KEY missing."
        )

        return (
            "Error: OpenRouter API key missing."
        )



    model = getattr(
        settings,
        "OPENROUTER_MODEL",
        "openai/gpt-3.5-turbo"
    )


    try:

        return call_openrouter(
            messages,
            model,
            api_key,
        )


    except RuntimeError as exc:

        logger.exception(
            "RAG generation failed."
        )

        return str(exc)
```
`chat\tests.py`:

```py
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

    @patch("chat.serializers.generate_rag_response", return_value="Mocked reply")
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

```
`chat\urls.py`:

```py
"""
chat/urls.py

Registers URL routes for the chat app ONLY:
  - /api/chat/sessions/              → ChatSessionViewSet (list, create, retrieve, destroy)
  - /api/chat/sessions/<id>/messages/ → ChatMessageListCreateView (list, create)

JWT token endpoints (token/, token/refresh/) are registered at the project
level in config/urls.py and do NOT belong in the chat app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatMessageListCreateView, ChatSessionViewSet

router = DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "sessions/<uuid:session_id>/messages/",
        ChatMessageListCreateView.as_view(),
        name="chat-messages",
    ),
]
```
`chat\views.py`:

```py
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
```
`config\asgi.py`:

```py
"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()

```
`config\exceptions.py`:

```py
"""
config/exceptions.py

Wrap all DRF error responses in a consistent JSON envelope:
{
    "status": "error",
    "status_code": 400,
    "errors": { ... }   ← original DRF error structure
}

This makes client-side error handling predictable — every error
response has the same shape regardless of error type.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "status": "error",
            "status_code": response.status_code,
            "errors": response.data,
        }

    return response

```
`config\settings.py`:

```py
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
```
`config\urls.py`:

```py
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
```
`config\wsgi.py`:

```py
"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

```
`docker-compose.yml`:

```yml
version: '3.8'

services:
  web:
    build: .
    container_name: rag_backend
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - chroma_data:/app/chroma_data
      - media_data:/app/media
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
      - USE_POSTGRES=${USE_POSTGRES:-False}
    restart: unless-stopped

volumes:
  chroma_data:
  media_data:

```
`docs\API_DOCKER_GUIDE.md`:

```md
# 🚀 Backend Docker & Frontend API Integration Reference

This document contains everything needed for **Docker deployment** and **Frontend API integration**.

---

## 1. 🐳 Docker Setup

The repository now contains clean Docker configuration files ready for local testing and Railway deployment.

### Files Created:
1. **`Dockerfile`**: Lightweight Python 3.11 image with system dependencies (`libpq-dev`, `build-essential`).
2. **`docker-compose.yml`**: Mounts persistent volumes for `chroma_data` (vector database) and `media` (uploaded documents).
3. **`railway.json`**: Railway deployment config running migrations and Gunicorn on `$PORT`.
4. **`.dockerignore`**: Prevents unnecessary host files (`db.sqlite3`, `chroma_data`, `.env`) from bloating the docker image.

### How to Run Locally with Docker Compose:
```bash
docker-compose up --build
```
The server will run on `http://localhost:8000`.

---

## 2. 🔑 Essential Environment Variables for Railway / Docker

Ensure the following environment variables are set in your Railway dashboard or `.env`:

| Variable | Recommended / Default Value | Purpose |
| :--- | :--- | :--- |
| `SECRET_KEY` | *(Generate a secure random string)* | Django security key |
| `DEBUG` | `False` | Production flag |
| `ALLOWED_HOSTS` | `*` or your Railway domain | Allowed host headers |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,https://your-frontend.vercel.app` | **Crucial for Frontend requests** |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | LLM token for chat & RAG |
| `USE_POSTGRES` | `True` | Set to `True` if using PostgreSQL |
| `PG_HOST` / `PG_NAME` / etc. | Railway Postgres credentials | Postgres DB configuration |

---

## 3. 📡 API Endpoints Cheat-Sheet for Frontend Developers

All endpoints require standard JSON request bodies. Endpoints marked with 🔒 require the header:
`Authorization: Bearer <access_token>`

### 👤 Authentication (`/api/accounts/`)
- **Register**: `POST /api/accounts/register/`
  ```json
  { "email": "user@example.com", "password": "securepassword123" }
  ```
- **Login**: `POST /api/accounts/login/`
  ```json
  { "email": "user@example.com", "password": "securepassword123" }
  // Returns: { "access": "...", "refresh": "..." }
  ```
- **Refresh Token**: `POST /api/accounts/token/refresh/`
  ```json
  { "refresh": "<refresh_token>" }
  ```
- **Logout** 🔒: `POST /api/accounts/logout/`
  ```json
  { "refresh": "<refresh_token>" }
  ```

### 📚 Knowledge Base Management (`/api/knowledge/`) 🔒
- **List Knowledge Bases**: `GET /api/knowledge/`
- **Create Knowledge Base**: `POST /api/knowledge/`
  ```json
  { "name": "Medical Docs", "description": "Clinical guidelines" }
  ```
- **Upload Document**: `POST /api/knowledge/documents/upload/` (Form-Data)
  - Headers: `Content-Type: multipart/form-data`
  - Body: `knowledge_base_id` (ID), `file` (Binary File: PDF/DOCX/TXT)

### 💬 Chat & RAG (`/api/chat/`) 🔒
- **Create Chat Session**: `POST /api/chat/sessions/`
  ```json
  { "title": "General Q&A", "knowledge_base": <knowledge_base_id> }
  ```
- **List Sessions**: `GET /api/chat/sessions/`
- **Send Message (RAG Query)**: `POST /api/chat/messages/`
  ```json
  {
    "session": <session_id>,
    "content": "What is the recommended treatment for hypertension?"
  }
  ```
  *Response includes AI response and cited document chunks.*

```
`docs\API_Integration_guide.md`:

```md
# RAG Chat API — Integration Guide

**Base URL:** `https://ragchat-production-95c4.up.railway.app/api`
**Interactive docs (Swagger, click-and-test):** `https://ragchat-production-95c4.up.railway.app/api/docs/`
**ReDoc (read-only, cleaner for browsing):** `https://ragchat-production-95c4.up.railway.app/api/redoc/`

Everyone on the team should use **Swagger** (`/api/docs/`) to explore and test endpoints — no code, no files, just a browser. Everything below matches exactly what's in Swagger.

---

## 1. Authentication (JWT)

- `access` token → expires in 60 min. Send with every request that needs login.
- `refresh` token → expires in 7 days. Use it to get a new `access` without logging in again.

**Every protected endpoint needs this header:**
```
Authorization: Bearer <access_token>
```

### Flow
1. `POST /accounts/register/` or `POST /accounts/login/` → get `{ tokens: { access, refresh } }`
2. Save both tokens
3. Send `Authorization: Bearer <access>` on every request after that
4. Got a `401`? Call `POST /auth/token/refresh/` with `refresh` to get a new `access`
5. Logging out? `POST /accounts/logout/` with `{ refresh }`, then delete both tokens locally

### Testing in Swagger (no code needed)
1. Open `/api/docs/`
2. Expand `POST /accounts/register/` → "Try it out" → fill in email/password → Execute
3. Copy the `access` value from the response
4. Click the green **Authorize** button (top right) → type `Bearer ` + paste the token (the word "Bearer", a space, then the token) → Authorize → Close
5. Every "Try it out" call below now sends that header automatically. Token dies after 60 min — just redo steps 2-4 with `/accounts/login/`.

---

## 2. Endpoints

### Auth — `/accounts/`
| Method | Path | Auth | Body |
|---|---|---|---|
| POST | `/accounts/register/` | No | `{ email, password, full_name? }` |
| POST | `/accounts/login/` | No | `{ email, password }` |
| POST | `/accounts/forgot-password/` | No | `{ email }` |
| POST | `/accounts/change-password/` | Yes | `{ old_password, new_password }` |
| GET | `/accounts/profile/` | Yes | — |
| PATCH | `/accounts/profile/` | Yes | `{ full_name }` |
| DELETE | `/accounts/profile/` | Yes | — (deletes account, irreversible) |
| POST | `/accounts/logout/` | Yes | `{ refresh }` |
| GET | `/accounts/dashboard-summary/` | Yes | Counts — see below |

**Dashboard summary response:**
```json
{
  "total_knowledge_bases": 3,
  "total_documents": 12,
  "total_chat_sessions": 8,
  "total_messages": 47
}
```
Use this for any dashboard/home screen. Numbers are scoped to whoever's logged in — no cross-user data.

### Token refresh
| Method | Path | Auth | Body |
|---|---|---|---|
| POST | `/auth/token/refresh/` | No | `{ refresh }` → `{ access }` |

### Knowledge Bases — `/knowledge/`
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/knowledge/bases/` | Yes | List your knowledge bases |
| POST | `/knowledge/bases/` | Yes | `{ name, description? }` |
| GET/PATCH/DELETE | `/knowledge/bases/{id}/` | Yes | |
| GET | `/knowledge/bases/{kb_id}/documents/` | Yes | List documents in a KB |
| POST | `/knowledge/bases/{kb_id}/documents/` | Yes | multipart upload, see below |
| GET/PATCH/DELETE | `/knowledge/bases/{kb_id}/documents/{doc_id}/` | Yes | |

**Uploading a document** — `source_type` is `PDF`, `DOCX`, `TXT`, or `WEBSITE`.
- PDF/DOCX/TXT: send `file` (multipart), max 50MB, extension must match `source_type`
- WEBSITE: send `source_url` instead, no file

```
POST /knowledge/bases/{kb_id}/documents/
Content-Type: multipart/form-data
title: "My PDF"
source_type: "PDF"
file: <binary>
```

**How to know it actually worked (no file access needed):**
```
GET /knowledge/bases/{kb_id}/documents/{doc_id}/
```
Check `status` (should say something like "ready"/"processed") and `chunk_count` (should be > 0). If `chunk_count` is 0 or `status` shows failed, ingestion broke on that document.

### Chat — `/chat/`
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/chat/sessions/` | Yes | List your chat sessions |
| POST | `/chat/sessions/` | Yes | `{ title?, knowledge_base? }` — set `knowledge_base` to link RAG context |
| GET | `/chat/sessions/{id}/` | Yes | Session + full message history |
| DELETE | `/chat/sessions/{id}/` | Yes | |
| GET | `/chat/sessions/{id}/messages/` | Yes | List messages |
| POST | `/chat/sessions/{id}/messages/` | Yes | `{ content }` → returns user + AI reply together |

**Message response:**
```json
{
  "user_message": { "id": "...", "role": "user", "content": "...", "created_at": "..." },
  "assistant_message": { "id": "...", "role": "assistant", "content": "...", "created_at": "..." }
}
```
This is a blocking call — waits for the full AI reply (calls OpenRouter), takes a few seconds. No streaming yet. Show a loading indicator.

---

## 3. Where data actually lives (so nobody's confused)

Two separate stores, both already wired up:
- **Postgres (Neon)** — everything structured: users, knowledge base names, document metadata, chat sessions, messages. Normal rows and columns.
- **ChromaDB** — only the text chunks + embeddings from uploaded documents, used to power RAG search. Nothing here is human-readable through the API directly — you confirm it worked through `chunk_count` on the document (see above), or by asking the chatbot something about the uploaded content and getting a relevant answer back.

You never need to touch either database directly — the API is the only interface. `chunk_count > 0` on a document + a relevant chatbot answer = proof both stores are working.

---

## 4. CORS

Only origins in the backend's `CORS_ALLOWED_ORIGINS` list can call this API from a browser. Currently allowed:
```
http://localhost:3000
http://localhost:5173
https://rag-chat-frontend-ten.vercel.app
```
Running locally on a different port, or deploying to a new domain? That URL needs to be added to this list on the backend (Railway env var) before your browser calls will work — otherwise you'll see a CORS error even though the API itself is fine.

---

## 5. Status codes you'll actually see

- `200` / `201` — success
- `400` — validation error (check the response body for which field)
- `401` — missing/expired token → refresh or re-login
- `404` — doesn't exist, or belongs to someone else (all data is user-scoped)
- `429` — rate limited (20/min unauthenticated, 200/min authenticated)

---

## 6. Full example (JS fetch)

```js
const BASE = "https://ragchat-production-95c4.up.railway.app/api";

// Login
const loginRes = await fetch(`${BASE}/accounts/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
const { tokens } = await loginRes.json();

// Create a chat session
const sessionRes = await fetch(`${BASE}/chat/sessions/`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${tokens.access}`,
  },
  body: JSON.stringify({ title: "New chat" }),
});
const session = await sessionRes.json();

// Send a message
const msgRes = await fetch(`${BASE}/chat/sessions/${session.id}/messages/`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${tokens.access}`,
  },
  body: JSON.stringify({ content: "What's in my knowledge base?" }),
});
const { assistant_message } = await msgRes.json();
console.log(assistant_message.content);
```
```
`docs\API_TESTING.md`:

```md
# API Testing Guide — Swagger (drf-yasg) & Postman

Separate guide for documenting and testing KnowledgeNest APIs.
Build endpoints first (see [GUIDE.md](../GUIDE.md)); wire Swagger when you want interactive docs; use Postman for repeatable tests.

---

## What you will use

| Tool | Role |
|------|------|
| **drf-yasg** | Auto-generates OpenAPI / Swagger UI from your DRF views |
| **Swagger UI** | Try endpoints in the browser |
| **Postman** | Collections, environments, JWT reuse, file uploads, sharing tests |

You do **not** need both for every request — Swagger for quick explore, Postman for a full learning checklist.

---

## Part A — Swagger with drf-yasg

### A1. Why Swagger here?

- See all routes in one place
- Send JWT from the UI
- Share a live contract with frontend classmates
- Catch missing serializers / unclear request bodies early

### A2. Install (when ready)

```bash
pip install drf-yasg
```

Add to `requirements.txt` when you adopt it:

```text
drf-yasg>=1.21
```

Add `"drf_yasg"` to `INSTALLED_APPS` in `config/settings.py`.

### A3. What to configure (learning checklist)

Do these in order — look up current `drf-yasg` docs for exact imports if versions differ:

1. [ ] Install package + add to `INSTALLED_APPS`
2. [ ] Create a Swagger `schema_view` in `config/urls.py` (or a small `config/swagger.py`)
3. [ ] Mount UI routes, typically:
   - `/swagger/` — Swagger UI
   - `/redoc/` — ReDoc (optional)
   - `/swagger.json` or schema endpoint — raw OpenAPI
4. [ ] Ensure JWT works in Swagger: authorize with `Bearer <access_token>`
5. [ ] Restart `runserver` and open the UI

Suggested URLs after setup:

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/swagger/ | Interactive API docs |
| http://127.0.0.1:8000/redoc/ | Readable reference |
| http://127.0.0.1:8000/admin/ | Data inspection |

### A4. JWT inside Swagger

1. Call `POST /api/auth/token/` with email + password (or use Postman once)
2. Copy the `access` token
3. In Swagger UI → **Authorize**
4. Enter: `Bearer <paste_access_token>`
5. Call protected routes (`/api/accounts/me/`, knowledge, chat)

If Authorize is missing, configure drf-yasg security definitions for `Bearer` / JWT (HTTP bearer or apiKey in header `Authorization`).

### A5. Make docs clearer (optional improvements)

As you add views:

- Use meaningful serializer classes (Swagger reads fields from them)
- Add short view/`@swagger_auto_schema` descriptions when a body is special (e.g. multipart upload)
- Mark public routes (`AllowAny`) vs JWT routes clearly
- Prefer ViewSets/routers so paths appear consistently

### A6. Swagger learning checklist

- [ ] `/swagger/` loads without errors
- [ ] Signup and token endpoints visible
- [ ] Authorize with Bearer token works
- [ ] `GET /api/accounts/me/` succeeds after Authorize
- [ ] File upload endpoint shows form-data / binary field (when you build Step 4)
- [ ] You can export OpenAPI JSON for Postman import (optional)

---

## Part B — Postman for API testing

### B1. Why Postman?

- Save a **Collection** that matches the [API map](../GUIDE.md#api-map-target)
- Store `base_url` and `access_token` in an **Environment**
- Retest after every feature without retyping URLs
- Easy multipart PDF upload testing

### B2. One-time setup

1. Install [Postman](https://www.postman.com/downloads/)
2. Create environment: `KnowledgeNest Local`
3. Add variables:

| Variable | Initial value | Example |
|----------|---------------|---------|
| `base_url` | `http://127.0.0.1:8000` | server root |
| `access_token` | *(empty)* | filled after login |
| `refresh_token` | *(empty)* | optional |
| `knowledge_base_id` | *(empty)* | filled after create KB |
| `session_id` | *(empty)* | filled after create chat |

4. Create collection: `KnowledgeNest API`
5. On the collection (or each protected request), set header:

```http
Authorization: Bearer {{access_token}}
```

Use **Tests** scripts on the login request to save tokens automatically, for example:

- Parse JSON response
- `pm.environment.set("access_token", json.access)`
- Optionally save `refresh_token`

### B3. Suggested collection folders (match learning steps)

```
KnowledgeNest API/
├── 01 Auth
│   ├── Signup
│   ├── Login (Token)
│   ├── Refresh Token
│   └── Me
├── 02 Knowledge Bases
│   ├── List / Create / Detail / Update / Delete
├── 03 Documents
│   ├── List documents
│   ├── Upload PDF (form-data)
│   ├── Add website URL (JSON)
│   └── Delete document
└── 04 Chat
    ├── Create session
    ├── List messages
    └── Ask question
```

Build folders as you complete GUIDE steps — empty folders are fine early on.

### B4. Request recipes (what to send)

#### Signup — `POST {{base_url}}/api/accounts/signup/`

- Auth: none
- Body (JSON): `email`, `password`, optional `full_name`

#### Login — `POST {{base_url}}/api/auth/token/`

- Auth: none
- Body (JSON): `email`, `password`  
  (field name is **email**, not username)
- Tests tab: save `access` → `access_token`

#### Me — `GET {{base_url}}/api/accounts/me/`

- Header: `Authorization: Bearer {{access_token}}`

#### Create knowledge base — `POST {{base_url}}/api/knowledge/bases/`

- JWT required
- Body (JSON): `name`, optional `description`
- Tests: save returned `id` → `knowledge_base_id`

#### Upload PDF — `POST {{base_url}}/api/knowledge/bases/{{knowledge_base_id}}/documents/`

- JWT required
- Body: **form-data** (not raw JSON)
  - `title` (text)
  - `source_type` = `pdf`
  - `file` (File)

#### Add website — same URL, JSON body

- `title`, `source_type` = `website`, `source_url`

#### Chat ask — `POST {{base_url}}/api/chat/sessions/{{session_id}}/messages/`

- JWT required
- Body (JSON): `content` = your question

### B5. Import OpenAPI into Postman (optional)

After Swagger works:

1. Open `/swagger.json` (or your schema URL) in the browser
2. Postman → Import → Link / file
3. You get a generated collection — still add environment variables and Bearer header

### B6. Postman testing checklist

For **each** new endpoint:

- [ ] Happy path (valid JWT + body) → expected status (`200` / `201`)
- [ ] No token → `401`
- [ ] Wrong user’s id → empty list / `403` / `404` (your choice, but consistent)
- [ ] Bad validation → `400` with clear field errors
- [ ] File upload uses form-data
- [ ] Token refresh still works when access expires

### B7. Sharing with teammates

- Export Collection + Environment (JSON)
- Do **not** commit real tokens or `.env` secrets
- Keep `base_url` as localhost for learning

---

## Part C — Recommended testing workflow

```
Implement endpoint (serializer → view → url)
        ↓
Hit it once in Swagger (quick sanity)
        ↓
Save it in Postman collection + env vars
        ↓
Run Auth → feature folder in order
        ↓
Tick GUIDE.md checklist item
```

| Stage of GUIDE | Best tool |
|----------------|-----------|
| Step 2 Auth | Postman (save token) + Swagger Authorize |
| Step 3–4 Knowledge / upload | Postman (form-data shines) |
| Step 5 Chat | Either |
| Step 6–7 RAG | Postman (longer answers); check admin + Chroma side effects |

---

## Common pitfalls

| Mistake | Fix |
|---------|-----|
| Swagger “Authorize” without `Bearer ` prefix | Use `Bearer <token>` |
| Login body still using `username` | Use `email` (custom User) |
| Uploading PDF as JSON | Use form-data in Postman |
| Token in URL query string | Use `Authorization` header only |
| Committing Postman dumps with secrets | Strip tokens before sharing |
| Expecting Swagger before views exist | Empty/minimal schema until you add APIs |

---

## Learning checklist (this guide)

### Swagger
- [ ] `drf-yasg` installed and in `INSTALLED_APPS`
- [ ] `/swagger/` opens
- [ ] JWT Authorize works
- [ ] New endpoints appear after you add them

### Postman
- [ ] Environment with `base_url` + `access_token`
- [ ] Login request auto-saves access token
- [ ] Collection folders match GUIDE steps
- [ ] PDF upload tested with form-data
- [ ] Unauthorized case verified at least once

---

## See also

- [GUIDE.md](../GUIDE.md) — API map & build order
- [README.md](../README.md) — architecture & pipeline
- [VECTOR_DB.md](VECTOR_DB.md) — what to verify after ingest/chat

```
`docs\CODEBASE_REVIEW.md`:

```md
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

```
`docs\VECTOR_DB.md`:

```md
# Vector Database Guide (ChromaDB)

Beginner guide for how KnowledgeNest stores and searches embeddings.
This project uses **ChromaDB only**. Do not use Qdrant, Pinecone, pgvector, or Redis for vectors.

Related reading: [GUIDE.md](../GUIDE.md) Steps 6–7 · [schema.mmd](schema.mmd) · [README.md](../README.md)

---

## Why a vector database?

Normal SQL is great for exact lookups (`email = …`, `owner_id = …`).

RAG needs a different question:

> “Which text chunks are **most similar in meaning** to this user question?”

That needs:

1. Turn text into a list of numbers (**embedding** / vector)
2. Store those vectors
3. Search by **nearest neighbors** (similarity)

ChromaDB is that store. SQLite/PostgreSQL stays the metadata store.

---

## Split of responsibility

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  SQLite / PostgreSQL        │     │  ChromaDB                    │
│  (Django models)            │     │  (vector store)              │
├─────────────────────────────┤     ├──────────────────────────────┤
│  User                       │     │  Embedding vectors           │
│  KnowledgeBase              │────▶│  Chunk text                  │
│    · chroma_collection_id   │     │  Metadata:                   │
│  Document (file, url,       │     │    document_id               │
│    status, chunk_count)     │     │    knowledge_base_id         │
│  ChatSession / ChatMessage  │     │    chunk_index               │
└─────────────────────────────┘     └──────────────────────────────┘
```

| Store | What belongs here | What does **not** |
|-------|-------------------|-------------------|
| SQL | Users, KB names, file paths, status, chat history, `chroma_collection_id` string | Float arrays / embeddings |
| ChromaDB | Vectors, chunk text, small metadata for filtering | Passwords, JWT tokens, full user tables |

**Hard rule:** never add an `embedding` JSON/array column to Django models.

---

## Core ideas (plain language)

### Embedding
A model (Sentence Transformers) turns a sentence into a fixed-length list of floats, e.g. 384 numbers. Similar meanings → similar vectors.

### Chunk
Long documents are split into smaller pieces (chunks) before embedding. Each chunk becomes one vector in Chroma.

### Collection
In Chroma, a **collection** is like a named bucket of vectors.  
In this app: **one KnowledgeBase → one Chroma collection**, named by `KnowledgeBase.chroma_collection_id`.

### Similarity search (query)
Embed the user’s question → ask Chroma for the top‑k closest chunks in that collection → send those chunks to OpenRouter as context.

---

## How it maps to this project

| Django field / model | Role with Chroma |
|----------------------|------------------|
| `KnowledgeBase.chroma_collection_id` | Collection name (string only) |
| `KnowledgeBase.id` | Stored in chunk metadata as `knowledge_base_id` |
| `Document.id` | Stored in chunk metadata as `document_id` |
| `Document.chunk_count` | How many vectors were written (SQL counter) |
| `Document.status` | `pending` → `processing` → `ready` / `failed` |

When you delete a Document or KnowledgeBase in SQL, also delete matching Chroma data (by metadata filter or by dropping the collection). Keep the two stores in sync manually in your service code.

---

## Data stored per chunk in Chroma

Each item in a collection should look conceptually like:

| Piece | Example purpose |
|-------|-----------------|
| **id** | Unique chunk id (string), e.g. `{document_id}_{chunk_index}` |
| **embedding** | Vector from Sentence Transformers |
| **document** (text) | The chunk string used later in the LLM prompt |
| **metadata** | `knowledge_base_id`, `document_id`, `chunk_index`, maybe `source_type` |

Metadata must be simple types Chroma accepts (strings, numbers, bools) — not nested objects.

---

## End-to-end flows

### A) Ingest (after upload / website add)

```
Document created (status=pending)
        ↓
Extract plain text (pdf / docx / txt / html)
        ↓
Split into chunks (size + overlap you choose)
        ↓
Embed each chunk (same model every time)
        ↓
Upsert into collection = knowledge_base.chroma_collection_id
        ↓
Update Document: status=ready, chunk_count=N
```

Do this **synchronously** first (inside the upload view or a small service). No Celery required for learning.

### B) Retrieve + answer (chat)

```
User question
        ↓
Embed question (same embedding model as ingest)
        ↓
Query that KB’s Chroma collection (top_k = 3–8)
        ↓
Build prompt: system rules + retrieved chunk text + question
        ↓
OpenRouter completion
        ↓
Save ChatMessage (user + assistant) in SQL only
```

Chat history stays in SQL. Retrieved chunk vectors stay in Chroma.

---

## Settings already reserved for you

In `config/settings.py` (wired later in code):

| Setting | Meaning |
|---------|---------|
| `CHROMA_PERSIST_DIR` | Folder on disk where Chroma persists data (default `chroma_data/`) |
| `EMBEDDING_MODEL_NAME` | Sentence Transformers model id |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | LLM for answers (not for embeddings) |

Local persistence means: restarting the server keeps vectors if `CHROMA_PERSIST_DIR` is unchanged. Add `chroma_data/` to `.gitignore` (already done).

---

## Choosing chunk size (practical defaults)

| Setting | Beginner starting point | Why |
|---------|-------------------------|-----|
| Chunk size | ~500–1000 characters | Fits context; enough meaning per chunk |
| Overlap | ~50–150 characters | Avoids cutting sentences awkwardly |
| top_k | 3–5 (then try 8) | More isn’t always better; can add noise |

Tune after you see real answers. Keep the **same** embedding model for ingest and query.

---

## Isolation between users

Never query “all collections at once” for a chat answer.

Always:

1. Load the `ChatSession` → its `knowledge_base`
2. Confirm `knowledge_base.owner == request.user`
3. Open **only** `knowledge_base.chroma_collection_id`
4. Search inside that collection

That way User A’s vectors cannot leak into User B’s answers.

---

## Lifecycle checklist

### On KnowledgeBase create
- [ ] Generate unique `chroma_collection_id` (e.g. `kb_<uuid>`)
- [ ] Optionally create the empty Chroma collection immediately

### On Document create / reprocess
- [ ] Set `status=processing`
- [ ] Extract → chunk → embed → upsert
- [ ] Set `chunk_count` and `status=ready` (or `failed` + `error_message`)

### On Document delete
- [ ] Delete Chroma items where `document_id` matches
- [ ] Delete the SQL `Document` row

### On KnowledgeBase delete
- [ ] Delete the whole Chroma collection
- [ ] Cascade SQL docs/sessions (Django `CASCADE` already helps SQL side)

---

## What you install when you reach this step

Add to your environment only when starting GUIDE Step 6 (not required for auth CRUD):

- `chromadb` — vector store client + local persistence
- `sentence-transformers` — embedding model
- extractors: `pypdf`, `python-docx`, `beautifulsoup4`, `requests`
- `openai` — OpenRouter-compatible client (Step 7)

Keep them commented in `requirements.txt` until you need them, or uncomment then `pip install -r requirements.txt`.

---

## Learning checklist (vector layer)

- [ ] Can explain why SQL cannot replace Chroma for meaning search
- [ ] One KB ↔ one Chroma collection via `chroma_collection_id`
- [ ] Chunks stored with `document_id` + `knowledge_base_id` metadata
- [ ] Same embedding model used for ingest and query
- [ ] Document `status` / `chunk_count` updated in SQL only
- [ ] Chat queries only the session’s KB collection
- [ ] Deleting a doc/KB also cleans Chroma
- [ ] Confirmed: no embedding columns in Django models

---

## Common pitfalls

| Pitfall | Fix |
|---------|-----|
| Saving vectors in PostgreSQL/SQLite | Use Chroma only |
| Different embedding models for ingest vs query | One model name everywhere |
| Searching the wrong collection | Always use that KB’s `chroma_collection_id` |
| Huge chunks or whole PDFs as one vector | Chunk with overlap |
| Ignoring failed ingest | Set `status=failed` and store `error_message` |
| Adding Celery “because vectors” | Sync is enough until it is slow |
| Switching to Qdrant/Pinecone early | Out of scope for this project |

---

## How this fits the main GUIDE

| GUIDE step | Vector work |
|------------|-------------|
| Steps 0–5 | No Chroma yet — API + SQL only |
| **Step 6** | Ingest pipeline → write Chroma |
| **Step 7** | Query Chroma → prompt → OpenRouter |

Build auth and knowledge CRUD first. Come back here when documents upload successfully and you are ready to fill embeddings.

---

## Mental model to remember

> **SQL remembers what the user owns.  
> Chroma remembers what the text means.  
> OpenRouter answers using the text Chroma finds.**

```
`docs\schema.mmd`:

```mmd
%%{init: {"theme": "neutral"}}%%
%% KnowledgeNest AI — Database schema (metadata only)
%% Embeddings live in ChromaDB, not in these tables.
%% Auth: accounts.User (email + password). No Profile table.

erDiagram
    User ||--o{ KnowledgeBase : owns
    User ||--o{ ChatSession : starts
    KnowledgeBase ||--o{ Document : contains
    KnowledgeBase ||--o{ ChatSession : powers
    ChatSession ||--o{ ChatMessage : includes

    User {
        int id PK
        string email UK
        string password
        string full_name
        bool is_active
        bool is_staff
        datetime date_joined
        datetime last_login
    }

    KnowledgeBase {
        uuid id PK
        int owner_id FK
        string name
        text description
        string chroma_collection_id UK
        datetime created_at
        datetime updated_at
    }

    Document {
        uuid id PK
        uuid knowledge_base_id FK
        string title
        string source_type
        string file
        string source_url
        string status
        text error_message
        int chunk_count
        datetime created_at
        datetime updated_at
    }

    ChatSession {
        uuid id PK
        int user_id FK
        uuid knowledge_base_id FK
        string title
        datetime created_at
        datetime updated_at
    }

    ChatMessage {
        uuid id PK
        uuid session_id FK
        string role
        text content
        datetime created_at
    }

```
`knowledge\admin.py`:

```py
from django.contrib import admin

from .models import Document, KnowledgeBase


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "chroma_collection_id", "created_at")
    search_fields = ("name", "owner__email")
    list_filter = ("created_at",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "knowledge_base", "source_type", "status", "chunk_count", "created_at")
    list_filter = ("source_type", "status", "created_at")
    search_fields = ("title", "source_url")
    list_select_related = ("knowledge_base",)  # prevents N+1 in admin list

```
`knowledge\apps.py`:

```py
from django.apps import AppConfig


class KnowledgeConfig(AppConfig):
    name = 'knowledge'

```
`knowledge\migrations\0001_initial.py`:

```py
# Generated by Django 6.0.7 on 2026-07-25 16:55

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeBase',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('chroma_collection_id', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_bases', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('source_type', models.CharField(choices=[('pdf', 'PDF'), ('docx', 'DOCX'), ('txt', 'TXT'), ('website', 'Website')], max_length=20)),
                ('file', models.FileField(blank=True, null=True, upload_to='documents/%Y/%m/%d/')),
                ('source_url', models.URLField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('ready', 'Ready'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True)),
                ('chunk_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('knowledge_base', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='knowledge.knowledgebase')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]

```
`knowledge\migrations\0002_document_document_status_idx.py`:

```py
# Generated by Django 6.0.7 on 2026-07-27 08:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['status'], name='document_status_idx'),
        ),
    ]

```
`knowledge\models.py`:

```py
import uuid

from django.conf import settings
from django.db import models


class KnowledgeBase(models.Model):
    """
    A user-owned knowledge collection.

    Embeddings live in ChromaDB (see chroma_collection_id).
    This table stores metadata only — never vectors.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="knowledge_bases",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # ChromaDB collection name/id — not an embedding vector
    chroma_collection_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    A single source inside a knowledge base (file or website).

    Extracted text chunks + embeddings are stored in ChromaDB.
    PostgreSQL/SQLite only keeps file/url metadata and processing status.
    """

    class SourceType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"
        TXT = "txt", "TXT"
        WEBSITE = "website", "Website"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    file = models.FileField(upload_to="documents/%Y/%m/%d/", blank=True, null=True)
    source_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    # How many chunks were written to ChromaDB (metadata only)
    chunk_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="document_status_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.source_type})"

```
`knowledge\script_chroma.py`:

```py
import os
import sys
import django

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()

from knowledge.services.chroma import get_collection


collection = get_collection("test_collection")

print(collection.name)
```
`knowledge\script_chroma_add.py`:

```py
import os
import sys
import django

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()


from knowledge.services.chroma import add_chunks


chunks = [
    "Allah is a du'a away",
    "Protection is a du'a away",
]

# Fake embeddings for testing
# (real ones will come from embedder.py)
embeddings = [
    [0.1, 0.2, 0.3],
    [0.4, 0.5, 0.6],
]


count = add_chunks(
    collection_name="test_collection",
    chunks=chunks,
    embeddings=embeddings,
    document_id="123",
    knowledge_base_id="abc",
)

print("Added chunks:", count)
```
`knowledge\script_chroma_query.py`:

```py
import os
import sys
import django

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()


from knowledge.services.chroma import get_collection


collection = get_collection("test_collection")


results = collection.query(
    query_embeddings=[
        [0.1, 0.2, 0.3]
    ],
    n_results=2
)


print(results)
```
`knowledge\script_chunker.py`:

```py
import os
import sys

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from knowledge.services.chunker import chunk_text


text = """
This is a very long document.
It contains many words.
We want to split it into smaller pieces.
"""


chunks = chunk_text(text, chunk_size=5)

for chunk in chunks:
    print("----")
    print(chunk)
```
`knowledge\script_embedder.py`:

```py
import os
import sys
import django


sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()


from knowledge.services.embedder import create_embeddings


chunks = [
    "Allah is a du'a away",
    "Protection is a du'a away"
]


vectors = create_embeddings(chunks)


print(len(vectors))
print(len(vectors[0]))
```
`knowledge\script_extractor.py`:

```py
import os
import sys
import django

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()

from knowledge.models import Document
from knowledge.services.extractor import extract_document


document = Document.objects.first()

text = extract_document(document)

print(text[:500])
```
`knowledge\script_ingest.py`:

```py
import os
import sys
import django

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()


from knowledge.models import Document
from knowledge.services.ingest import ingest_document


document = Document.objects.first()

print("Before:", document.status)

ingest_document(document)

document.refresh_from_db()

print("After:", document.status)
print("Chunks:", document.chunk_count)
```
`knowledge\serializers.py`:

```py

from rest_framework import serializers

from .models import KnowledgeBase, Document


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBase
        fields = (
            "id",
            "owner",
            "name",
            "description",
            "chroma_collection_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "owner",
            "chroma_collection_id",
            "created_at",
            "updated_at",
        )


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
            "id",
            "knowledge_base",
            "title",
            "source_type",
            "file",
            "source_url",
            "status",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "knowledge_base",
            "error_message",
            "chunk_count",
            "created_at",
            "updated_at",
        )

    def validate_file(self, value):
        if value is None:
            return value

        ALLOWED_SOURCE_EXTENSIONS = {
            Document.SourceType.PDF: {"pdf"},
            Document.SourceType.DOCX: {"docx"},
            Document.SourceType.TXT: {"txt"},
            Document.SourceType.WEBSITE: set(),
        }
        MAX_UPLOAD_MB = 50

        source_type = self.initial_data.get("source_type", "")
        allowed = ALLOWED_SOURCE_EXTENSIONS.get(source_type, set())

        if allowed:
            ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
            if ext not in allowed:
                raise serializers.ValidationError(
                    f"File extension '.{ext}' is not allowed for source type '{source_type}'. "
                    f"Allowed extensions: {', '.join(allowed)}"
                )

        if value.size > MAX_UPLOAD_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"File size ({value.size // (1024 * 1024)} MB) exceeds the maximum allowed limit of {MAX_UPLOAD_MB} MB."
            )

        return value

    def validate(self, attrs):
        """
        Validation rules:
        - PDF/DOCX/TXT require a file.
        - WEBSITE requires a URL.
        """

        source_type = attrs.get("source_type")

        file = attrs.get("file")
        source_url = attrs.get("source_url")

        if source_type == Document.SourceType.WEBSITE:
            if not source_url:
                raise serializers.ValidationError(
                    {"source_url": "A website URL is required for WEBSITE source type."}
                )
        else:
            if not file:
                raise serializers.ValidationError(
                    {"file": f"A file is required for source type '{source_type}'."}
                )

        return attrs
```
`knowledge\services\chroma.py`:

```py
import chromadb
from django.conf import settings


# Connect to local ChromaDB storage
client = chromadb.PersistentClient(
    path=str(settings.CHROMA_PERSIST_DIR)
)


def get_collection(collection_name):
    """
    Get an existing Chroma collection
    or create it if it does not exist.
    """

    return client.get_or_create_collection(
        name=collection_name
    )


def add_chunks(
    collection_name,
    chunks,
    embeddings,
    document_id,
    knowledge_base_id,
):
    """
    Store document chunks and their embeddings in ChromaDB.

    SQL stores:
        - document metadata
        - knowledge base info

    Chroma stores:
        - chunk text
        - embeddings
        - metadata
    """

    collection = get_collection(collection_name)

    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]

    metadatas = [
        {
            "document_id": str(document_id),
            "knowledge_base_id": str(knowledge_base_id),
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )

    return len(chunks)
```
`knowledge\services\chunker.py`:

```py
def chunk_text(text, chunk_size=500):
    """
    Split text into smaller chunks.
    """

    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(
            words[i:i + chunk_size]
        )

        chunks.append(chunk)

    return chunks
```
`knowledge\services\embedder.py`:

```py
from django.conf import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def create_embeddings(chunks):
    """
    Convert text chunks into vectors.
    """
    model = _get_model()
    embeddings = model.encode(chunks)
    return embeddings.tolist()

```
`knowledge\services\extractor.py`:

```py
from pypdf import PdfReader
import requests
from bs4 import BeautifulSoup


def extract_pdf(file_path):
    """
    Extract text from PDF file.
    """

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text



def extract_website(url):
    """
    Extract text from website URL.
    """

    response = requests.get(url)

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    return soup.get_text(
        separator="\n"
    )



def extract_document(document):
    """
    Decide extraction method based on document type.
    """

    if document.source_type == "pdf":
        return extract_pdf(
            document.file.path
        )

    elif document.source_type == "website":
        return extract_website(
            document.source_url
        )

    else:
        raise ValueError(
            "Unsupported document type"
        )
```
`knowledge\services\ingest.py`:

```py
from knowledge.services.extractor import extract_document
from knowledge.services.chunker import chunk_text
from knowledge.services.embedder import create_embeddings
from knowledge.services.chroma import add_chunks

from knowledge.models import Document


def ingest_document(document):
    try:
        # Mark as processing
        document.status = Document.Status.PROCESSING
        document.save()

        # 1. Extract text
        text = extract_document(document)

        if not text.strip():
            raise ValueError("No text extracted from document")

        # 2. Split text
        chunks = chunk_text(text)

        # 3. Create embeddings
        embeddings = create_embeddings(chunks)

        # 4. Store in Chroma
        count = add_chunks(
            collection_name=document.knowledge_base.chroma_collection_id,
            chunks=chunks,
            embeddings=embeddings,
            document_id=document.id,
            knowledge_base_id=document.knowledge_base.id,
        )

        # 5. Update document
        document.status = Document.Status.READY
        document.chunk_count = count
        document.save()

        return document

    except Exception as e:
        document.status = Document.Status.FAILED
        document.error_message = str(e)
        document.save()

        raise e
    
```
`knowledge\tests.py`:

```py
"""
knowledge/tests.py

Tests for the Knowledge Base and Document API endpoints.

Coverage:
  - KnowledgeBase: create, list, retrieve, update, delete (ownership enforced)
  - Document: create with validation, ownership enforcement
  - Unauthenticated access → 401
  - Other user's resource → 404
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from knowledge.models import Document, KnowledgeBase

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email, password="StrongPass123!"):
    return User.objects.create_user(email=email, password=password)


def make_kb(owner, name="Test KB", description="Test knowledge base"):
    return KnowledgeBase.objects.create(
        owner=owner,
        name=name,
        description=description,
        chroma_collection_id=f"kb_test_{name.replace(' ', '_').lower()}_{owner.pk}",
    )


# ---------------------------------------------------------------------------
# KnowledgeBase CRUD
# ---------------------------------------------------------------------------

class KnowledgeBaseCreateTests(APITestCase):
    """POST /api/knowledge/bases/"""

    def setUp(self):
        self.user = make_user("alice@example.com")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/knowledge/bases/"

    def test_create_kb_success(self):
        """Valid data creates a knowledge base and returns 201."""
        response = self.client.post(self.url, {
            "name": "Research Papers",
            "description": "ML papers collection",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Research Papers")
        # chroma_collection_id is auto-generated by the server
        self.assertTrue(response.data["chroma_collection_id"].startswith("kb_"))

    def test_create_kb_sets_owner_from_jwt(self):
        """Owner is always set from JWT — never from request body."""
        response = self.client.post(self.url, {"name": "My KB"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        kb = KnowledgeBase.objects.get(id=response.data["id"])
        self.assertEqual(kb.owner, self.user)

    def test_create_kb_unauthenticated(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {"name": "Nope"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class KnowledgeBaseListTests(APITestCase):
    """GET /api/knowledge/bases/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        make_kb(self.alice, "Alice KB")
        make_kb(self.bob, "Bob KB")
        self.client.force_authenticate(user=self.alice)

    def test_list_returns_only_own_kbs(self):
        """User only sees their own knowledge bases."""
        response = self.client.get("/api/knowledge/bases/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [kb["name"] for kb in response.data["results"]]
        self.assertIn("Alice KB", names)
        self.assertNotIn("Bob KB", names)


class KnowledgeBaseRetrieveTests(APITestCase):
    """GET /api/knowledge/bases/{id}/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        self.alice_kb = make_kb(self.alice, "Alice KB")
        self.bob_kb = make_kb(self.bob, "Bob KB")

    def test_retrieve_own_kb(self):
        """Owner can retrieve their knowledge base."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"/api/knowledge/bases/{self.alice_kb.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Alice KB")

    def test_retrieve_other_users_kb_returns_404(self):
        """Accessing another user's KB returns 404 — not 403."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"/api/knowledge/bases/{self.bob_kb.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class KnowledgeBaseUpdateTests(APITestCase):
    """PATCH /api/knowledge/bases/{id}/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.kb = make_kb(self.alice, "Original Name")
        self.client.force_authenticate(user=self.alice)

    def test_update_kb_name(self):
        """PATCH updates the name successfully."""
        response = self.client.patch(
            f"/api/knowledge/bases/{self.kb.id}/",
            {"name": "Updated Name"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Name")

    def test_cannot_update_other_users_kb(self):
        """Cannot PATCH another user's KB."""
        bob = make_user("bob@example.com")
        bob_kb = make_kb(bob, "Bob KB")
        response = self.client.patch(
            f"/api/knowledge/bases/{bob_kb.id}/",
            {"name": "Hacked"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class KnowledgeBaseDeleteTests(APITestCase):
    """DELETE /api/knowledge/bases/{id}/"""

    def setUp(self):
        self.alice = make_user("alice@example.com")
        self.bob = make_user("bob@example.com")
        self.alice_kb = make_kb(self.alice, "Alice KB")
        self.bob_kb = make_kb(self.bob, "Bob KB")

    def test_delete_own_kb(self):
        """Owner can delete their KB."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.delete(f"/api/knowledge/bases/{self.alice_kb.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(KnowledgeBase.objects.filter(id=self.alice_kb.id).exists())

    def test_delete_other_users_kb_returns_404(self):
        """Cannot delete another user's KB."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.delete(f"/api/knowledge/bases/{self.bob_kb.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Document validation
# ---------------------------------------------------------------------------

class DocumentValidationTests(APITestCase):
    """POST /api/knowledge/bases/{kb_id}/documents/"""

    def setUp(self):
        self.user = make_user("alice@example.com")
        self.kb = make_kb(self.user, "Test KB")
        self.client.force_authenticate(user=self.user)
        self.url = f"/api/knowledge/bases/{self.kb.id}/documents/"

    def test_website_requires_url(self):
        """Website source_type requires source_url."""
        response = self.client.post(self.url, {
            "title": "Web Page",
            "source_type": "website",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pdf_requires_file(self):
        """PDF source_type requires a file upload."""
        response = self.client.post(self.url, {
            "title": "My PDF",
            "source_type": "pdf",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_access_other_users_kb_documents(self):
        """Listing documents under another user's KB returns 404."""
        bob = make_user("bob@example.com")
        bob_kb = make_kb(bob, "Bob KB")
        response = self.client.get(f"/api/knowledge/bases/{bob_kb.id}/documents/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_access(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

```
`knowledge\urls.py`:

```py
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
```
`knowledge\views.py`:

```py
import uuid

from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Document, KnowledgeBase
from .serializers import DocumentSerializer, KnowledgeBaseSerializer
from .services.ingest import ingest_document


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for user Knowledge Bases.

    Users can only access their own knowledge bases.
    """

    serializer_class = KnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only the authenticated user's knowledge bases.
        """
        if getattr(self, "swagger_fake_view", False) or not self.request.user.is_authenticated:
            return KnowledgeBase.objects.none()
        return KnowledgeBase.objects.filter(
            owner=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        """
        Automatically assign the owner and generate a unique
        ChromaDB collection ID when creating a knowledge base.
        """
        serializer.save(
            owner=self.request.user,
            chroma_collection_id=f"kb_{uuid.uuid4().hex}",
        )


class DocumentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, kb_id):
        kb = get_object_or_404(
            KnowledgeBase,
            id=kb_id,
            owner=request.user
        )

        documents = Document.objects.filter(knowledge_base=kb)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request, kb_id):
        kb = get_object_or_404(
            KnowledgeBase,
            id=kb_id,
            owner=request.user
        )

        serializer = DocumentSerializer(data=request.data)

        if serializer.is_valid():
            document = serializer.save(knowledge_base=kb)
            ingest_document(document)
            document.refresh_from_db()

            return Response(
                DocumentSerializer(document).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class DocumentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, kb_id, doc_id):
        return get_object_or_404(
            Document,
            id=doc_id,
            knowledge_base__id=kb_id,
            knowledge_base__owner=request.user,
        )

    def get(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        serializer = DocumentSerializer(document)
        return Response(serializer.data)

    def put(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        serializer = DocumentSerializer(document, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def patch(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        serializer = DocumentSerializer(
            document,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, kb_id, doc_id):
        document = self.get_object(request, kb_id, doc_id)
        document.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )
```
`manage.py`:

```py
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def _ensure_venv_site_packages():
    """
    Cursor / some shells may run a different Python than the project venv.
    Prefer the project .venv site-packages so Django imports reliably.
    """
    base = Path(__file__).resolve().parent
    venv_lib = base / ".venv" / "lib"
    if not venv_lib.exists():
        return
    for site in sorted(venv_lib.glob("python*/site-packages")):
        path = str(site)
        if path not in sys.path:
            sys.path.insert(0, path)
        break


def main():
    """Run administrative tasks."""
    _ensure_venv_site_packages()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?\n"
            "Tip: run  .venv/bin/python manage.py runserver"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

```
`railway.json`:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "sleepApplication": false,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}

```
`requirements.txt`:

```txt
--extra-index-url https://download.pytorch.org/whl/cpu

aiohappyeyeballs==2.7.1
aiohttp==3.14.3
aiosignal==1.4.0
annotated-doc==0.0.4
annotated-types==0.8.0
anyio==4.14.2
asgiref==3.12.1
attrs==26.1.0
bcrypt==5.0.0
beautifulsoup4==4.15.0
build==1.5.0
certifi==2026.7.22
charset-normalizer==3.4.9
chromadb==1.5.9
click==8.4.2
colorama==0.4.6
distro==1.9.0
Django==6.0.7
django-cors-headers==4.9.0
djangorestframework==3.17.1
djangorestframework_simplejwt==5.5.1
drf-yasg==1.21.15
durationpy==0.10
filelock==3.32.0
flatbuffers==25.12.19
frozenlist==1.8.0
fsspec==2026.6.0
googleapis-common-protos==1.75.0
grpcio==1.83.0
gunicorn==23.0.0
whitenoise==6.8.2
h11==0.16.0
hf-xet==1.5.2
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.1
huggingface_hub==1.24.0
idna==3.18
importlib_resources==7.1.0
inflection==0.5.1
Jinja2==3.1.6
jiter==0.16.0
joblib==1.5.3
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
kubernetes==36.0.3
lxml==6.1.1
markdown-it-py==4.2.0
MarkupSafe==3.0.3
mdurl==0.1.2
mmh3==5.2.1
mpmath==1.3.0
multidict==6.7.1
narwhals==2.24.0
networkx==3.6.1
numpy==2.5.1
oauthlib==3.3.1
onnxruntime==1.28.0
openai==2.48.0
opentelemetry-api==1.44.0
opentelemetry-exporter-otlp-proto-common==1.44.0
opentelemetry-exporter-otlp-proto-grpc==1.44.0
opentelemetry-proto==1.44.0
opentelemetry-sdk==1.44.0
opentelemetry-semantic-conventions==0.65b0
orjson==3.11.9
overrides==7.7.0
packaging==26.2
propcache==0.5.2
protobuf==7.35.1
psycopg2-binary==2.9.12
pybase64==1.4.3
pydantic==2.13.4
pydantic-settings==2.14.2
pydantic_core==2.46.4
Pygments==2.20.0
PyJWT==2.13.0
pypdf==6.14.2
PyPika==0.51.1
pyproject_hooks==1.2.0
python-dateutil==2.9.0.post0
python-docx==1.2.0
python-dotenv==1.2.2
pytz==2026.3.post1
PyYAML==6.0.3
referencing==0.37.0
regex==2026.7.19
requests==2.34.2
requests-oauthlib==2.0.0
rich==15.0.0
rpds-py==2026.6.3
safetensors==0.8.0
scikit-learn==1.9.0
scipy==1.18.0
sentence-transformers==5.6.1
setuptools==83.0.0
shellingham==1.5.4
six==1.17.0
sniffio==1.3.1
soupsieve==2.9.1
sqlparse==0.5.5
sympy==1.14.0
tenacity==9.1.4
threadpoolctl==3.6.0
tokenizers==0.22.2
torch==2.13.0+cpu
tqdm==4.69.1
transformers==5.14.1
typer==0.27.0
typing-inspection==0.4.2
typing_extensions==4.16.0
tzdata==2026.3
uritemplate==4.2.0
urllib3==2.7.0
uvicorn==0.51.0
watchfiles==1.2.0
websocket-client==1.9.0
websockets==16.1.1
yarl==1.24.5
```