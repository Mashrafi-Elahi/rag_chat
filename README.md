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
