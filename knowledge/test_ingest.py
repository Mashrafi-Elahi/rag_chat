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


from knowledge.models import Document
from knowledge.services.ingest import ingest_document


document = Document.objects.first()

print("Before:", document.status)

ingest_document(document)

document.refresh_from_db()

print("After:", document.status)
print("Chunks:", document.chunk_count)