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
