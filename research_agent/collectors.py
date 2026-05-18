from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

import feedparser
import requests

from research_agent.models import ResearchPlan, ResearchSource
from research_agent.utils import REQUEST_TIMEOUT_SECONDS, USER_AGENT, clean_text


def collect_sources(plan: ResearchPlan) -> list[ResearchSource]:
    sources, warnings = collect_sources_with_warnings(plan)
    if warnings and not sources:
        raise RuntimeError("; ".join(warnings))
    return sources


def collect_sources_with_warnings(plan: ResearchPlan) -> tuple[list[ResearchSource], list[str]]:
    collectors = {
        "arxiv": search_arxiv,
        "pubmed": search_pubmed,
        "crossref": search_crossref,
        "semantic_scholar": search_semantic_scholar,
    }

    results: list[ResearchSource] = []
    warnings: list[str] = []
    for term in plan.search_terms:
        for source_name in plan.sources:
            collector = collectors.get(source_name)
            if collector is None:
                warnings.append(f"Unknown source skipped: {source_name}")
                continue
            try:
                results.extend(collector(term, plan.max_results_per_source))
            except (requests.RequestException, ET.ParseError, ValueError) as exc:
                warnings.append(f"{source_name} failed for '{term}': {exc}")
            time.sleep(0.2)

    return dedupe_sources(results), warnings


def search_arxiv(query: str, max_results: int = 5) -> list[ResearchSource]:
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query=all:{quote(query)}&start=0&max_results={max_results}"
        "&sortBy=relevance&sortOrder=descending"
    )
    feed = feedparser.parse(url)

    results: list[ResearchSource] = []
    for entry in feed.entries:
        links = entry.get("links", [])
        pdf_url = next((link.href for link in links if link.get("type") == "application/pdf"), "")
        results.append(
            ResearchSource(
                source="arXiv",
                title=clean_text(entry.get("title", "")),
                authors=[author.name for author in entry.get("authors", [])],
                abstract=clean_text(entry.get("summary", "")),
                url=entry.get("link", ""),
                pdf_url=pdf_url,
                published=entry.get("published", ""),
                source_id=entry.get("id", ""),
            )
        )
    return results


def search_pubmed(query: str, max_results: int = 5) -> list[ResearchSource]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    search_response = session.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed", "term": query, "retmode": "json", "retmax": max_results},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    search_response.raise_for_status()
    ids = search_response.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    fetch_response = session.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    fetch_response.raise_for_status()

    root = ET.fromstring(fetch_response.text)
    results: list[ResearchSource] = []
    for article in root.findall(".//PubmedArticle"):
        medline = article.find("MedlineCitation")
        article_node = medline.find("Article") if medline is not None else None
        if article_node is None:
            continue

        pmid = _node_text(medline.find("PMID") if medline is not None else None)
        title = clean_text("".join(article_node.findtext("ArticleTitle", default="")))
        abstract = " ".join(
            clean_text("".join(abstract_node.itertext()))
            for abstract_node in article_node.findall(".//AbstractText")
        )
        authors = []
        for author in article_node.findall(".//Author"):
            last = _node_text(author.find("LastName"))
            fore = _node_text(author.find("ForeName"))
            collective = _node_text(author.find("CollectiveName"))
            name = collective or f"{fore} {last}".strip()
            if name:
                authors.append(name)

        doi = ""
        for article_id in article.findall(".//ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = clean_text(article_id.text or "")
                break

        results.append(
            ResearchSource(
                source="PubMed",
                title=title,
                authors=authors,
                abstract=clean_text(abstract),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                published=_pubmed_year(article_node),
                doi=doi,
                source_id=pmid,
            )
        )
    return results


def search_crossref(query: str, max_results: int = 5) -> list[ResearchSource]:
    response = requests.get(
        "https://api.crossref.org/works",
        params={"query": query, "rows": max_results, "select": "title,author,abstract,URL,DOI,published-print,published-online,issued"},
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    items = response.json().get("message", {}).get("items", [])

    results: list[ResearchSource] = []
    for item in items:
        title = clean_text((item.get("title") or [""])[0])
        authors = [
            f"{author.get('given', '')} {author.get('family', '')}".strip()
            for author in item.get("author", [])
            if author.get("given") or author.get("family")
        ]
        results.append(
            ResearchSource(
                source="Crossref",
                title=title,
                authors=authors,
                abstract=clean_text(item.get("abstract", "")),
                url=item.get("URL", ""),
                published=_crossref_year(item),
                doi=item.get("DOI", ""),
                source_id=item.get("DOI", ""),
            )
        )
    return results


def search_semantic_scholar(query: str, max_results: int = 5) -> list[ResearchSource]:
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={
            "query": query,
            "limit": max_results,
            "fields": "title,abstract,authors,year,url,externalIds,openAccessPdf",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    results: list[ResearchSource] = []
    for item in response.json().get("data", []):
        external_ids = item.get("externalIds") or {}
        open_pdf = item.get("openAccessPdf") or {}
        results.append(
            ResearchSource(
                source="Semantic Scholar",
                title=clean_text(item.get("title", "")),
                authors=[author.get("name", "") for author in item.get("authors", []) if author.get("name")],
                abstract=clean_text(item.get("abstract", "") or ""),
                url=item.get("url", ""),
                pdf_url=open_pdf.get("url", "") or "",
                published=str(item.get("year") or ""),
                doi=external_ids.get("DOI", ""),
                source_id=item.get("paperId", ""),
            )
        )
    return results


def dedupe_sources(results: list[ResearchSource]) -> list[ResearchSource]:
    unique: list[ResearchSource] = []
    seen: set[str] = set()
    for result in results:
        if not result.title:
            continue
        key = _dedupe_key(result)
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def _dedupe_key(source: ResearchSource) -> str:
    if source.doi:
        return f"doi:{source.doi.lower().strip()}"
    title = "".join(ch.lower() for ch in source.title if ch.isalnum())
    return f"title:{title}"


def _node_text(node: ET.Element | None) -> str:
    return clean_text("".join(node.itertext())) if node is not None else ""


def _pubmed_year(article_node: ET.Element) -> str:
    for path in ("Journal/JournalIssue/PubDate/Year", "ArticleDate/Year"):
        year = article_node.findtext(path)
        if year:
            return year
    medline_date = article_node.findtext("Journal/JournalIssue/PubDate/MedlineDate")
    return clean_text(medline_date or "")


def _crossref_year(item: dict) -> str:
    for key in ("published-print", "published-online", "issued"):
        date_parts = item.get(key, {}).get("date-parts", [])
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
    return ""
