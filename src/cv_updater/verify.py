"""Safety checks that run before a tailored CV is rendered. These are what make it anti-hallucination."""
from __future__ import annotations

import re

import pdfplumber
from docx import Document

from .render import SECTION_TITLES
from .schema import flatten_text

_NUM = re.compile(r"\d+(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    return set(_NUM.findall(text))


def check_numbers(base: dict, tailored: dict) -> list[str]:
    """Every number in the tailored CV must already exist in the base CV."""
    new = sorted(numbers(flatten_text(tailored)) - numbers(flatten_text(base)))
    return [f"Number '{n}' does not appear in the original CV." for n in new]


def check_immutable_facts(base: dict, tailored: dict) -> list[str]:
    """Employers, roles, dates, schools and degrees must match the original exactly."""
    problems = []
    base_jobs = {(e["company"], e.get("role", ""), e.get("start", ""), e.get("end", "")) for e in base.get("experience", [])}
    for e in tailored.get("experience", []):
        key = (e["company"], e.get("role", ""), e.get("start", ""), e.get("end", ""))
        if key not in base_jobs:
            problems.append(f"Experience entry {key} does not match the original (company/role/dates must be unchanged).")
    base_edu = {(e["institution"], e.get("degree", ""), e.get("year", "")) for e in base.get("education", [])}
    for e in tailored.get("education", []):
        key = (e["institution"], e.get("degree", ""), e.get("year", ""))
        if key not in base_edu:
            problems.append(f"Education entry {key} does not match the original.")
    base_certs = {c["name"] for c in base.get("certifications", [])}
    for c in tailored.get("certifications", []):
        if c["name"] not in base_certs:
            problems.append(f"Certification '{c['name']}' is not in the original CV.")
    return problems


def check_new_skills(base: dict, tailored: dict) -> list[str]:
    """Warning only: skills with no trace in the original CV text (rewording is allowed, invention is not)."""
    base_text = flatten_text(base).lower()
    out = []
    for s in tailored.get("skills", []):
        words = [w for w in re.findall(r"[a-z0-9+#.]+", s.lower()) if len(w) > 2]
        if words and not any(w in base_text for w in words):
            out.append(f"Skill '{s}' has no trace in the original CV. Confirm the user really has it.")
    return out


def verify(base: dict, tailored: dict) -> dict:
    blocking = check_numbers(base, tailored) + check_immutable_facts(base, tailored)
    warnings = check_new_skills(base, tailored)
    return {"passed": not blocking, "blocking": blocking, "warnings": warnings}


def ats_check(cv: dict, file_path: str) -> dict:
    """Extract text from the rendered file and confirm a parser would see it in a sane order."""
    if file_path.lower().endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    else:
        text = "\n".join(p.text for p in Document(file_path).paragraphs)
    lower = text.lower()
    issues = []
    first_line = (text.strip().splitlines() or [""])[0]
    if cv["name"].lower() not in first_line.lower():
        issues.append("Name is not the first line of extracted text.")
    email = cv.get("contact", {}).get("email", "")
    if email and email.lower() not in lower:
        issues.append("Email address did not extract cleanly.")
    positions = []
    for key, title in SECTION_TITLES.items():
        if cv.get(key):
            idx = lower.find(title.lower())
            if idx < 0:
                issues.append(f"Section heading '{title}' not found in extracted text.")
            else:
                positions.append(idx)
    if positions != sorted(positions):
        issues.append("Section headings extract out of order.")
    return {"passed": not issues, "issues": issues, "extracted_chars": len(text)}
