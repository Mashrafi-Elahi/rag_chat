# RAG Chat API — Frontend Integration Guide

**Base URL:** `https://ragchat-production-95c4.up.railway.app/api`
**Interactive docs (Swagger):** `https://ragchat-production-95c4.up.railway.app/api/docs/`
**ReDoc (read-only, cleaner for browsing):** `https://ragchat-production-95c4.up.railway.app/api/redoc/`
**Raw OpenAPI spec (for codegen):** `https://ragchat-production-95c4.up.railway.app/api/swagger.json`

All endpoints below are prefixed with the base URL above. E.g. `POST /accounts/register/` means `POST https://ragchat-production-95c4.up.railway.app/api/accounts/register/`.

---

## 1. Authentication

This API uses **JWT** (JSON Web Tokens) via `djangorestframework-simplejwt`.

- `access` token → short-lived (60 min). Send with every request to a protected endpoint.
- `refresh` token → long-lived (7 days). Use it to get a new `access` token without re-logging in.

**Every protected endpoint requires this header:**
```
Authorization: Bearer <access_token>
```

### Auth flow
1. `POST /accounts/register/` or `POST /accounts/login/` → get back `{ tokens: { access, refresh } }`
2. Store both tokens (e.g. `localStorage`, or memory + httpOnly cookie if you want it more secure)
3. Attach `Authorization: Bearer <access>` to every subsequent request
4. When you get a `401`, call `POST /api/auth/token/refresh/` with the `refresh` token to get a new `access`
5. On logout, call `POST /accounts/logout/` (invalidates the refresh token server-side) and delete both tokens client-side

---

## 2. Endpoints

### Auth — `/accounts/`

| Method | Path | Auth? | Body |
|---|---|---|---|
| POST | `/accounts/register/` | No | `{ email, password, full_name? }` |
| POST | `/accounts/login/` | No | `{ email, password }` |
| POST | `/accounts/forgot-password/` | No | `{ email }` |
| POST | `/accounts/change-password/` | Yes | `{ old_password, new_password }` |
| GET | `/accounts/profile/` | Yes | — |
| PATCH | `/accounts/profile/` | Yes | `{ full_name }` |
| DELETE | `/accounts/profile/` | Yes | — (irreversible account delete) |
| POST | `/accounts/logout/` | Yes | `{ refresh }` |

**Register/Login response shape:**
```json
{
  "message": "Login successful.",
  "user": { "id": 1, "email": "user@gmail.com", "full_name": "Test User", "date_joined": "..." },
  "tokens": { "access": "eyJ...", "refresh": "eyJ..." }
}
```

### Token refresh — top-level, not under `/accounts/`

| Method | Path | Auth? | Body |
|---|---|---|---|
| POST | `/auth/token/refresh/` | No | `{ refresh }` → returns `{ access }` |

### Knowledge Bases — `/knowledge/`

| Method | Path | Auth? | Notes |
|---|---|---|---|
| GET | `/knowledge/bases/` | Yes | List your knowledge bases |
| POST | `/knowledge/bases/` | Yes | `{ name, description? }` |
| GET | `/knowledge/bases/{id}/` | Yes | |
| PUT/PATCH | `/knowledge/bases/{id}/` | Yes | |
| DELETE | `/knowledge/bases/{id}/` | Yes | |
| GET | `/knowledge/bases/{kb_id}/documents/` | Yes | List documents in a KB |
| POST | `/knowledge/bases/{kb_id}/documents/` | Yes | **multipart/form-data** upload — see below |
| GET/PUT/PATCH/DELETE | `/knowledge/bases/{kb_id}/documents/{doc_id}/` | Yes | |

**Document upload** — `source_type` is one of `PDF`, `DOCX`, `TXT`, `WEBSITE`.
- For `PDF`/`DOCX`/`TXT`: send `file` (multipart), max **50MB**, extension must match `source_type`.
- For `WEBSITE`: send `source_url` instead of a file, no file needed.

```
POST /knowledge/bases/{kb_id}/documents/
Content-Type: multipart/form-data

title: "My PDF"
source_type: "PDF"
file: <binary>
```

Document has a `status` field (processing state) and `chunk_count` once ingestion finishes — poll `GET` on the document if you want to show ingestion progress in the UI.

### Chat — `/chat/`

| Method | Path | Auth? | Notes |
|---|---|---|---|
| GET | `/chat/sessions/` | Yes | List your chat sessions |
| POST | `/chat/sessions/` | Yes | `{ title?, knowledge_base? }` — `knowledge_base` is optional, links session to a KB for RAG context |
| GET | `/chat/sessions/{id}/` | Yes | Returns session **with full message history** |
| DELETE | `/chat/sessions/{id}/` | Yes | |
| GET | `/chat/sessions/{session_id}/messages/` | Yes | List messages in a session |
| POST | `/chat/sessions/{session_id}/messages/` | Yes | `{ content }` — send a user message, get the AI reply back **synchronously in the same response** |

**Sending a chat message — response shape:**
```json
{
  "user_message": { "id": "...", "role": "user", "content": "...", "created_at": "..." },
  "assistant_message": { "id": "...", "role": "assistant", "content": "...", "created_at": "..." }
}
```
This is a **blocking call** — the backend calls OpenRouter and waits for the full reply before responding. No streaming/websockets currently. Expect this to take a few seconds; show a loading/typing indicator in the UI.

---

## 3. Testing with Bearer tokens in Swagger UI

1. Go to `/api/docs/`
2. Call `POST /accounts/register/` (or `/login/`) using "Try it out" → copy the `access` token from the response
3. Click the green **Authorize** button (top right, lock icon)
4. Paste `Bearer <access_token>` into the value field (yes, include the word `Bearer` and a space) → click Authorize → Close
5. Now every "Try it out" call on protected endpoints will include that header automatically

Token expires in 60 minutes — if you start getting `401`s mid-testing, re-login and re-authorize.

---

## 4. CORS setup — required before your frontend can call this API

The backend only allows origins listed in the `CORS_ALLOWED_ORIGINS` env var (currently defaults to `localhost:3000` only). **Whoever owns Railway deploy needs to add your frontend's dev and prod URLs**, e.g.:

```
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://your-frontend.vercel.app
```

Set via Railway CLI:
```
railway variables --set "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,https://your-frontend.vercel.app"
```

Until your frontend's origin is in that list, browser requests will fail with a CORS error even though the API itself is up — this is not a bug, it's the API refusing unknown origins on purpose.

---

## 5. Quick reference — status codes you'll actually see

- `200` / `201` — success
- `400` — validation error (body has field-level error messages)
- `401` — missing/expired/invalid Bearer token → refresh or re-login
- `404` — resource doesn't exist or doesn't belong to you (KBs/sessions/docs are user-scoped — you can't see other users' data)
- `429` — rate limited (20 req/min unauthenticated, 200 req/min authenticated)

---

## 6. Example: full flow in JS (fetch)

```js
const BASE = "https://ragchat-production-95c4.up.railway.app/api";

// 1. Login
const loginRes = await fetch(`${BASE}/accounts/login/`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
const { tokens } = await loginRes.json();

// 2. Create a chat session
const sessionRes = await fetch(`${BASE}/chat/sessions/`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${tokens.access}`,
  },
  body: JSON.stringify({ title: "New chat" }),
});
const session = await sessionRes.json();

// 3. Send a message
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