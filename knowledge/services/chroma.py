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