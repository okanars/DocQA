import os
import fitz
from docx import Document
from pathlib import Path


def parse_file(filepath: str) -> list[dict]:
    ext = Path(filepath).suffix.lower()
    parsers = {
        ".pdf": _parse_pdf,
        ".docx": _parse_docx,
        ".txt": _parse_txt,
    }

    parser = parsers.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: {ext}")

    return parser(filepath)


def _parse_pdf(filepath: str) -> list[dict]:
    pages = []
    with fitz.open(filepath) as doc:
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append({"text": text, "page": i + 1})
    return pages


def _parse_docx(filepath: str) -> list[dict]:
    doc = Document(filepath)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if not full_text.strip():
        return []
    return [{"text": full_text, "page": 1}]


def _parse_txt(filepath: str) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return []
    return [{"text": text, "page": 1}]


def save_upload(file_bytes: bytes, filename: str, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    counter = 1
    base, ext = os.path.splitext(filepath)
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{ext}"
        counter += 1

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    return filepath
