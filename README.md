# Olist Insight Agent

An LLM-powered data agent for e-commerce analysis.
It uses LangGraph to ground questions in schema, generate and validate SQL, run multi-step investigations, and explain findings in plain English.

## What The Agent Does
- Reads the available tables and columns from a SQLite source
- Chooses the relevant tables for a user question
- Generates SQL and validates that it is read-only and schema-safe
- Executes the query against the selected source
- Synthesizes the result into a concise business answer
- Escalates to multi-query analysis when a question needs investigation instead of a single lookup

## Why It Is Interesting
Most BI tools are passive: they show charts and wait for a human to interpret them.
This agent is built to act more like an analyst:
it can reason over the data model, ask follow-up questions internally, and return a focused answer with evidence.

## Agent Capabilities
- Schema-grounded table selection
- Query validation before execution
- Source-aware behavior for bundled or user-uploaded SQLite data
- Single-query question answering
- Multi-query analysis mode for trends, comparisons, and root-cause style questions
- Chat-style history with SQL and result transparency

## Example Workflows
**Simple lookup**
- Question: What are the top 5 product categories by number of orders?
- Agent: finds the relevant order and product tables, generates SQL, returns a ranked answer.

**Analyst-style investigation**
- Question: Why did orders drop last week?
- Agent: plans sub-questions, runs multiple SQL queries, compares results, and summarizes the likely drivers.

**Bring your own data**
- Question: Ask the same style of question over an uploaded SQLite file.
- Agent: inspects the uploaded schema, adapts table selection, and answers from that source.

## Architecture
Source Selector -> Schema Loader -> Question Analyzer -> Query Generator -> Query Validator -> Query Executor -> Insight Synthesizer -> Answer

## Tech Stack
- LangGraph - agent orchestration
- Streamlit - UI layer
- Python 3.11
- SQLite - data source
- GitHub Models (GPT-4o) - LLM backend

## How To Run
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

## Data Support
The agent can work with:
- Bundled Olist sample data
- Uploaded SQLite databases
- Local SQLite file paths

For Streamlit Community Cloud, the repo includes a smaller bundled demo database in `demo_data/olist_demo.sqlite` so the deployed app still has a usable default source.

## How To Position It
If you are using this for a portfolio or GitHub profile, describe it as:
- an analyst-style agent for e-commerce data
- a grounded SQL agent with validation and analysis mode
- a source-aware agent that can handle bundled data or user-provided SQLite files

## Project Status
- [x] Data-first agent UI
- [x] Bundled demo database for deployment
- [x] Automatic schema loading for SQLite sources
- [x] Natural language to SQL flow
- [x] Multi-query analysis mode
- [ ] Direct Postgres/MySQL connection support
- [ ] CSV upload support
- [ ] Production auth and multi-user workspace support
