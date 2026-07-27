Project Path: rag-chat-app

Source Tree:

```txt
rag-chat-app
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
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── config
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docs
│   ├── API_TESTING.md
│   ├── VECTOR_DB.md
│   └── schema.mmd
├── knowledge
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── models.py
│   ├── serializers.py
│   ├── services
│   │   ├── chroma.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── extractor.py
│   │   └── ingest.py
│   ├── test_chroma.py
│   ├── test_chroma_add.py
│   ├── test_chroma_query.py
│   ├── test_chunker.py
│   ├── test_embedder.py
│   ├── test_extractor.py
│   ├── test_ingest.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── manage.py
└── requirements.txt

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

        return Response(
            {"message": "Logout successful"},
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
import os
import requests
import chromadb
from django.conf import settings
from rest_framework import serializers

from knowledge.models import KnowledgeBase
from .models import ChatMessage, ChatSession

# Cache the model instance globally so it loads only once when first used
_EMBEDDING_MODEL = None

def get_embedding_model():
    """Lazy loader to prevent PyTorch DLL blocks on Django startup/migrations."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBEDDING_MODEL


def generate_rag_response(session, user_query: str) -> str:
    """
    1. Retrieve relevant text chunks from ChromaDB if a KnowledgeBase is linked.
    2. Build prompt with retrieved context.
    3. Call OpenRouter API for the assistant response.
    """
    context_text = ""

    # --- Step 1: ChromaDB Retrieval ---
    if session.knowledge_base and session.knowledge_base.chroma_collection_id:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        try:
            collection = chroma_client.get_collection(
                name=session.knowledge_base.chroma_collection_id
            )
            
            # Fetch lazy-loaded embedding model
            embedding_model = get_embedding_model()
            query_vector = embedding_model.encode(user_query).tolist()
            
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=3,
            )

            if results and results.get("documents"):
                retrieved_docs = results["documents"][0]
                context_text = "\n\n".join(retrieved_docs)
        except Exception:
            context_text = ""

    # --- Step 2: Build Prompt ---
    messages = []
    if context_text:
        system_prompt = (
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the context provided below. If the context does not contain enough "
            "information, state that clearly.\n\n"
            f"Context:\n{context_text}"
        )
    else:
        system_prompt = "You are a helpful AI assistant."

    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_query})

    # --- Step 3: OpenRouter API Call ---
    api_key = getattr(settings, "OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY"))
    if not api_key:
        return "Error: OPENROUTER_API_KEY is missing from environment/settings."

    model_name = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-3.5-turbo")

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": messages,
            },
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"OpenRouter Error ({response.status_code}): {response.text}"

    except Exception as e:
        return f"Failed to reach OpenRouter: {str(e)}"


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class ChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField(read_only=True)
    knowledge_base = serializers.PrimaryKeyRelatedField(
        queryset=KnowledgeBase.objects.all(),
        required=False,
        allow_null=True,
        default=None,  # <-- Crucial fix for optional foreign keys
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

    def validate_knowledge_base(self, value: KnowledgeBase):
        if value is None:
            return value

        request = self.context.get("request")
        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "You do not own this knowledge base."
            )
        return value

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ChatSessionDetailSerializer(ChatSessionSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta):
        fields = ChatSessionSerializer.Meta.fields + ["messages"]


class CreateMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10_000, allow_blank=False)

    def create(self, validated_data):
        session: ChatSession = self.context["session"]
        user_content = validated_data["content"]

        # 1. Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_content,
        )

        # 2. Generate RAG response directly via helper function above
        reply_content = generate_rag_response(session, user_content)

        # 3. Save assistant response
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=reply_content,
        )

        # Update chat session timestamp
        session.save(update_fields=["updated_at"])

        return {
            "user_message": ChatMessageSerializer(user_msg).data,
            "assistant_message": ChatMessageSerializer(assistant_msg).data,
        }
```
`chat\tests.py`:

```py
from django.test import TestCase

# Create your tests here.

```
`chat\urls.py`:

```py
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import ChatMessageListCreateView, ChatSessionViewSet

router = DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    # Login / Token route added inside the chat app
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    # Session & Message routes
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
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
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
    "corsheaders",
    "drf_yasg",
    # Local apps
    "accounts",
    "knowledge",
    "chat",
   
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS — allow local frontend during development
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ---------------------------------------------------------------------------
# AI / RAG settings (used in later steps — not wired yet)
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_data"
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# ---------------------------------------------------------------------------
# Swagger / drf-yasg — JWT Bearer Authorization button
# ---------------------------------------------------------------------------
# Enables the 🔒 Authorize button in Swagger UI (/api/docs/).
# How to use:
#   1. POST /api/accounts/login/  → copy tokens.access
#   2. Click Authorize → enter:  Bearer <access_token>
#   3. All protected endpoints now work in Swagger.
SWAGGER_SETTINGS = {
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
    "USE_SESSION_AUTH": False,       # disable DRF session login in Swagger
    "JSON_EDITOR": True,             # prettier request body editor
    "SUPPORTED_SUBMIT_METHODS": [    # allow all HTTP methods in Try-it-out
        "get", "post", "put", "patch", "delete",
    ],
}

```
`config\urls.py`:

```py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
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

    def __str__(self):
        return f"{self.title} ({self.source_type})"

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
                    {"source_url": "A website URL is required."}
                )

        else:
            if not file:
                raise serializers.ValidationError(
                    {"file": "A file is required for this source type."}
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
from sentence_transformers import SentenceTransformer
from django.conf import settings


model = SentenceTransformer(
    settings.EMBEDDING_MODEL_NAME
)


def create_embeddings(chunks):
    """
    Convert text chunks into vectors.
    """

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
`knowledge\test_chroma.py`:

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
`knowledge\test_chroma_add.py`:

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
`knowledge\test_chroma_query.py`:

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
`knowledge\test_chunker.py`:

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
`knowledge\test_embedder.py`:

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
`knowledge\test_extractor.py`:

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
`knowledge\test_ingest.py`:

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
`knowledge\tests.py`:

```py
from django.test import TestCase

# Create your tests here.

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
`requirements.txt`:

```txt
Django>=5.0,<7.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
python-dotenv>=1.0

# API docs (see docs/API_TESTING.md):
drf-yasg>=1.21

# Install later when you build the RAG pipeline (Step 6+ in GUIDE.md):
# chromadb
# sentence-transformers
# openai          # OpenRouter is OpenAI-compatible
# pypdf           # PDF text extraction
# python-docx     # DOCX text extraction
# beautifulsoup4  # website HTML → text
# requests

```