"""Text extraction from PDF / DOCX CVs. Design is NOT extracted: users pick a template instead."""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
from docx import Document


def _clean(text: str) -> str:
    text = re.sub(r"\(cid:\d+\)", "•", text)  # bullet glyphs that pdfplumber cannot decode
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_text(file_path: str) -> str:
    p = Path(file_path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    ext = p.suffix.lower()
    if ext == ".pdf":
        with pdfplumber.open(p) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n\n".join(pages)
        if len(text.strip()) < 50:
            raise ValueError("This PDF has almost no extractable text (probably a scan). OCR is not supported yet.")
        return _clean(text)
    if ext == ".docx":
        doc = Document(p)
        parts = [para.text for para in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return _clean("\n".join(parts))
    raise ValueError(f"Unsupported file type '{ext}'. Use .pdf or .docx.")
