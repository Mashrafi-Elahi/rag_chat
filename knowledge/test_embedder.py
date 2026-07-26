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


from knowledge.services.embedder import create_embeddings


chunks = [
    "Allah is a du'a away",
    "Protection is a du'a away"
]


vectors = create_embeddings(chunks)


print(len(vectors))
print(len(vectors[0]))