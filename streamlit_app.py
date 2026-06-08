import html
import sqlite3
from pathlib import Path

import streamlit as st

from src.app import invoke_agent
from src.config import DEFAULT_DB_PATH
from src.tools import generate_and_save_schema, load_schema


st.set_page_config(
    page_title="Olist Insight Agent",
    page_icon="OI",
    layout="wide",
    initial_sidebar_state="expanded",
)


def resolve_db_path() -> Path | None:
    if DEFAULT_DB_PATH.exists():
        return DEFAULT_DB_PATH
    return None


@st.cache_data(show_spinner=False)
def load_catalog(db_path: str) -> tuple[dict, dict]:
    schema_path = Path("schemas") / f"{Path(db_path).stem}_schema.json"
    if schema_path.exists():
        schema = load_schema(str(schema_path))
    else:
        schema = generate_and_save_schema(db_path)

    counts: dict[str, int] = {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    for (table_name,) in cur.fetchall():
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            counts[table_name] = int(cur.fetchone()[0])
        except Exception:
            counts[table_name] = 0
    conn.close()
    return schema, counts


def format_count(value: int) -> str:
    return f"{value:,}"


def render_answer_card(answer: str) -> None:
    st.markdown(
        f"""
        <div class="answer-card">
            <div class="answer-kicker">Final answer</div>
            <div class="answer-copy">{html.escape(answer).replace(chr(10), "<br>")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_panel(result: dict) -> None:
    tabs = st.tabs(["Answer", "SQL", "Results", "Analysis"])

    with tabs[0]:
        render_answer_card(result.get("final_answer", "No answer returned."))
        if result.get("execution_error"):
            st.warning(result["execution_error"])

    with tabs[1]:
        sql = result.get("generated_query")
        if sql:
            st.markdown(
                """
                <div class="sql-shell">
                    <div class="header">Generated SQL</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.code(sql, language="sql")
        else:
            st.info("No SQL query was generated for this run.")

    with tabs[2]:
        rows = result.get("raw_results", [])
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("No rows returned.")

    with tabs[3]:
        if result.get("analysis_runs"):
            for run in result["analysis_runs"]:
                title = run.get("subquestion", "Sub-question")
                with st.expander(title, expanded=False):
                    if run.get("query"):
                        st.write("Query")
                        st.code(run["query"], language="sql")
                    if run.get("error"):
                        st.warning(run["error"])
                    if run.get("results"):
                        st.dataframe(run["results"], use_container_width=True)
        elif result.get("analysis_summary"):
            st.json(result["analysis_summary"])
        else:
            st.info("No investigation trail for this run.")


def render_history(turns: list[dict]) -> None:
    st.markdown("### Conversation")
    st.caption("A chat-style history of the questions you have asked and the answers returned by the agent.")

    if not turns:
        st.info("Ask a question to start the conversation.")
        return

    for turn in turns:
        question = turn.get("question", "")
        result = turn.get("result", {})
        mode = turn.get("mode", "single")

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            st.caption(f"Mode: {mode.title()}")
            render_answer_card(result.get("final_answer", "No answer returned."))
            with st.expander("Evidence", expanded=False):
                if result.get("generated_query"):
                    st.write("SQL")
                    st.code(result["generated_query"], language="sql")
                if result.get("raw_results"):
                    st.write("Result rows")
                    st.dataframe(result["raw_results"], use_container_width=True)
                if result.get("analysis_runs"):
                    st.write("Investigation steps")
                    st.json(result["analysis_runs"])
                elif result.get("analysis_summary"):
                    st.write("Investigation summary")
                    st.json(result["analysis_summary"])


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

    :root {
        --bg: #f4efe7;
        --bg-2: #fbfaf7;
        --ink: #101828;
        --muted: #667085;
        --line: rgba(16, 24, 40, 0.10);
        --shadow: 0 18px 55px rgba(16, 24, 40, 0.10);
    }

    html, body, [class*="css"] {
        font-family: 'Manrope', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 32%),
            radial-gradient(circle at 80% 0%, rgba(194, 65, 12, 0.10), transparent 28%),
            linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 42%, #f2eee6 100%);
        color: var(--ink);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1220 0%, #111827 55%, #111827 100%);
        color: #f8fafc;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc;
    }

    .brand {
        padding: 1rem 1rem 1.15rem;
        border-radius: 1.1rem;
        background: linear-gradient(135deg, rgba(15, 118, 110, 0.28), rgba(37, 99, 235, 0.14));
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 1rem;
    }

    .brand-kicker {
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-size: 0.72rem;
        color: rgba(255, 255, 255, 0.75);
        margin-bottom: 0.35rem;
    }

    .brand-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.6rem;
        line-height: 1.05;
        margin: 0;
    }

    .brand-subtitle {
        font-size: 0.92rem;
        line-height: 1.55;
        color: rgba(255, 255, 255, 0.72);
        margin-top: 0.45rem;
    }

    .hero {
        padding: 1.6rem 1.7rem;
        border-radius: 1.4rem;
        background:
            linear-gradient(135deg, rgba(16, 24, 40, 0.96) 0%, rgba(17, 24, 39, 0.88) 55%, rgba(15, 118, 110, 0.90) 100%);
        color: #ffffff;
        box-shadow: var(--shadow);
        border: 1px solid rgba(255, 255, 255, 0.10);
        position: relative;
        overflow: hidden;
        margin-bottom: 1rem;
    }

    .hero::after {
        content: "";
        position: absolute;
        inset: auto -10% -55% auto;
        width: 16rem;
        height: 16rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        filter: blur(4px);
    }

    .hero-topline {
        display: flex;
        gap: 0.55rem;
        flex-wrap: wrap;
        margin-bottom: 0.8rem;
    }

    .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        border-radius: 999px;
        padding: 0.38rem 0.72rem;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
    }

    .hero h1 {
        font-family: 'Space Grotesk', sans-serif;
        margin: 0;
        font-size: 2.15rem;
        line-height: 1.02;
        letter-spacing: -0.03em;
    }

    .hero p {
        max-width: 58rem;
        margin: 0.75rem 0 0;
        color: rgba(255, 255, 255, 0.84);
        font-size: 1rem;
        line-height: 1.7;
    }

    .stat {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid var(--line);
        border-radius: 1rem;
        padding: 0.95rem 1rem;
        box-shadow: 0 8px 20px rgba(16, 24, 40, 0.05);
    }

    .stat-label {
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .stat-value {
        color: var(--ink);
        font-size: 1.05rem;
        font-weight: 800;
        line-height: 1.25;
    }

    .data-card {
        background: linear-gradient(180deg, #ffffff 0%, #fffdf9 100%);
        border: 1px solid rgba(16, 24, 40, 0.08);
        border-radius: 1.1rem;
        padding: 1rem;
        box-shadow: 0 10px 26px rgba(16, 24, 40, 0.06);
        position: relative;
        overflow: hidden;
        min-height: 230px;
    }

    .data-card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 4px;
        background: linear-gradient(180deg, rgba(15, 118, 110, 1), rgba(194, 65, 12, 1));
    }

    .data-card h3 {
        font-family: 'Space Grotesk', sans-serif;
        margin: 0.65rem 0 0.45rem;
        font-size: 1.08rem;
        color: #0f172a;
    }

    .data-card p {
        margin: 0;
        color: #475467;
        line-height: 1.6;
        font-size: 0.92rem;
    }

    .data-card-top {
        display: flex;
        justify-content: space-between;
        gap: 0.6rem;
        align-items: center;
    }

    .data-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        background: rgba(15, 118, 110, 0.10);
        color: #0f766e;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .data-count {
        color: #344054;
        font-size: 0.8rem;
        font-weight: 800;
    }

    .table-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.85rem;
    }

    .table-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        border-radius: 999px;
        padding: 0.34rem 0.6rem;
        background: #f2f4f7;
        color: #344054;
        font-size: 0.74rem;
        font-weight: 700;
    }

    .table-pill strong {
        color: #101828;
    }

    .quick-question {
        background: linear-gradient(180deg, rgba(255,255,255,0.88), rgba(255,255,255,0.76));
        border: 1px solid rgba(16, 24, 40, 0.08);
        border-radius: 1rem;
        padding: 0.9rem 0.95rem;
        min-height: 132px;
        box-shadow: 0 10px 24px rgba(16, 24, 40, 0.05);
    }

    .quick-question h4 {
        margin: 0 0 0.4rem 0;
        color: #101828;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.98rem;
    }

    .quick-question p {
        margin: 0;
        color: #475467;
        font-size: 0.9rem;
        line-height: 1.55;
    }

    .answer-card {
        background: linear-gradient(180deg, #ffffff 0%, #fffdf9 100%);
        border: 1px solid rgba(16, 24, 40, 0.08);
        border-radius: 1.15rem;
        padding: 1.05rem 1.15rem;
        box-shadow: 0 10px 28px rgba(16, 24, 40, 0.06);
        color: #101828;
        line-height: 1.75;
    }

    .answer-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #0f766e;
        margin-bottom: 0.55rem;
    }

    .answer-copy {
        color: #101828;
        font-size: 0.98rem;
        line-height: 1.8;
        white-space: normal;
    }

    .sql-shell {
        background: #0b1220;
        color: #dbeafe;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 1rem;
        overflow: hidden;
        box-shadow: 0 14px 28px rgba(16, 24, 40, 0.12);
        margin-bottom: 0.5rem;
    }

    .sql-shell .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.8rem 0.95rem;
        background: rgba(255, 255, 255, 0.04);
        border-bottom: 1px solid rgba(255, 255, 255, 0.07);
        color: #cbd5e1;
        font-size: 0.82rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
    }

    .small-note {
        color: var(--muted);
        font-size: 0.88rem;
        line-height: 1.5;
    }

    .soft-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(16, 24, 40, 0.12), transparent);
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "question_input" not in st.session_state:
    st.session_state["question_input"] = "What are the top 5 product categories by number of orders?"
if "mode" not in st.session_state:
    st.session_state["mode"] = "analysis"
if "turns" not in st.session_state:
    st.session_state["turns"] = []
if "latest_result" not in st.session_state:
    st.session_state["latest_result"] = None


db_path = resolve_db_path()
if not db_path:
    st.error("No Olist database could be found. Check data/olist.sqlite/olist.sqlite or demo_data/olist_demo.sqlite.")
    st.stop()

schema, table_counts = load_catalog(str(db_path))
source_label = "Bundled Olist sample" if db_path == DEFAULT_DB_PATH else "Demo Olist sample"


with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-kicker">Commerce intelligence</div>
            <h2 class="brand-title">Olist Insight Agent</h2>
            <div class="brand-subtitle">
                A grounded BI agent for the Olist Brazilian e-commerce dataset.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.radio(
        "Operating mode",
        ["single", "analysis"],
        index=1 if st.session_state["mode"] == "analysis" else 0,
        key="mode",
        help="Single answers are fast. Analysis mode runs a deeper investigation.",
    )

    st.markdown("### Active source")
    st.write(f"**{source_label}**")
    st.caption("This version stays focused on the Olist domain.")


st.markdown(
    """
    <div class="hero">
        <div class="hero-topline">
            <span class="pill">Live SQL agent</span>
            <span class="pill">Olist only</span>
            <span class="pill">Chat + dashboard</span>
        </div>
        <h1>Ask business questions over the Olist dataset and get grounded answers.</h1>
        <p>
            The app loads one trusted commerce dataset first, surfaces the tables and row counts, and then lets you
            ask a question in plain English. The agent chooses tables, writes SQL, validates it, runs it, and explains the result.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


overview_a, overview_b, overview_c, overview_d = st.columns(4)
overview_a.markdown(
    f"""
    <div class="stat">
        <div class="stat-label">Tables loaded</div>
        <div class="stat-value">{len(schema["tables"])}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
overview_b.markdown(
    f"""
    <div class="stat">
        <div class="stat-label">Source</div>
        <div class="stat-value">{html.escape(source_label)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
overview_c.markdown(
    """
    <div class="stat">
        <div class="stat-label">Interface</div>
        <div class="stat-value">Cards plus chat history</div>
    </div>
    """,
    unsafe_allow_html=True,
)
overview_d.markdown(
    """
    <div class="stat">
        <div class="stat-label">Output</div>
        <div class="stat-value">Answer, SQL, rows, analysis</div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
st.markdown("### Detected data")
st.caption("These cards show the data the agent sees before you ask a question.")

preview_cols = st.columns(3)
tables = schema["tables"][:6]
for idx, table in enumerate(tables):
    with preview_cols[idx % 3]:
        count = table_counts.get(table["name"], 0)
        table_list = "".join(
            f'<span class="table-pill">{html.escape(col["name"])} <strong>{html.escape(col["type"] or "TEXT")}</strong></span>'
            for col in table.get("columns", [])[:4]
        )
        st.markdown(
            f"""
            <div class="data-card">
                <div class="data-card-top">
                    <span class="data-badge">Table</span>
                    <span class="data-count">{format_count(count)} rows</span>
                </div>
                <h3>{html.escape(table["name"])}</h3>
                <p>{html.escape(table.get("description", ""))}</p>
                <div class="table-list">{table_list}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with st.expander("Full table inventory", expanded=False):
    inv_cols = st.columns(2)
    for idx, table in enumerate(schema["tables"]):
        col = inv_cols[idx % 2]
        with col:
            st.markdown(
                f"""
                <div class="data-card" style="margin-bottom:0.7rem; min-height:auto;">
                    <div class="data-card-top">
                        <span class="data-badge">Table</span>
                        <span class="data-count">{format_count(table_counts.get(table["name"], 0))} rows</span>
                    </div>
                    <h3>{html.escape(table["name"])}</h3>
                    <p>{html.escape(table.get("description", ""))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
st.markdown("### Suggested questions")
st.caption("These are starters. Click one to fill the question box.")

suggestions = [
    ("What are the top 5 product categories by number of orders?", "Catalog mix"),
    ("Why did orders drop last week?", "Trend investigation"),
    ("Which states have the most delayed deliveries?", "Operations"),
    ("How do review scores change when delivery is late?", "Customer experience"),
    ("Which payment types are used most often?", "Payments"),
    ("What looks unusual in the data this week?", "Analysis mode"),
]

for row in range(2):
    cols = st.columns(3)
    for col_idx in range(3):
        prompt, title = suggestions[row * 3 + col_idx]
        with cols[col_idx]:
            st.markdown(
                f"""
                <div class="quick-question">
                    <h4>{html.escape(title)}</h4>
                    <p>{html.escape(prompt)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Use this", key=f"suggestion_{row}_{col_idx}", use_container_width=True):
                st.session_state["question_input"] = prompt


st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
st.markdown("### Ask your own question")
st.caption("This is the actual question composer. The agent will choose tables and SQL automatically.")

st.text_area(
    "Business question",
    key="question_input",
    height=120,
    label_visibility="collapsed",
    placeholder="Ask about sales trends, delivery delays, customer behavior, categories, payment mix, reviews, or sellers...",
)

composer_left, composer_right = st.columns([0.24, 0.76])
with composer_left:
    ask_clicked = st.button("Ask the agent", type="primary", use_container_width=True)
with composer_right:
    st.markdown(
        """
        <div class="small-note">
        The app loads the Olist source first, then the schema and table counts update automatically.
        </div>
        """,
        unsafe_allow_html=True,
    )


if ask_clicked:
    prompt = st.session_state["question_input"].strip()
    if not prompt:
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Running the agent..."):
            try:
                result = invoke_agent(prompt, mode=st.session_state["mode"])
            except Exception as exc:
                st.error(f"Agent failed: {exc}")
            else:
                st.session_state["latest_result"] = result
                st.session_state["turns"].append(
                    {
                        "question": prompt,
                        "result": result,
                        "mode": st.session_state["mode"],
                    }
                )


latest_result = st.session_state.get("latest_result")
if latest_result:
    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
    st.markdown("### Latest result")
    st.caption("A dashboard-style summary of the most recent agent run.")
    render_result_panel(latest_result)


st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
render_history(st.session_state["turns"])


st.markdown(
    """
    <div class="small-note" style="margin-top: 1.2rem; text-align: center;">
    Built for the Olist Brazilian e-commerce dataset. The first version stays focused on one trusted domain.
    </div>
    """,
    unsafe_allow_html=True,
)
