from django.conf import settings


_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def create_embeddings(chunks):
    """
    Convert text chunks into vectors.
    """
    model = _get_model()
    embeddings = model.encode(chunks)
    return embeddings.tolist()