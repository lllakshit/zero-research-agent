from __future__ import annotations

from research_agent.models import ResearchSource


def review_sources(sources: list[ResearchSource]) -> list[str]:
    warnings: list[str] = []
    if not sources:
        return ["No sources were found. Use a broader query or reduce filters."]

    missing_urls = sum(1 for source in sources if not source.url)
    missing_abstracts = sum(1 for source in sources if not source.abstract and not source.full_text)
    missing_authors = sum(1 for source in sources if not source.authors)
    missing_years = sum(1 for source in sources if not source.published)

    if missing_urls:
        warnings.append(f"{missing_urls} source(s) are missing direct URLs.")
    if missing_abstracts:
        warnings.append(f"{missing_abstracts} source(s) have no public abstract/full text.")
    if missing_authors:
        warnings.append(f"{missing_authors} source(s) are missing author metadata.")
    if missing_years:
        warnings.append(f"{missing_years} source(s) are missing publication year/date metadata.")

    weak_summaries = sum(1 for source in sources if source.summary.startswith("No abstract"))
    if weak_summaries:
        warnings.append(f"{weak_summaries} source(s) could not be summarized strongly because public text was unavailable.")

    return warnings
