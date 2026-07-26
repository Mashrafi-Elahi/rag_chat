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
