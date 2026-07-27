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
