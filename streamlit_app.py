from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from research_agent.models import ResearchSource
from research_agent.pipeline import run_research
from research_agent.planner import DEFAULT_SOURCES
from research_agent.storage import bootstrap_reports_from_outputs, get_report, list_reports
from research_agent.utils import clean_text


ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT_DIR / "outputs"
DB_PATH = OUTPUT_DIR / "reports.sqlite3"
MAX_UPLOADED_PDF_BYTES = 50 * 1024 * 1024
MAX_UPLOADED_TEXT_CHARS = 60000

st.set_page_config(page_title="Zero Research Agent", page_icon=":mag:", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --zero-ink: #0f1730;
            --zero-muted: #55617b;
            --zero-line: #d8e0ef;
            --zero-bg: #f4f7ff;
            --zero-card: #ffffff;
            --zero-primary: #4f5cf5;
            --zero-primary-2: #7a4bf4;
            --zero-primary-soft: rgba(79, 92, 245, .12);
            --zero-surface: #f9fbff;
            --zero-surface-strong: #edf2ff;
            --zero-accent: #eff2ff;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 25% 0%, rgba(79, 92, 245, .10), transparent 34rem),
                linear-gradient(180deg, #ffffff 0%, var(--zero-bg) 100%);
            color: var(--zero-ink);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--zero-line);
        }

        [data-testid="stSidebar"], [data-testid="stSidebar"] * {
            color: var(--zero-ink) !important;
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: var(--zero-ink);
        }

        .block-container {
            max-width: 1220px;
            padding: 2rem 2rem 4rem;
        }

        .zero-brand {
            display: flex;
            align-items: center;
            gap: .75rem;
            margin: .25rem 0 1.75rem;
        }

        .zero-mark {
            width: 38px;
            height: 38px;
            border-radius: 14px;
            position: relative;
            box-shadow: 0 16px 30px rgba(79, 92, 245, .22);
            flex: none;
            background: linear-gradient(135deg, var(--zero-primary), var(--zero-primary-2));
            display: block;
        }

        .zero-mark-ring {
            position: absolute;
            inset: 8px;
            border: 4px solid #ffffff;
            border-radius: 999px;
            box-sizing: border-box;
        }

        .zero-mark-slash {
            position: absolute;
            left: 10px;
            top: 8px;
            width: 22px;
            height: 4px;
            background: #ffffff;
            border-radius: 999px;
            transform: rotate(52deg);
            transform-origin: center;
        }

        .zero-title {
            font-weight: 850;
            line-height: 1.05;
            color: var(--zero-ink);
        }

        .zero-hero {
            margin-bottom: 1.5rem;
        }

        .zero-hero h1 {
            font-size: clamp(2.2rem, 5vw, 4.4rem);
            line-height: .96;
            letter-spacing: -.065em;
            margin: 0 0 .75rem;
            color: var(--zero-ink);
        }

        .zero-gradient {
            background: linear-gradient(92deg, var(--zero-ink), var(--zero-primary) 50%, var(--zero-primary-2));
            -webkit-background-clip: text;
            color: transparent;
        }

        .zero-hero p {
            max-width: 780px;
            color: var(--zero-muted);
            font-size: 1.08rem;
            line-height: 1.75;
            margin: 0;
        }

        .zero-card {
            border: 1px solid var(--zero-line);
            border-radius: 18px;
            background: rgba(255, 255, 255, .96);
            padding: 1.25rem;
            box-shadow: 0 18px 48px rgba(24, 36, 78, .07);
        }

        .zero-card h3 {
            color: var(--zero-ink);
            font-size: 1.04rem;
            font-weight: 820;
            margin: 0 0 .8rem;
        }

        .zero-steps {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .75rem;
            margin: 1.2rem 0 1.35rem;
        }

        .zero-step {
            border: 1px solid var(--zero-line);
            border-radius: 14px;
            background: #fff;
            padding: .9rem;
        }

        .zero-step strong {
            display: block;
            color: var(--zero-ink);
            margin-bottom: .25rem;
        }

        .zero-step span {
            color: var(--zero-muted);
            font-size: .88rem;
            line-height: 1.45;
        }

        .zero-step-num {
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border-radius: 999px;
            color: #fff;
            background: linear-gradient(135deg, var(--zero-primary), var(--zero-primary-2));
            font-weight: 800;
            margin-bottom: .55rem;
        }

        .zero-upload-note {
            color: var(--zero-muted);
            font-size: .9rem;
            line-height: 1.55;
            margin-top: .45rem;
        }

        .zero-status {
            border: 1px solid var(--zero-line);
            border-radius: 14px;
            padding: .9rem;
            background: var(--zero-surface);
            color: var(--zero-muted);
            font-size: .92rem;
        }

        .zero-output-file {
            border: 1px solid var(--zero-line);
            border-radius: 12px;
            padding: .8rem;
            background: var(--zero-surface);
            font-weight: 760;
            color: var(--zero-ink);
        }

        .zero-report-card {
            border: 1px solid var(--zero-line);
            border-radius: 16px;
            background: var(--zero-surface);
            padding: .9rem;
            margin-top: .75rem;
        }

        .zero-report-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: .8rem;
        }

        .zero-report-title {
            color: var(--zero-ink);
            font-weight: 820;
            font-size: .95rem;
            line-height: 1.35;
        }

        .zero-report-meta {
            color: var(--zero-muted);
            font-size: .8rem;
            margin-top: .3rem;
            line-height: 1.45;
        }

        .zero-report-chip {
            color: var(--zero-primary);
            background: var(--zero-accent);
            border: 1px solid rgba(79, 92, 245, .18);
            border-radius: 999px;
            padding: .2rem .55rem;
            font-size: .72rem;
            font-weight: 800;
            white-space: nowrap;
        }

        .zero-report-actions {
            display: grid;
            gap: .55rem;
            margin-top: .75rem;
        }

        .zero-report-viewer {
            border: 1px solid var(--zero-line);
            border-radius: 18px;
            background: #fff;
            padding: 1rem 1.1rem;
            box-shadow: 0 16px 36px rgba(24, 36, 78, .06);
        }

        .stButton > button {
            min-height: 46px;
            border-radius: 12px;
            font-weight: 800;
            color: #ffffff !important;
            border: 0 !important;
            background: linear-gradient(135deg, var(--zero-primary), var(--zero-primary-2)) !important;
            box-shadow: 0 14px 26px rgba(79, 92, 245, .24);
            transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
        }

        .stButton > button:hover {
            filter: brightness(1.02);
            box-shadow: 0 18px 30px rgba(79, 92, 245, .28);
            transform: translateY(-1px);
        }

        .stButton > button:active {
            transform: translateY(0);
        }

        .stTextArea textarea {
            border-radius: 14px;
            border: 1px solid var(--zero-line) !important;
            background: var(--zero-surface) !important;
            color: var(--zero-ink) !important;
            box-shadow: none !important;
        }

        .stTextArea textarea::placeholder {
            color: #8893ab !important;
        }

        [data-testid="stFileUploader"] {
            background: var(--zero-surface);
            border: 1px solid var(--zero-line);
            border-radius: 16px;
            padding: .7rem .8rem .9rem;
        }

        [data-testid="stFileUploader"] button {
            border-radius: 12px !important;
            color: #ffffff !important;
            background: linear-gradient(135deg, var(--zero-primary), var(--zero-primary-2)) !important;
            border: 0 !important;
            box-shadow: 0 12px 22px rgba(79, 92, 245, .22);
        }

        [data-testid="stFileUploader"] section {
            color: var(--zero-muted);
        }

        [data-testid="stMultiSelect"] [data-baseweb="select"],
        [data-testid="stTextInput"] input,
        [data-testid="stSlider"] {
            background: var(--zero-surface) !important;
            border-color: var(--zero-line) !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] {
            background: var(--zero-surface) !important;
            border: 1px solid var(--zero-line) !important;
            border-radius: 14px !important;
            min-height: 46px !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] input {
            color: var(--zero-ink) !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] input::placeholder {
            color: #8893ab !important;
        }

        [data-testid="stSidebar"] [data-baseweb="select"] svg {
            fill: var(--zero-muted) !important;
        }

        [data-baseweb="tag"] {
            background: var(--zero-primary) !important;
            color: #ffffff !important;
            border-radius: 999px !important;
        }

        [data-baseweb="tag"] span {
            color: #ffffff !important;
        }

        [data-baseweb="tag"] button {
            color: #ffffff !important;
        }

        @media (max-width: 900px) {
            .block-container {
                padding: 1rem .9rem 3rem;
            }

            .zero-hero h1 {
                font-size: 2.1rem;
                letter-spacing: -.04em;
            }

            .zero-hero p {
                font-size: .95rem;
            }

            .zero-steps {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .zero-card {
                padding: 1rem;
                border-radius: 16px;
            }
        }

        @media (max-width: 520px) {
            .zero-steps {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def zero_logo_svg() -> str:
    return '<span class="zero-mark-ring"></span><span class="zero-mark-slash"></span>'


def parse_uploaded_pdfs(uploaded_files) -> tuple[list[ResearchSource], list[str]]:
    parsed_sources: list[ResearchSource] = []
    warnings: list[str] = []

    for uploaded_file in uploaded_files or []:
        if uploaded_file.size > MAX_UPLOADED_PDF_BYTES:
            warnings.append(f"{uploaded_file.name} was skipped because it is larger than 50MB.")
            continue

        try:
            reader = PdfReader(BytesIO(uploaded_file.getvalue()))
            page_text = []
            for page in reader.pages[:30]:
                page_text.append(page.extract_text() or "")
            text = clean_text(" ".join(page_text))[:MAX_UPLOADED_TEXT_CHARS]
        except (PdfReadError, OSError, UnicodeDecodeError, ValueError) as exc:
            warnings.append(f"{uploaded_file.name} could not be parsed: {exc}")
            continue

        if not text:
            warnings.append(f"{uploaded_file.name} did not contain selectable text.")
            continue

        parsed_sources.append(
            ResearchSource(
                source="Uploaded PDF",
                title=Path(uploaded_file.name).stem.replace("_", " ").replace("-", " ").title(),
                authors=[],
                abstract=text[:3000],
                full_text=text,
                source_id=uploaded_file.name,
            )
        )

    return parsed_sources, warnings


def fallback_query(query: str, uploaded_files) -> str:
    if query.strip():
        return query.strip()
    if uploaded_files:
        return Path(uploaded_files[0].name).stem.replace("_", " ").replace("-", " ").strip()
    return ""


def sidebar_controls():
    st.sidebar.markdown(
        """
        <div class="zero-brand">
            <div class="zero-mark">""" + zero_logo_svg() + """</div>
            <div class="zero-title">Zero<br>Research Agent</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.header("Settings")
    selected_sources = st.sidebar.multiselect(
        "Public sources",
        DEFAULT_SOURCES,
        default=DEFAULT_SOURCES,
        help="All selected sources use free public endpoints.",
    )
    max_results = st.sidebar.slider("Results per source/search term", min_value=1, max_value=10, value=3)
    parse_documents = st.sidebar.checkbox(
        "Also parse public PDFs/web pages",
        value=False,
        help="Slower. This is separate from uploaded PDFs, which are always parsed locally.",
    )
    use_local_llm = st.sidebar.checkbox(
        "Use Ollama local model",
        value=False,
        help="Off by default because it can make the PC heavy.",
    )
    ollama_model = st.sidebar.text_input("Ollama model", value="qwen2.5", disabled=not use_local_llm)
    st.sidebar.markdown(
        """
        <div class="zero-status">
            <strong>Status:</strong> Ready<br>
            No paid API keys are used.
        </div>
        """,
        unsafe_allow_html=True,
    )
    return selected_sources, max_results, parse_documents, use_local_llm, ollama_model


def format_created_at(value: str) -> str:
    return value.replace("T", " ").replace("+00:00", " UTC")


def render_recent_reports(reports) -> None:
    if not reports:
        st.caption("No reports generated yet.")
        return

    for report in reports:
        st.markdown(
            f"""
            <div class="zero-report-card">
                <div class="zero-report-head">
                    <div>
                        <div class="zero-report-title">{escape(report.query)}</div>
                        <div class="zero-report-meta">{escape(format_created_at(report.created_at))} | {report.source_count} sources | {report.warning_count} warnings</div>
                    </div>
                    <div class="zero-report-chip">Saved</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cols = st.columns(5)
        if cols[0].button("View", key=f"view-{report.report_id}", use_container_width=True):
            st.session_state.active_report_id = report.report_id
            st.rerun()
        cols[1].download_button("MD", report.markdown_content, file_name=f"{report.report_id}.md", key=f"md-{report.report_id}", use_container_width=True)
        cols[2].download_button("HTML", report.html_content, file_name=f"{report.report_id}.html", key=f"html-{report.report_id}", use_container_width=True)
        cols[3].download_button("PDF", report.pdf_bytes, file_name=f"{report.report_id}.pdf", key=f"pdf-{report.report_id}", use_container_width=True)
        cols[4].download_button("JSON", report.raw_json_content, file_name=f"{report.report_id}-raw.json", key=f"json-{report.report_id}", use_container_width=True)


def render_selected_report(report) -> None:
    if report is None:
        st.caption("Click View on a report to open it here.")
        return

    st.markdown(
        f"""
        <div class="zero-report-viewer">
            <div class="zero-report-title">{escape(report.query)}</div>
            <div class="zero-report-meta">{escape(format_created_at(report.created_at))} | {report.source_count} sources | {report.warning_count} warnings</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(report.markdown_content)


inject_css()
bootstrap_reports_from_outputs(OUTPUT_DIR, DB_PATH)
if "recent_reports_cache" not in st.session_state or not st.session_state.recent_reports_cache:
    st.session_state.recent_reports_cache = list_reports(DB_PATH, limit=6)
if "active_report_id" not in st.session_state:
    st.session_state.active_report_id = st.session_state.recent_reports_cache[0].report_id if st.session_state.recent_reports_cache else ""
selected_sources, max_results, parse_documents, use_local_llm, ollama_model = sidebar_controls()

st.markdown(
    """
    <section class="zero-hero">
        <h1>Zero <span class="zero-gradient">Research Agent</span></h1>
        <p>Upload a PDF, search public academic sources, summarize locally, and generate Markdown, HTML, PDF, and JSON reports without paid API credits.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="zero-steps">
        <div class="zero-step"><div class="zero-step-num">1</div><strong>Upload or Ask</strong><span>Add PDFs and/or enter a research query.</span></div>
        <div class="zero-step"><div class="zero-step-num">2</div><strong>Collect</strong><span>Search arXiv, PubMed, Crossref, and Semantic Scholar.</span></div>
        <div class="zero-step"><div class="zero-step-num">3</div><strong>Summarize</strong><span>Use extractive local summaries by default.</span></div>
        <div class="zero-step"><div class="zero-step-num">4</div><strong>Report</strong><span>Create downloadable cited reports.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

main_col, side_col = st.columns([1.75, 1], gap="large")

with main_col:
    with st.container(border=True):
        st.subheader("1. Upload PDF")
        uploaded_files = st.file_uploader(
            "Upload one or more PDFs to parse locally",
            type=["pdf"],
            accept_multiple_files=True,
            help="Uploaded PDFs are parsed on this PC with pypdf. No API key is used.",
        )
        st.markdown('<p class="zero-upload-note">PDF upload is optional. If you upload a PDF without a query, the filename is used as the search query.</p>', unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("2. Search query")
        query = st.text_area(
            "What should the agent research?",
            placeholder="Example: recent advancements in large language models 2023 2024",
            height=120,
        )
        effective_query = fallback_query(query, uploaded_files)
        can_run = bool(effective_query and selected_sources)
        run_clicked = st.button(
            "Create Research Report",
            type="primary",
            use_container_width=True,
            disabled=not can_run,
        )
        if not can_run:
            st.caption("Enter a query or upload a PDF to enable the report button.")

with side_col:
    with st.container(border=True):
        st.subheader("How it works")
        st.markdown(
            """
            - Uploaded PDFs are parsed locally.
            - Public-source search uses free endpoints only.
            - Summaries are extractive unless Ollama is enabled.
            - Reports include source warnings when metadata is weak.
            """
        )

    recent_reports_box = st.container(border=True)

if run_clicked:
    with st.status("Running research agent...", expanded=True) as status:
        try:
            status.write("Parsing uploaded PDFs.")
            uploaded_sources, upload_warnings = parse_uploaded_pdfs(uploaded_files)
            for warning in upload_warnings:
                st.warning(warning)

            if uploaded_files and not uploaded_sources:
                raise ValueError("No uploaded PDF text could be parsed. Try a selectable-text PDF or enter a query.")

            status.write("Planning search terms.")
            status.write("Collecting metadata and abstracts from public sources.")
            if parse_documents:
                status.write("Parsing allowed public documents for the first matching sources.")
            status.write("Creating summaries and reports.")

            result = run_research(
                effective_query,
                output_dir=OUTPUT_DIR,
                max_results_per_source=max_results,
                sources=selected_sources,
                local_sources=uploaded_sources,
                parse_documents=parse_documents,
                use_local_llm=use_local_llm,
                ollama_model=ollama_model,
            )
            st.session_state.active_report_id = result.report_id
            latest_report = get_report(DB_PATH, result.report_id)
            if latest_report is not None:
                cached = [report for report in st.session_state.recent_reports_cache if report.report_id != latest_report.report_id]
                st.session_state.recent_reports_cache = [latest_report, *cached][:6]
        except (RuntimeError, ValueError, OSError, requests.RequestException, PdfReadError) as exc:
            status.update(label="Research failed", state="error")
            st.error(str(exc))
            st.stop()

        status.update(label="Research report created", state="complete")

    st.success(f"Report created with {len(result.sources)} source(s).")

    if result.warnings:
        with st.expander("Warnings and quality notes", expanded=True):
            for warning in result.warnings:
                st.warning(warning)

    st.subheader("Downloads")
    col1, col2, col3, col4 = st.columns(4)
    col1.download_button("Markdown", result.markdown_path.read_bytes(), file_name=result.markdown_path.name, use_container_width=True)
    col2.download_button("HTML", result.html_path.read_bytes(), file_name=result.html_path.name, use_container_width=True)
    col3.download_button("PDF", result.pdf_path.read_bytes(), file_name=result.pdf_path.name, use_container_width=True)
    col4.download_button("Raw JSON", result.raw_json_path.read_bytes(), file_name=result.raw_json_path.name, use_container_width=True)

with recent_reports_box:
    st.subheader("Recent reports")
    render_recent_reports(st.session_state.recent_reports_cache)

st.subheader("View report")
active_report = get_report(DB_PATH, st.session_state.active_report_id) if st.session_state.active_report_id else None
render_selected_report(active_report)
