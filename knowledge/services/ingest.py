from knowledge.services.extractor import extract_document
from knowledge.services.chunker import chunk_text
from knowledge.services.embedder import create_embeddings
from knowledge.services.chroma import add_chunks

from knowledge.models import Document


def ingest_document(document):
    try:
        # Mark as processing
        document.status = Document.Status.PROCESSING
        document.save()

        # 1. Extract text
        text = extract_document(document)

        if not text.strip():
            raise ValueError("No text extracted from document")

        # 2. Split text
        chunks = chunk_text(text)

        # 3. Create embeddings
        embeddings = create_embeddings(chunks)

        # 4. Store in Chroma
        count = add_chunks(
            collection_name=document.knowledge_base.chroma_collection_id,
            chunks=chunks,
            embeddings=embeddings,
            document_id=document.id,
            knowledge_base_id=document.knowledge_base.id,
        )

        # 5. Update document
        document.status = Document.Status.READY
        document.chunk_count = count
        document.save()

        return document

    except Exception as e:
        document.status = Document.Status.FAILED
        document.error_message = str(e)
        document.save()

        raise e
    