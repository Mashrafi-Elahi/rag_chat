"""
chat/services/rag.py

Responsible for the entire RAG pipeline:
  1. Lazy-load a local sentence embedding model.
  2. Retrieve relevant text chunks from ChromaDB (if a KnowledgeBase is linked).
  3. Build a system prompt with the retrieved context.
  4. Call the OpenRouter LLM API and return the reply.

Views and serializers must NOT contain any of this logic — they call
`generate_rag_response` and receive a plain string back.
"""

import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model — lazy-loaded once per process to avoid blocking Django
# startup and migrations with PyTorch DLL initialisation.
# ---------------------------------------------------------------------------
_EMBEDDING_MODEL = None


def get_embedding_model():
    """Return the cached SentenceTransformer instance, loading it on first call."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model 'all-MiniLM-L6-v2' loaded.")
    return _EMBEDDING_MODEL


# ---------------------------------------------------------------------------
# ChromaDB retrieval
# ---------------------------------------------------------------------------

def retrieve_context(chroma_collection_id: str, user_query: str, n_results: int = 3) -> str:
    """
    Query ChromaDB for the most relevant text chunks.

    Returns a newline-joined string of retrieved chunks, or an empty string
    if the collection does not exist or the query fails.
    """
    import chromadb  # noqa: PLC0415 — optional dependency, not forced at import time

    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        collection = chroma_client.get_collection(name=chroma_collection_id)

        embedding_model = get_embedding_model()
        query_vector = embedding_model.encode(user_query).tolist()

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=n_results,
        )

        if results and results.get("documents"):
            return "\n\n".join(results["documents"][0])

    except Exception:
        logger.exception(
            "ChromaDB retrieval failed for collection '%s'.", chroma_collection_id
        )

    return ""


# ---------------------------------------------------------------------------
# OpenRouter LLM call
# ---------------------------------------------------------------------------

def call_openrouter(messages: list[dict], model: str, api_key: str) -> str:
    """
    POST the message list to OpenRouter and return the assistant's reply text.

    Raises RuntimeError on HTTP errors or network failures so the caller can
    decide how to surface the error.
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "messages": messages},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.exception("Network error calling OpenRouter.")
        raise RuntimeError(f"Failed to reach OpenRouter: {exc}") from exc

    if response.status_code != 200:
        logger.error(
            "OpenRouter returned %s: %s", response.status_code, response.text[:200]
        )
        raise RuntimeError(
            f"OpenRouter error ({response.status_code}): {response.text}"
        )

    return response.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Public entry point — called by the serializer
# ---------------------------------------------------------------------------

def generate_rag_response(session, user_query: str) -> str:
    """
    Orchestrate the full RAG pipeline for a single user turn.

    Args:
        session:    ChatSession ORM instance (may have .knowledge_base set).
        user_query: The raw user message string.

    Returns:
        A plain-string reply from the LLM (or an error message string if the
        LLM call fails — the caller persists this as the assistant message).
    """
    # --- 1. Retrieve context from ChromaDB (if a KB is linked) ---------------
    context_text = ""
    kb = session.knowledge_base
    if kb and kb.chroma_collection_id:
        context_text = retrieve_context(kb.chroma_collection_id, user_query)

    # --- 2. Build prompt -------------------------------------------------------
    if context_text:
        system_prompt = (
            "You are a helpful assistant. Answer the user's question using ONLY "
            "the context provided below. If the context does not contain enough "
            "information, state that clearly.\n\n"
            f"Context:\n{context_text}"
        )
    else:
        system_prompt = "You are a helpful AI assistant."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
    ]

    # --- 3. Call OpenRouter ----------------------------------------------------
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv(
        "OPENROUTER_API_KEY"
    )
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not configured.")
        return "Error: OPENROUTER_API_KEY is missing from environment/settings."

    model_name = getattr(settings, "OPENROUTER_MODEL", "openai/gpt-3.5-turbo")

    try:
        return call_openrouter(messages, model_name, api_key)
    except RuntimeError as exc:
        logger.error("RAG response generation failed: %s", exc)
        return str(exc)
