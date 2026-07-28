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
4. Got a `401`? Call `POST /auth/token/refresh/` with `refresh`, then replace both stored tokens
5. Logging out? `POST /accounts/logout/` with `{ refresh }`, then delete both tokens locally. The refresh token is blacklisted; the access token remains valid until it expires.

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
| POST | `/auth/token/refresh/` | No | `{ refresh }` → `{ access, refresh }` |

### Knowledge Bases — `/knowledge/`
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/knowledge/bases/` | Yes | List your knowledge bases |
| POST | `/knowledge/bases/` | Yes | `{ name, description? }` |
| GET/PATCH/DELETE | `/knowledge/bases/{id}/` | Yes | |
| GET | `/knowledge/bases/{kb_id}/documents/` | Yes | List documents in a KB |
| POST | `/knowledge/bases/{kb_id}/documents/` | Yes | multipart upload, see below |
| GET/PATCH/DELETE | `/knowledge/bases/{kb_id}/documents/{doc_id}/` | Yes | |

**Uploading a document** — `source_type` is `pdf`, `docx`, `txt`, or `website`.
- PDF/DOCX/TXT: send `file` (multipart), max 50MB, extension must match `source_type`
- WEBSITE: send `source_url` instead, no file

```
POST /knowledge/bases/{kb_id}/documents/
Content-Type: multipart/form-data
title: "My PDF"
source_type: "pdf"
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
