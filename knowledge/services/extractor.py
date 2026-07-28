from pypdf import PdfReader
import requests
from bs4 import BeautifulSoup


def extract_pdf(file_path):
    """
    Extract text from PDF file.
    """

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def extract_docx(file_path):
    """
    Extract text from DOCX file.
    """
    from docx import Document as DocxDocument

    doc = DocxDocument(file_path)
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_txt(file_path):
    """
    Extract text from TXT file.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_website(url):
    """
    Extract text from website URL.
    """

    response = requests.get(url)

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    return soup.get_text(
        separator="\n"
    )



def extract_document(document):
    """
    Decide extraction method based on document type.
    """

    if document.source_type == "pdf":
        return extract_pdf(
            document.file.path
        )

    elif document.source_type == "docx":
        return extract_docx(
            document.file.path
        )

    elif document.source_type == "txt":
        return extract_txt(
            document.file.path
        )

    elif document.source_type == "website":
        return extract_website(
            document.source_url
        )

    else:
        raise ValueError(
            "Unsupported document type"
        )