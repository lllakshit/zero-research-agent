from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests
from pypdf.errors import PdfReadError

from research_agent.collectors import collect_sources_with_warnings
from research_agent.local_llm import summarize_with_ollama
from research_agent.models import ResearchSource
from research_agent.parser import extract_source_text
from research_agent.planner import create_plan
from research_agent.reviewer import review_sources
from research_agent.summarizer import summarize_sources
from research_agent.utils import safe_filename, timestamp_slug, write_json
from research_agent.writer import write_html_report, write_markdown_report, write_pdf_report


@dataclass(slots=True)
class PipelineResult:
    query: str
    sources: list[ResearchSource]
    warnings: list[str]
    raw_json_path: Path
    markdown_path: Path
    html_path: Path
    pdf_path: Path


def run_research(
    query: str,
    *,
    output_dir: Path,
    max_results_per_source: int = 5,
    sources: list[str] | None = None,
    local_sources: list[ResearchSource] | None = None,
    parse_documents: bool = False,
    max_documents_to_parse: int = 3,
    use_local_llm: bool = False,
    ollama_model: str = "qwen2.5",
) -> PipelineResult:
    plan = create_plan(
        query,
        max_results_per_source=max_results_per_source,
        sources=sources,
        parse_documents=parse_documents,
        use_local_llm=use_local_llm,
    )
    collected, warnings = collect_sources_with_warnings(plan)
    collected = [*(local_sources or []), *collected]

    slug = f"{timestamp_slug()}-{safe_filename(query)}"
    raw_json_path = output_dir / f"{slug}-raw.json"
    write_json(
        raw_json_path,
        {
            "plan": {
                "original_query": plan.original_query,
                "search_terms": plan.search_terms,
                "sources": plan.sources,
                "max_results_per_source": plan.max_results_per_source,
                "parse_documents": plan.parse_documents,
                "use_local_llm": plan.use_local_llm,
            },
            "collector_warnings": warnings,
            "sources": [source.to_dict() for source in collected],
        },
    )

    if parse_documents:
        parsed_count = 0
        for source in collected:
            if parsed_count >= max_documents_to_parse:
                break
            try:
                source.full_text = extract_source_text(source)
            except (requests.RequestException, ValueError, OSError, PdfReadError, UnicodeDecodeError) as exc:
                warnings.append(f"Document parsing failed for '{source.title}': {exc}")
            if source.full_text:
                parsed_count += 1

    summarized = summarize_sources(collected)

    if use_local_llm:
        try:
            for source in summarized[: min(5, len(summarized))]:
                text = source.full_text or source.abstract
                if text:
                    source.summary = summarize_with_ollama(text, model=ollama_model)
        except RuntimeError as exc:
            warnings.append(f"Ollama summarization skipped: {exc}")

    warnings.extend(review_sources(summarized))
    warnings = _dedupe_warnings(warnings)

    markdown_path = output_dir / f"{slug}.md"
    html_path = output_dir / f"{slug}.html"
    pdf_path = output_dir / f"{slug}.pdf"

    write_markdown_report(query, summarized, warnings, markdown_path)
    write_html_report(query, summarized, warnings, html_path)
    write_pdf_report(query, summarized, warnings, pdf_path)

    return PipelineResult(
        query=query,
        sources=summarized,
        warnings=warnings,
        raw_json_path=raw_json_path,
        markdown_path=markdown_path,
        html_path=html_path,
        pdf_path=pdf_path,
    )


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        if warning not in seen:
            seen.add(warning)
            unique.append(warning)
    return unique
