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
