from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ResearchPlan:
    original_query: str
    search_terms: list[str]
    sources: list[str]
    max_results_per_source: int
    parse_documents: bool = False
    use_local_llm: bool = False


@dataclass(slots=True)
class ResearchSource:
    source: str
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    url: str = ""
    pdf_url: str = ""
    published: str = ""
    doi: str = ""
    source_id: str = ""
    full_text: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "published": self.published,
            "doi": self.doi,
            "source_id": self.source_id,
            "full_text": self.full_text,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchSource":
        return cls(
            source=str(data.get("source", "")),
            title=str(data.get("title", "")),
            authors=list(data.get("authors", []) or []),
            abstract=str(data.get("abstract", "")),
            url=str(data.get("url", "")),
            pdf_url=str(data.get("pdf_url", "")),
            published=str(data.get("published", "")),
            doi=str(data.get("doi", "")),
            source_id=str(data.get("source_id", "")),
            full_text=str(data.get("full_text", "")),
            summary=str(data.get("summary", "")),
        )
