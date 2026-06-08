# Olist Insight Agent

An interactive decision-intelligence app for e-commerce analysis.
Built with LangGraph and Streamlit, it can answer business questions over the
Olist Brazilian E-Commerce dataset or a user-provided SQLite database.

## Why It Exists
Most dashboards are passive. This app turns data exploration into a guided workflow:
it shows the dataset first, helps the user understand what is available, and then
lets them ask business questions in plain English.

## Core Features
- Data-first UI with table cards, row counts, and sample question prompts
- Bundled Olist sample for instant use
- Upload a SQLite file or point to a local SQLite path
- Automatic schema discovery and cache-backed schema loading
- Natural language to SQL query generation
- Multi-query analysis mode for deeper investigation
- Dashboard-style results with SQL, rows, and a chat-like history

## Example
**Question:** What are the top 5 product categories by number of orders?

**Answer:** The top 5 product categories are bed_bath_table (11,115 orders), health_beauty (9,670 orders), sports_leisure (8,641 orders), furniture_decor (8,334 orders), and computers_accessories (7,827 orders).

## Architecture
Source Selector -> Schema Loader -> Question Analyzer -> Query Generator -> Query Validator -> Query Executor -> Insight Synthesizer -> Dashboard UI

## Tech Stack
- LangGraph - agent orchestration
- Streamlit - UI
- Python 3.11
- SQLite - data source
- GitHub Models (GPT-4o) - LLM

## Run Locally
1. Clone the repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Add your token to `.env`:
   ```env
   Github_token=your_token
   ```
   or
   ```env
   GITHUB_TOKEN=your_token
   ```
4. Start the app:
   ```bash
   streamlit run streamlit_app.py
   ```

## Data Sources
The app supports:
- Bundled Olist sample data
- Uploaded SQLite databases
- Local SQLite file paths

For Streamlit Community Cloud, the app falls back to the smaller demo database
in `demo_data/olist_demo.sqlite` so the hosted version has a usable default source.

## Streamlit Cloud Deployment
1. Push the repository to GitHub.
2. In Streamlit Community Cloud, choose `streamlit_app.py` as the entrypoint.
3. Add `Github_token` or `GITHUB_TOKEN` in the app secrets.
4. Deploy the app.

## Project Status
- [x] Streamlit UI with data-source selection
- [x] Bundled demo database for hosted deployment
- [x] Automatic schema loading for SQLite sources
- [x] Natural language to SQL flow
- [x] Multi-query analysis mode
- [ ] Direct Postgres/MySQL connection support
- [ ] CSV upload support
- [ ] Production auth and multi-user workspace support

## Notes
- The full local Olist database is used when `data/olist.sqlite/olist.sqlite` exists.
- If that database is unavailable, the app falls back to `demo_data/olist_demo.sqlite`.
- Uploaded SQLite files are copied to a temporary local folder for inspection.
