import os
import sys
import django

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

django.setup()


from knowledge.services.chroma import add_chunks


chunks = [
    "Allah is a du'a away",
    "Protection is a du'a away",
]

# Fake embeddings for testing
# (real ones will come from embedder.py)
embeddings = [
    [0.1, 0.2, 0.3],
    [0.4, 0.5, 0.6],
]


count = add_chunks(
    collection_name="test_collection",
    chunks=chunks,
    embeddings=embeddings,
    document_id="123",
    knowledge_base_id="abc",
)

print("Added chunks:", count)