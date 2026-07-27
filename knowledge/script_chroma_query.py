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


from knowledge.services.chroma import get_collection


collection = get_collection("test_collection")


results = collection.query(
    query_embeddings=[
        [0.1, 0.2, 0.3]
    ],
    n_results=2
)


print(results)