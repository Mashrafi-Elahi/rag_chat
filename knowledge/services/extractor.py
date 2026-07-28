from pathlib import Path

from pypdf import PdfReader
import requests
from bs4 import BeautifulSoup


def extract_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def extract_txt(file_path):
    return Path(file_path).read_text(encoding="utf-8")


def extract_docx(file_path):
    try:
        from docx import Document as DocxDocument
    except ImportError:
        raise ImportError("python-docx is required to extract .docx files")
    doc = DocxDocument(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_website(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text(separator="\n")


def extract_document(document):
    if document.source_type == "pdf":
        return extract_pdf(document.file.path)
    elif document.source_type == "txt":
        return extract_txt(document.file.path)
    elif document.source_type == "docx":
        return extract_docx(document.file.path)
    elif document.source_type == "website":
        return extract_website(document.source_url)
    else:
        raise ValueError(f"Unsupported document type: {document.source_type}")