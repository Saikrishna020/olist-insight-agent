import json
import os
import sqlite3
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
try:
    import streamlit as st
except Exception:
    st = None

from .config import DEFAULT_DB_PATH, DEFAULT_MAX_RESULT_ROWS, DEFAULT_MODEL
from .state import OlistAgentState
from .tools import generate_and_save_schema, validate_query

load_dotenv()


def _get_openai_client() -> OpenAI:
    github_token = os.getenv("Github_token") or os.getenv("GITHUB_TOKEN")
    if not github_token and st is not None:
        try:
            github_token = st.secrets.get("Github_token") or st.secrets.get("GITHUB_TOKEN")
        except Exception:
            github_token = None

    if not github_token:
        raise RuntimeError(
            "Missing GitHub/Azure model token. Set Github_token or GITHUB_TOKEN in .env"
        )

    return OpenAI(
        api_key=github_token,
        base_url="https://models.inference.ai.azure.com",
    )


def _get_db_path(state: OlistAgentState) -> str:
    return state.get("db_path") or str(DEFAULT_DB_PATH)


def _schema_table_summary(schema: dict) -> str:
    lines = []
    for table in schema.get("tables", []):
        lines.append(f"- {table['name']}: {table.get('description', '')}")
    return "\n".join(lines)


def _schema_for_tables(schema: dict, tables: list[str]) -> list[dict]:
    selected = []
    wanted = {table.lower() for table in tables}
    for table in schema.get("tables", []):
        if table["name"].lower() in wanted:
            selected.append(table)
    return selected or schema.get("tables", [])


def _parse_json_array(value: str, fallback: list) -> list:
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return fallback


def _generate_relevant_tables(question: str, schema: dict) -> list[str]:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        max_tokens=500,
        messages=[
            {
                "role": "system",
                "content": "You are a data analyst. Given a question and available tables, identify which tables are needed to answer the question. Return ONLY a JSON array of table names. Example: [\"orders\", \"customers\"]",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nAvailable tables:\n{_schema_table_summary(schema)}",
            },
        ],
    )

    raw_response = response.choices[0].message.content.strip()
    fallback = [table["name"] for table in schema.get("tables", [])]
    return _parse_json_array(raw_response, fallback)


def _generate_sql_query(
    question: str,
    schema: dict,
    relevant_tables: Optional[list[str]] = None,
    retry_feedback: str = "",
) -> str:
    client = _get_openai_client()
    relevant_schema = (
        _schema_for_tables(schema, relevant_tables or []) if relevant_tables else schema["tables"]
    )
    schema_context = json.dumps(relevant_schema, indent=2)

    retry_note = ""
    if retry_feedback:
        retry_note = f"\n\nPrevious query failed with this error: {retry_feedback}\nFix the error."

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        max_tokens=500,
        messages=[
            {
                "role": "system",
                "content": "You are a SQL expert. Generate a SQLite SQL query to answer the question. Return ONLY the SQL query, no explanation, no markdown, no backticks.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nSchema:\n{schema_context}{retry_note}",
            },
        ],
    )

    return response.choices[0].message.content.strip()


def _execute_sql(query: str, db_path: str) -> tuple[list[dict], str]:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)

        if cursor.description is None:
            conn.close()
            return [], "Query did not return a result set"

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchmany(DEFAULT_MAX_RESULT_ROWS)
        conn.close()

        results = [dict(zip(columns, row)) for row in rows]
        return results, ""
    except Exception as e:
        return [], str(e)


def schema_loader_node(state: OlistAgentState) -> dict:
    schema = generate_and_save_schema(_get_db_path(state))
    return {"schema": schema}


def question_analyzer_node(state: OlistAgentState) -> dict:
    schema = state["schema"]
    question = state["question"]

    try:
        relevant_tables = _generate_relevant_tables(question, schema)
    except Exception:
        relevant_tables = [table["name"] for table in schema["tables"]]

    return {"relevant_tables": relevant_tables}


def query_generator_node(state: OlistAgentState) -> dict:
    schema = state["schema"]
    question = state["question"]
    relevant_tables = state.get("relevant_tables", [])
    retry_feedback = state.get("retry_feedback", "")

    query = _generate_sql_query(
        question=question,
        schema=schema,
        relevant_tables=relevant_tables,
        retry_feedback=retry_feedback,
    )
    return {"generated_query": query}


def query_validator_node(state: OlistAgentState) -> dict:
    query = state.get("generated_query", "")
    schema = state["schema"]
    retry_count = state.get("retry_count", 0)

    result = validate_query(query, schema)

    if not result["is_valid"]:
        return {
            "is_valid": False,
            "validation_error": result["error"],
            "retry_feedback": result["error"],
            "retry_count": retry_count + 1,
        }

    return {
        "is_valid": True,
        "validation_error": "",
        "retry_feedback": "",
        "retry_count": retry_count,
    }


def query_executor_node(state: OlistAgentState) -> dict:
    query = state.get("generated_query", "")
    db_path = _get_db_path(state)

    if not state.get("is_valid"):
        return {"raw_results": [], "execution_error": "Query was not valid"}

    results, execution_error = _execute_sql(query, db_path)
    if execution_error:
        return {"raw_results": [], "execution_error": execution_error, "retry_feedback": execution_error}

    return {"raw_results": results, "execution_error": ""}


def _plan_analysis_questions(question: str, schema: dict) -> list[str]:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        max_tokens=500,
        messages=[
            {
                "role": "system",
                "content": "You are a senior analytics strategist. Break the user's business question into 3 focused SQL-friendly investigation steps that can help explain the result. Return ONLY a JSON array of strings.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nAvailable tables:\n{_schema_table_summary(schema)}",
            },
        ],
    )

    raw_response = response.choices[0].message.content.strip()
    fallback = [
        f"What is the time trend for {question.lower()}?",
        f"Which segment or category contributes most to {question.lower()}?",
        f"What outliers or exceptions explain {question.lower()}?",
    ]
    return _parse_json_array(raw_response, fallback)


def analysis_planner_node(state: OlistAgentState) -> dict:
    schema = state["schema"]
    question = state["question"]

    try:
        analysis_questions = _plan_analysis_questions(question, schema)
    except Exception:
        analysis_questions = [
            f"What is the time trend for {question.lower()}?",
            f"Which segment or category contributes most to {question.lower()}?",
            f"What outliers or exceptions explain {question.lower()}?",
        ]

    return {"analysis_questions": analysis_questions}


def analysis_executor_node(state: OlistAgentState) -> dict:
    schema = state["schema"]
    db_path = _get_db_path(state)
    analysis_questions = state.get("analysis_questions", [])

    runs = []
    for subquestion in analysis_questions:
        try:
            relevant_tables = _generate_relevant_tables(subquestion, schema)
        except Exception:
            relevant_tables = [table["name"] for table in schema["tables"]]

        try:
            query = _generate_sql_query(
                question=subquestion,
                schema=schema,
                relevant_tables=relevant_tables,
            )
        except Exception as e:
            runs.append(
                {
                    "subquestion": subquestion,
                    "query": "",
                    "results": [],
                    "error": str(e),
                }
            )
            continue

        validation = validate_query(query, schema)
        if not validation["is_valid"]:
            try:
                query = _generate_sql_query(
                    question=subquestion,
                    schema=schema,
                    relevant_tables=relevant_tables,
                    retry_feedback=validation["error"],
                )
                validation = validate_query(query, schema)
            except Exception as e:
                runs.append(
                    {
                        "subquestion": subquestion,
                        "query": query,
                        "results": [],
                        "error": str(e),
                    }
                )
                continue

        if not validation["is_valid"]:
            runs.append(
                {
                    "subquestion": subquestion,
                    "query": query,
                    "results": [],
                    "error": validation["error"],
                }
            )
            continue

        results, execution_error = _execute_sql(query, db_path)
        runs.append(
            {
                "subquestion": subquestion,
                "query": query,
                "results": results,
                "error": execution_error,
            }
        )

    summary_source = json.dumps(runs, indent=2)
    return {"analysis_runs": runs, "raw_results": runs, "analysis_summary": summary_source}


def insight_synthesizer_node(state: OlistAgentState) -> dict:
    question = state["question"]

    if state.get("analysis_runs"):
        analysis_runs = state.get("analysis_runs", [])
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior business analyst. Given the investigation steps, their queries, and results, synthesize a concise root-cause style answer with key findings and a recommendation. Keep it to 4-6 sentences maximum.",
                },
                {
                    "role": "user",
                    "content": f"Original question: {question}\n\nInvestigation results:\n{json.dumps(analysis_runs, indent=2)}",
                },
            ],
        )

        answer = response.choices[0].message.content.strip()
        return {"final_answer": answer, "analysis_summary": json.dumps(analysis_runs, indent=2)}

    raw_results = state.get("raw_results", [])
    execution_error = state.get("execution_error", "")

    if execution_error or not raw_results:
        return {"final_answer": f"Could not retrieve data. Error: {execution_error}"}

    client = _get_openai_client()
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        max_tokens=500,
        messages=[
            {
                "role": "system",
                "content": "You are a business analyst. Given a question and raw data results, write a clear plain English insight. Be specific with numbers. Keep it to 2-3 sentences maximum.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nData: {json.dumps(raw_results, indent=2)}",
            },
        ],
    )

    answer = response.choices[0].message.content.strip()
    return {"final_answer": answer}
