from __future__ import annotations

from io import BytesIO

import requests
import trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader

from research_agent.models import ResearchSource
from research_agent.utils import REQUEST_TIMEOUT_SECONDS, USER_AGENT, clean_text

MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 20000


def enrich_with_document_text(sources: list[ResearchSource], *, max_documents: int = 5) -> list[ResearchSource]:
    enriched: list[ResearchSource] = []
    parsed_count = 0
    for source in sources:
        if parsed_count < max_documents:
            source.full_text = extract_source_text(source)
            if source.full_text:
                parsed_count += 1
        enriched.append(source)
    return enriched


def extract_source_text(source: ResearchSource) -> str:
    if source.pdf_url:
        text = extract_pdf_text(source.pdf_url)
        if text:
            return text
    if source.url:
        return extract_web_text(source.url)
    return ""


def extract_web_text(url: str) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    response.raise_for_status()
    content = _bounded_content(response)
    downloaded = content.decode(response.encoding or "utf-8", errors="ignore")

    extracted = trafilatura.extract(downloaded, url=url, include_comments=False, include_tables=False)
    if extracted:
        return clean_text(extracted)[:MAX_EXTRACTED_CHARS]

    soup = BeautifulSoup(downloaded, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return clean_text(soup.get_text(" "))[:MAX_EXTRACTED_CHARS]


def extract_pdf_text(url: str) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
        allow_redirects=True,
    )
    response.raise_for_status()
    content = _bounded_content(response)
    reader = PdfReader(BytesIO(content))

    pages: list[str] = []
    for page in reader.pages[:8]:
        pages.append(page.extract_text() or "")
    return clean_text(" ".join(pages))[:MAX_EXTRACTED_CHARS]


def _bounded_content(response: requests.Response) -> bytes:
    content = response.content
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError(f"Downloaded document is larger than {MAX_DOWNLOAD_BYTES} bytes.")
    return content
