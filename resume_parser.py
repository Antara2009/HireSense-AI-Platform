import os

def extract_resume_text(path, extension):
    extension = extension.lower()
    if extension == "txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if extension == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install project requirements first (pypdf is required).") from exc
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if extension == "docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("Install project requirements first (python-docx is required).") from exc
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError("Unsupported resume format.")
