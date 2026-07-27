import os
import sys

# Add project root to Python path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from knowledge.services.chunker import chunk_text


text = """
This is a very long document.
It contains many words.
We want to split it into smaller pieces.
"""


chunks = chunk_text(text, chunk_size=5)

for chunk in chunks:
    print("----")
    print(chunk)