from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from research_agent.models import ResearchSource
from research_agent.summarizer import build_executive_summary


def write_markdown_report(query: str, sources: list[ResearchSource], warnings: list[str], path: Path) -> None:
    lines: list[str] = [
        f"# Research Report: {query}",
        "",
        "## Executive Summary",
        "",
        build_executive_summary(query, sources),
        "",
        "## Source Quality Warnings",
        "",
    ]

    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No source quality warnings detected.")

    lines.extend(["", "## Sources Reviewed", ""])
    for index, source in enumerate(sources, start=1):
        authors = ", ".join(source.authors[:8]) if source.authors else "Unknown"
        lines.extend(
            [
                f"### {index}. {source.title}",
                "",
                f"- Source: {source.source}",
                f"- Published: {source.published or 'Unknown'}",
                f"- Authors: {authors}",
                f"- DOI: {source.doi or 'Not provided'}",
                f"- URL: {source.url or source.pdf_url or 'Not provided'}",
                "",
                "Summary:",
                "",
                source.summary,
                "",
            ]
        )

    lines.extend(
        [
            "## Method",
            "",
            "- Search used public academic endpoints only: arXiv, PubMed, Crossref, and Semantic Scholar.",
            "- Summaries are extractive by default and do not use paid model APIs.",
            "- Google Scholar, IEEE scraping, random scraping, and paid API keys were intentionally avoided.",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_html_report(query: str, sources: list[ResearchSource], warnings: list[str], path: Path) -> None:
    warning_items = "".join(f"<li>{escape(warning)}</li>" for warning in warnings) or "<li>No source quality warnings detected.</li>"
    source_cards = "\n".join(_html_source_card(index, source) for index, source in enumerate(sources, start=1))
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="theme-color" content="#ffffff">
  <title>Research Report: {escape(query)}</title>
  <style>
    :root {{
      color-scheme: light;
    }}
    html, body {{
      background: #ffffff !important;
      color: #111827 !important;
    }}
    body {{
      font-family: Georgia, serif;
      line-height: 1.65;
      max-width: 980px;
      margin: 0 auto;
      padding: 28px 20px 48px;
      color: #111827;
    }}
    h1, h2, h3 {{
      font-family: Arial, sans-serif;
      line-height: 1.15;
      color: #0f1730;
    }}
    h1 {{ font-size: clamp(2rem, 6vw, 3.25rem); margin-bottom: .85rem; }}
    h2 {{ margin-top: 1.8rem; }}
    .card {{
      border: 1px solid #d9e2ec;
      border-radius: 14px;
      padding: 20px;
      margin: 18px 0;
      background: #fbfdff;
      break-inside: avoid;
    }}
    .meta {{ color: #52606d; font-size: 14px; word-break: break-word; }}
    a {{ color: #0b5cad; word-break: break-word; }}
    ul {{ padding-left: 1.1rem; }}
    @media (max-width: 640px) {{
      body {{ padding: 16px 12px 36px; line-height: 1.6; }}
      .card {{ padding: 16px; border-radius: 12px; }}
      h1 {{ font-size: 2rem; }}
      h2 {{ font-size: 1.2rem; }}
      h3 {{ font-size: 1.05rem; }}
    }}
  </style>
</head>
<body>
  <h1>Research Report: {escape(query)}</h1>
  <h2>Executive Summary</h2>
  <p>{escape(build_executive_summary(query, sources))}</p>
  <h2>Source Quality Warnings</h2>
  <ul>{warning_items}</ul>
  <h2>Sources Reviewed</h2>
  {source_cards}
  <h2>Method</h2>
  <p>Search used public academic endpoints only. Summaries are extractive by default. Paid model APIs and aggressive scraping were avoided.</p>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def write_pdf_report(query: str, sources: list[ResearchSource], warnings: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ZeroBody", parent=styles["BodyText"], textColor=colors.HexColor("#111827"), leading=15))
    styles.add(ParagraphStyle(name="ZeroTitle", parent=styles["Title"], textColor=colors.HexColor("#0f1730")))
    styles.add(ParagraphStyle(name="ZeroHeading2", parent=styles["Heading2"], textColor=colors.HexColor("#0f1730")))
    styles.add(ParagraphStyle(name="ZeroHeading3", parent=styles["Heading3"], textColor=colors.HexColor("#0f1730")))
    story = [
        Paragraph(f"Research Report: {escape(query)}", styles["ZeroTitle"]),
        Spacer(1, 12),
        Paragraph("Executive Summary", styles["ZeroHeading2"]),
        Paragraph(escape(build_executive_summary(query, sources)), styles["ZeroBody"]),
        Spacer(1, 12),
        Paragraph("Source Quality Warnings", styles["ZeroHeading2"]),
    ]

    for warning in warnings or ["No source quality warnings detected."]:
        story.append(Paragraph(f"- {escape(warning)}", styles["ZeroBody"]))

    story.extend([Spacer(1, 12), Paragraph("Sources Reviewed", styles["ZeroHeading2"])])
    for index, source in enumerate(sources, start=1):
        story.append(Paragraph(f"{index}. {escape(source.title)}", styles["ZeroHeading3"]))
        story.append(Paragraph(escape(_plain_meta(source)), styles["ZeroBody"]))
        story.append(Paragraph(escape(source.summary), styles["ZeroBody"]))
        story.append(Spacer(1, 10))

    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
    doc.build(story)


def _html_source_card(index: int, source: ResearchSource) -> str:
    url = source.url or source.pdf_url
    link = f'<a href="{escape(url)}">{escape(url)}</a>' if url else "Not provided"
    return f"""<article class="card">
  <h3>{index}. {escape(source.title)}</h3>
  <p class="meta">{escape(_plain_meta(source))}</p>
  <p class="meta">URL: {link}</p>
  <p>{escape(source.summary)}</p>
</article>"""


def _plain_meta(source: ResearchSource) -> str:
    authors = ", ".join(source.authors[:8]) if source.authors else "Unknown authors"
    return (
        f"Source: {source.source} | Published: {source.published or 'Unknown'} | "
        f"Authors: {authors} | DOI: {source.doi or 'Not provided'}"
    )
