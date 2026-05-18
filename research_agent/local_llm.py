from __future__ import annotations


def summarize_with_ollama(text: str, *, model: str = "qwen2.5") -> str:
    try:
        import ollama
    except ImportError as exc:
        raise RuntimeError("Install the optional 'ollama' Python package before enabling local LLM summaries.") from exc

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Summarize only the provided research text. Do not invent citations or facts.",
            },
            {
                "role": "user",
                "content": text[:12000],
            },
        ],
    )
    return response["message"]["content"].strip()
