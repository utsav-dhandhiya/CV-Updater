"""Rendering helpers (DOCX -> PDF -> PNG via LibreOffice + PyMuPDF) and the page-fit engine."""
from __future__ import annotations

import copy
import shutil
import subprocess
import tempfile
from pathlib import Path

import pymupdf as fitz  # PyMuPDF

from .render import build_docx
from .templates import Template

# (spacing_scale, font_delta) tried in order before any content is trimmed
LEVELS = [(1.0, 0.0), (0.85, 0.0), (0.7, 0.0), (0.7, -0.5), (0.7, -1.0)]
MIN_BULLETS_PER_ENTRY = 2


def soffice_path() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def to_pdf(docx_path: str, out_dir: str | None = None) -> str:
    exe = soffice_path()
    if not exe:
        raise RuntimeError("LibreOffice ('soffice') is not installed, so PDF output, previews and page-fit are unavailable.")
    out = Path(out_dir or Path(docx_path).parent)
    with tempfile.TemporaryDirectory() as profile:  # private profile avoids lock clashes between runs
        subprocess.run(
            [exe, f"-env:UserInstallation=file://{profile}", "--headless", "--convert-to", "pdf",
             "--outdir", str(out), str(docx_path)],
            check=True, capture_output=True, timeout=120,
        )
    pdf = out / (Path(docx_path).stem + ".pdf")
    if not pdf.exists():
        raise RuntimeError("LibreOffice ran but produced no PDF.")
    return str(pdf)


def page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return doc.page_count


def pdf_to_png(pdf_path: str, page: int = 0, zoom: float = 1.1) -> bytes:
    with fitz.open(pdf_path) as doc:
        return doc[page].get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")


def _trim_one(cv: dict) -> str | None:
    """Drop the last bullet of the entry with the most bullets (bullets are written most-relevant-first)."""
    candidates = [
        (len(e.get("bullets", [])), kind, i)
        for kind in ("experience", "projects")
        for i, e in enumerate(cv.get(kind, []))
        if len(e.get("bullets", [])) > MIN_BULLETS_PER_ENTRY
    ]
    if not candidates:
        return None
    _, kind, i = max(candidates)
    entry = cv[kind][i]
    dropped = entry["bullets"].pop()
    label = entry.get("company") or entry.get("name", kind)
    return f"Dropped last bullet of '{label}': {dropped[:70]}..."


def fit_to_pages(cv: dict, tpl: Template, max_pages: int, docx_path: str) -> dict:
    """Render, measure, tighten. Returns the (possibly trimmed) CV plus a log of what changed."""
    work = copy.deepcopy(cv)
    actions: list[str] = []

    if not soffice_path():
        build_docx(work, tpl, docx_path)
        return {"cv": work, "pages": None, "fitted": None, "pdf": None,
                "actions": ["LibreOffice not found: page count not measured, no fitting applied."]}

    def attempt(scale, delta):
        build_docx(work, tpl, docx_path, scale, delta)
        pdf = to_pdf(docx_path)
        return pdf, page_count(pdf)

    pdf, pages = attempt(*LEVELS[0])
    for scale, delta in LEVELS[1:]:
        if pages <= max_pages:
            break
        actions.append(f"Over {max_pages} page(s) ({pages}): tightened spacing x{scale}, font {delta:+g}pt.")
        pdf, pages = attempt(scale, delta)

    guard = 0
    while pages > max_pages and guard < 20:
        note = _trim_one(work)
        if not note:
            actions.append("Cannot fit without removing more content; consider a Compact template or a higher page limit.")
            break
        actions.append(note)
        pdf, pages = attempt(*LEVELS[-1])
        guard += 1

    return {"cv": work, "pages": pages, "fitted": pages <= max_pages, "pdf": pdf, "actions": actions}
