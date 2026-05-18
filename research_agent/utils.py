from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

USER_AGENT = "ZeroKeyResearchAgent/0.1 (local personal research tool; no paid APIs)"
REQUEST_TIMEOUT_SECONDS = 25


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def safe_filename(value: str, fallback: str = "research_report") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    cleaned = cleaned.strip("-._")
    return cleaned[:90] or fallback


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
