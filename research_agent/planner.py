from __future__ import annotations

import re

from research_agent.models import ResearchPlan


DEFAULT_SOURCES = ["arxiv", "pubmed", "crossref", "semantic_scholar"]


def create_plan(
    query: str,
    *,
    max_results_per_source: int = 5,
    sources: list[str] | None = None,
    parse_documents: bool = False,
    use_local_llm: bool = False,
) -> ResearchPlan:
    query = query.strip()
    if not query:
        raise ValueError("Research query cannot be empty.")

    normalized_sources = sources or DEFAULT_SOURCES
    search_terms = build_search_terms(query)

    return ResearchPlan(
        original_query=query,
        search_terms=search_terms,
        sources=normalized_sources,
        max_results_per_source=max(1, min(max_results_per_source, 20)),
        parse_documents=parse_documents,
        use_local_llm=use_local_llm,
    )


def build_search_terms(query: str) -> list[str]:
    terms = [
        query,
        f"{query} review",
        f"{query} survey",
        f"{query} recent advances",
    ]

    compact = re.sub(r"\b(please|research|report|about|on)\b", " ", query, flags=re.I)
    compact = re.sub(r"\s+", " ", compact).strip()
    if compact and compact.lower() != query.lower():
        terms.append(compact)

    unique: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique
