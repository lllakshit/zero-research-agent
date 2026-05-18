from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from research_agent.pipeline import run_research
from research_agent.planner import DEFAULT_SOURCES


console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Zero-key academic research agent")
    parser.add_argument("query", nargs="*", help="Research query")
    parser.add_argument("--max-results", type=int, default=3, help="Max results per source per search term")
    parser.add_argument("--output-dir", default="outputs", help="Where reports and raw JSON are written")
    parser.add_argument("--sources", nargs="*", default=DEFAULT_SOURCES, help="Sources to use")
    parser.add_argument("--parse-documents", action="store_true", help="Try parsing allowed PDF/web text for top sources")
    parser.add_argument("--use-local-llm", action="store_true", help="Use Ollama for top summaries; off by default")
    parser.add_argument("--ollama-model", default="qwen2.5", help="Ollama model name if local LLM is enabled")
    args = parser.parse_args()

    query = " ".join(args.query).strip() or input("Research query: ").strip()
    console.print("[bold]Running zero-key research agent...[/bold]")

    result = run_research(
        query,
        output_dir=Path(args.output_dir),
        max_results_per_source=args.max_results,
        sources=args.sources,
        parse_documents=args.parse_documents,
        use_local_llm=args.use_local_llm,
        ollama_model=args.ollama_model,
    )

    console.print(f"[green]Found {len(result.sources)} unique sources.[/green]")
    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"- {warning}")

    console.print(f"[green]Raw JSON:[/green] {result.raw_json_path}")
    console.print(f"[green]Markdown:[/green] {result.markdown_path}")
    console.print(f"[green]HTML:[/green] {result.html_path}")
    console.print(f"[green]PDF:[/green] {result.pdf_path}")


if __name__ == "__main__":
    main()
