from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class StoredReport:
    report_id: str
    query: str
    created_at: str
    source_count: int
    warning_count: int
    markdown_path: str
    html_path: str
    pdf_path: str
    raw_json_path: str
    markdown_content: str
    html_content: str
    pdf_bytes: bytes
    raw_json_content: str


def init_store(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                created_at TEXT NOT NULL,
                source_count INTEGER NOT NULL,
                warning_count INTEGER NOT NULL,
                markdown_path TEXT NOT NULL,
                html_path TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                raw_json_path TEXT NOT NULL,
                markdown_content TEXT NOT NULL,
                html_content TEXT NOT NULL,
                pdf_bytes BLOB NOT NULL,
                raw_json_content TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC)")
        conn.commit()


def save_report(db_path: Path, report: StoredReport) -> None:
    init_store(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO reports (
                report_id, query, created_at, source_count, warning_count,
                markdown_path, html_path, pdf_path, raw_json_path,
                markdown_content, html_content, pdf_bytes, raw_json_content
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                query=excluded.query,
                created_at=excluded.created_at,
                source_count=excluded.source_count,
                warning_count=excluded.warning_count,
                markdown_path=excluded.markdown_path,
                html_path=excluded.html_path,
                pdf_path=excluded.pdf_path,
                raw_json_path=excluded.raw_json_path,
                markdown_content=excluded.markdown_content,
                html_content=excluded.html_content,
                pdf_bytes=excluded.pdf_bytes,
                raw_json_content=excluded.raw_json_content
            """,
            (
                report.report_id,
                report.query,
                report.created_at,
                report.source_count,
                report.warning_count,
                report.markdown_path,
                report.html_path,
                report.pdf_path,
                report.raw_json_path,
                report.markdown_content,
                report.html_content,
                report.pdf_bytes,
                report.raw_json_content,
            ),
        )
        conn.commit()


def list_reports(db_path: Path, limit: int = 8) -> list[StoredReport]:
    init_store(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT report_id, query, created_at, source_count, warning_count,
                   markdown_path, html_path, pdf_path, raw_json_path,
                   markdown_content, html_content, pdf_bytes, raw_json_content
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_report(row) for row in rows]


def get_report(db_path: Path, report_id: str) -> StoredReport | None:
    init_store(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT report_id, query, created_at, source_count, warning_count,
                   markdown_path, html_path, pdf_path, raw_json_path,
                   markdown_content, html_content, pdf_bytes, raw_json_content
            FROM reports
            WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()
    return _row_to_report(row) if row else None


def bootstrap_reports_from_outputs(output_dir: Path, db_path: Path) -> int:
    init_store(db_path)
    with sqlite3.connect(db_path) as conn:
        existing_ids = {row[0] for row in conn.execute("SELECT report_id FROM reports").fetchall()}
    imported = 0

    for markdown_path in sorted(output_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True):
        report_id = markdown_path.stem
        if report_id in existing_ids:
            continue

        html_path = markdown_path.with_suffix(".html")
        pdf_path = markdown_path.with_suffix(".pdf")
        raw_json_path = markdown_path.with_name(f"{report_id}-raw.json")

        markdown_content = markdown_path.read_text(encoding="utf-8")
        html_content = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
        raw_json_content = raw_json_path.read_text(encoding="utf-8") if raw_json_path.exists() else "{}"
        pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else b""
        query = _extract_query(markdown_content) or _title_from_slug(report_id)
        source_count = _extract_source_count(raw_json_content)
        warning_count = _extract_warning_count(raw_json_content)

        save_report(
            db_path,
            StoredReport(
                report_id=report_id,
                query=query,
                created_at=datetime.fromtimestamp(markdown_path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
                source_count=source_count,
                warning_count=warning_count,
                markdown_path=str(markdown_path),
                html_path=str(html_path),
                pdf_path=str(pdf_path),
                raw_json_path=str(raw_json_path),
                markdown_content=markdown_content,
                html_content=html_content,
                pdf_bytes=pdf_bytes,
                raw_json_content=raw_json_content,
            ),
        )
        imported += 1
        existing_ids.add(report_id)

    return imported


def _row_to_report(row: sqlite3.Row | None) -> StoredReport | None:
    if row is None:
        return None
    return StoredReport(
        report_id=row["report_id"],
        query=row["query"],
        created_at=row["created_at"],
        source_count=int(row["source_count"]),
        warning_count=int(row["warning_count"]),
        markdown_path=row["markdown_path"],
        html_path=row["html_path"],
        pdf_path=row["pdf_path"],
        raw_json_path=row["raw_json_path"],
        markdown_content=row["markdown_content"],
        html_content=row["html_content"],
        pdf_bytes=row["pdf_bytes"],
        raw_json_content=row["raw_json_content"],
    )


def _extract_query(markdown_content: str) -> str:
    first_line = markdown_content.splitlines()[0].strip() if markdown_content else ""
    prefix = "# Research Report: "
    if first_line.startswith(prefix):
        return first_line[len(prefix):].strip()
    return ""


def _extract_source_count(raw_json_content: str) -> int:
    try:
        return len(json.loads(raw_json_content).get("sources", []))
    except json.JSONDecodeError:
        return 0


def _extract_warning_count(raw_json_content: str) -> int:
    try:
        return len(json.loads(raw_json_content).get("collector_warnings", []))
    except json.JSONDecodeError:
        return 0


def _title_from_slug(report_id: str) -> str:
    return report_id.replace("-", " ").title()
