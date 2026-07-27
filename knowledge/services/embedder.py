from sentence_transformers import SentenceTransformer
from django.conf import settings


model = SentenceTransformer(
    settings.EMBEDDING_MODEL_NAME
)


def create_embeddings(chunks):
    """
    Convert text chunks into vectors.
    """

    embeddings = model.encode(chunks)

    return embeddings.tolist()