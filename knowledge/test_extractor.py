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
from knowledge.services.extractor import extract_document


document = Document.objects.first()

text = extract_document(document)

print(text[:500])