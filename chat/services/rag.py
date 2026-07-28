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