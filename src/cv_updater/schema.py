"""Canonical CV schema. Content is stored once; templates only decide how it looks."""
from __future__ import annotations

import shutil
from typing import Any

from . import config

LIST_SECTIONS = ("skills", "experience", "projects", "education", "certifications", "achievements")

EXAMPLE_SCHEMA: dict[str, Any] = {
    "name": "",
    "title": "",
    "contact": {"phone": "", "email": "", "linkedin": "", "location": ""},
    "summary": "",
    "skills": ["Python"],
    "experience": [
        {"company": "", "role": "", "location": "", "start": "", "end": "", "bullets": [""]}
    ],
    "projects": [{"name": "", "tech": "", "bullets": [""]}],
    "education": [{"institution": "", "degree": "", "year": "", "location": ""}],
    "certifications": [{"name": "", "issuer": "", "date": "", "credential_id": ""}],
    "achievements": [{"title": "", "description": ""}],
}


class CVError(ValueError):
    """Raised for problems the caller (the LLM) can fix; the message says how."""


def validate(cv: dict) -> dict:
    if not isinstance(cv, dict):
        raise CVError("CV JSON must be an object.")
    if not cv.get("name"):
        raise CVError("CV JSON needs a non-empty 'name'. See the schema in the `parse_cv_to_json` prompt.")
    for key in LIST_SECTIONS:
        if key in cv and not isinstance(cv[key], list):
            raise CVError(f"'{key}' must be a list.")
    for entry in cv.get("experience", []):
        if not isinstance(entry, dict) or not entry.get("company"):
            raise CVError("Each experience entry needs 'company', 'role', 'start', 'end' and 'bullets'.")
    return cv


def load_cv() -> dict:
    cv = config.read_json(config.cv_path())
    if not cv:
        raise CVError("No base CV saved yet. Call `import_cv` on your CV file, structure it, then `save_cv_data`.")
    return cv


def save_cv(cv: dict) -> str:
    """Save as the base CV. Backs up the previous version with a timestamp."""
    validate(cv)
    path = config.cv_path()
    backup = ""
    if path.exists():
        b = config.backups_dir() / f"cv_data_{config.timestamp()}.json"
        shutil.copy2(path, b)
        backup = str(b)
    config.write_json(path, cv)
    return backup


def merge(base: dict, tailored: dict | None) -> dict:
    """Tailored values override the base per top-level key; missing keys fall back to the base."""
    out = dict(base)
    for k, v in (tailored or {}).items():
        if v not in (None, "", [], {}):
            out[k] = v
    return validate(out)


def flatten_text(value: Any) -> str:
    """All strings in a CV (or any nested value) joined into one text blob."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(flatten_text(v) for v in value)
    return ""
