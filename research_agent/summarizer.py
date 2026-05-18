from __future__ import annotations

import re
from collections import Counter

from research_agent.models import ResearchSource
from research_agent.utils import clean_text

STOPWORDS = {
    "about", "after", "also", "among", "and", "are", "been", "being", "between",
    "both", "can", "could", "from", "have", "into", "more", "most", "our",
    "over", "paper", "research", "such", "that", "the", "their", "these",
    "this", "through", "using", "were", "with", "within", "without",
}


def summarize_sources(sources: list[ResearchSource], *, max_sentences: int = 3) -> list[ResearchSource]:
    for source in sources:
        text = source.full_text or source.abstract
        source.summary = summarize_text(text, max_sentences=max_sentences)
    return sources


def summarize_text(text: str, *, max_sentences: int = 3) -> str:
    text = clean_text(text)
    if not text:
        return "No abstract or full-text summary was available from the public source."

    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    word_scores = build_word_scores(text)
    ranked = sorted(
        sentences,
        key=lambda sentence: score_sentence(sentence, word_scores),
        reverse=True,
    )
    selected = set(ranked[:max_sentences])
    return " ".join(sentence for sentence in sentences if sentence in selected)


def build_executive_summary(query: str, sources: list[ResearchSource]) -> str:
    if not sources:
        return f"No public academic sources were found for '{query}'. Try a broader query."

    source_names = sorted({source.source for source in sources})
    years = sorted({source.published for source in sources if source.published}, reverse=True)
    year_text = f" Years represented include {', '.join(years[:5])}." if years else ""
    return (
        f"The agent found {len(sources)} unique public sources for '{query}' from "
        f"{', '.join(source_names)}.{year_text} The summaries below are extractive, "
        "meaning they are built from source abstracts or allowed full text without paid LLM APIs."
    )


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]


def build_word_scores(text: str) -> Counter[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", text.lower())
    return Counter(word for word in words if word not in STOPWORDS)


def score_sentence(sentence: str, word_scores: Counter[str]) -> int:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", sentence.lower())
    if not words:
        return 0
    return sum(word_scores[word] for word in words) // max(1, len(words))
