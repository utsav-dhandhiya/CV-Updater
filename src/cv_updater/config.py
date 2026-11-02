"""Paths and tiny JSON helpers. Everything lives under CV_UPDATER_HOME (default ~/.cv_updater)."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path


def home() -> Path:
    p = Path(os.environ.get("CV_UPDATER_HOME", Path.home() / ".cv_updater"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def cv_path() -> Path:
    return home() / "cv_data.json"


def prefs_path() -> Path:
    return home() / "preferences.json"


def backups_dir() -> Path:
    d = home() / "backups"
    d.mkdir(exist_ok=True)
    return d


def outputs_dir() -> Path:
    d = home() / "outputs"
    d.mkdir(exist_ok=True)
    return d


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slug(text: str, fallback: str = "cv") -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text or "").strip("_").lower()
    return s[:40] or fallback


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
