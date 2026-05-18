# Zero-Key Research Agent

A local research agent that uses public academic sources and creates Markdown, HTML, PDF, and raw JSON outputs without paid LLM/API keys.

## What It Does

- Creates a search plan from your query.
- Searches arXiv, PubMed, Crossref, and Semantic Scholar.
- Saves raw metadata and abstracts as JSON.
- Deduplicates papers by DOI or normalized title.
- Optionally parses allowed PDFs/web pages.
- Summarizes with local extractive Python logic by default.
- Optionally uses Ollama only if you enable it.
- Writes a structured report with citations and warnings.

## What It Avoids

- No OpenAI keys.
- No Groq keys.
- No OpenRouter keys.
- No Google Scholar scraping.
- No IEEE scraping.
- No random aggressive scraping.

## Setup

```powershell
cd F:\automations\research-agent-zero-key
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run CLI

```powershell
cd F:\automations\research-agent-zero-key
.\.venv\Scripts\python.exe cli.py "recent advancements in large language models 2023 2024" --max-results 2
```

Reports are written to `outputs/`.

## Run UI

```powershell
cd F:\automations\research-agent-zero-key
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501
```

Then open:

```text
http://localhost:8501
```

## Deploy Free

The easiest free deployment for this app is Streamlit Community Cloud.

### Files Needed

- `streamlit_app.py`
- `requirements.txt`
- `research_agent/`
- `README.md`

### Deploy Steps

1. Push this repository to GitHub.
2. Sign in to Streamlit Community Cloud.
3. Create a new app from the GitHub repo.
4. Set the app entry point to `streamlit_app.py`.
5. Deploy.

### Cloud Notes

- Leave `Use Ollama local model` off in the cloud.
- Leave `Parse allowed PDFs/web pages` off unless you expect slower runs.
- Uploaded PDFs still work because parsing happens locally inside the app runtime.
- The app uses public endpoints only and does not require OpenAI, Groq, or OpenRouter keys.

## Recommended Settings

- Keep `Use Ollama local model` unchecked unless you want heavier local model summaries.
- Keep `Parse allowed PDFs/web pages` unchecked for faster runs.
- Start with `Max results per source/search term` set to `2` or `3`.

## Agent Modules

- `research_agent/planner.py`: creates search terms and source plan.
- `research_agent/collectors.py`: collects public metadata and abstracts.
- `research_agent/parser.py`: parses allowed PDFs/web pages when enabled.
- `research_agent/summarizer.py`: creates extractive summaries.
- `research_agent/writer.py`: creates Markdown, HTML, and PDF reports.
- `research_agent/reviewer.py`: checks weak metadata, missing links, missing summaries.
- `research_agent/pipeline.py`: coordinates the full agent run.
