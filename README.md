# Olist Insight Agent

A natural language SQL agent built with LangGraph that answers business questions 
from the Olist Brazilian E-Commerce dataset in plain English.

## What it does
- Takes a business question in plain English
- Identifies relevant tables from the data model
- Generates SQL query automatically
- Executes against real data
- Returns a plain English insight

## Example
**Question:** What are the top 5 product categories by number of orders?

**Answer:** The top 5 product categories are bed_bath_table (11,115 orders), 
health_beauty (9,670 orders), sports_leisure (8,641 orders), 
furniture_decor (8,334 orders), and computers_accessories (7,827 orders).

## Architecture
User Question → Schema Loader → Question Analyzer → Query Generator 
→ Query Validator → Query Executor → Insight Synthesizer → Plain English Answer

## Tech Stack
- LangGraph — agent framework
- Python 3.11
- SQLite — Olist database
- GitHub Models (GPT-4o) — LLM
- Streamlit — UI (coming soon)

## Setup
1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Add your GitHub token to `.env`: `GITHUB_TOKEN=your_token`
4. Run: `python app.py`

## Streamlit Cloud Deployment
1. Push the repository to GitHub.
2. In Streamlit Community Cloud, choose `streamlit_app.py` as the entrypoint.
3. Add `Github_token` or `GITHUB_TOKEN` in the app secrets.
4. Deploy the app.

Notes:
- The app will use the bundled Olist sample locally when `data/olist.sqlite/olist.sqlite` exists.
- For hosted deployment, the app falls back to the smaller `demo_data/olist_demo.sqlite` bundle.
- Users can also upload their own SQLite database or point to a local SQLite file path.

## Status
- [x] Stage 1 — Natural language to SQL agent (LangGraph + Olist dataset + GPT-4o)
- [ ] Stage 2 — Auto schema generation from live database connection
- [ ] Stage 3 — Agentic Data Analyst (autonomous multi-query investigation)
