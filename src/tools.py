import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
try:
    import streamlit as st
except Exception:
    st = None

from .config import DEFAULT_MODEL

load_dotenv()

READ_ONLY_PREFIXES = ("select", "with")
BLOCKED_SQL_KEYWORDS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "attach",
    "detach",
    "pragma",
    "vacuum",
)


def _get_token() -> Optional[str]:
    token = os.getenv("Github_token") or os.getenv("GITHUB_TOKEN")
    if token:
        return token

    if st is not None:
        try:
            return st.secrets.get("Github_token") or st.secrets.get("GITHUB_TOKEN")
        except Exception:
            return None

    return None


def _get_openai_client() -> Optional[OpenAI]:
    token = _get_token()
    if not token:
        return None

    return OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )


def load_schema(schema_path: str) -> dict:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_query(query: str) -> str:
    return query.strip().rstrip(";").strip()


def _extract_table_references(query: str) -> list[str]:
    refs = re.findall(r"\b(?:from|join)\s+([A-Za-z_][\w.]*)", query, flags=re.IGNORECASE)
    cte_names = set(re.findall(r"\b([A-Za-z_][\w]*)\s+as\s*\(", query, flags=re.IGNORECASE))

    cleaned = []
    for ref in refs:
        table_name = ref.split(".")[-1].strip('"`[]')
        if table_name.lower() not in {name.lower() for name in cte_names}:
            cleaned.append(table_name)
    return cleaned


def validate_query(query: str, schema: dict) -> dict:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return {"is_valid": False, "error": "Query is empty"}

    lowered = normalized_query.lower()
    if not lowered.startswith(READ_ONLY_PREFIXES):
        return {"is_valid": False, "error": "Only read-only SELECT queries are allowed"}

    if ";" in normalized_query:
        return {"is_valid": False, "error": "Multiple SQL statements are not allowed"}

    for keyword in BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            return {"is_valid": False, "error": f"Blocked SQL keyword detected: {keyword}"}

    schema_tables = {table["name"].lower() for table in schema.get("tables", [])}
    referenced_tables = _extract_table_references(normalized_query)

    missing_tables = [table for table in referenced_tables if table.lower() not in schema_tables]
    if missing_tables:
        return {
            "is_valid": False,
            "error": f"Unknown table(s): {', '.join(missing_tables)}",
        }

    return {"is_valid": True, "error": ""}


def describe_table_with_llm(table_name: str, columns: list) -> str:
    """
    Call LLM to generate a business-friendly description of a table.
    This is cached in the schema JSON so it only runs once per table.
    """
    client = _get_openai_client()
    if client is None:
        return f"Table containing {table_name} data"

    column_names = [col["name"] for col in columns]

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        max_tokens=100,
        messages=[
            {
                "role": "system",
                "content": "You are a data analyst. Given a table name and its columns, write a single clear sentence describing what this table contains and its business purpose. Be specific and concise.",
            },
            {
                "role": "user",
                "content": f"Table: {table_name}\nColumns: {', '.join(column_names)}",
            },
        ],
    )

    return response.choices[0].message.content.strip()


def generate_descriptions_with_llm(tables_data: list) -> dict:
    """
    Send ALL tables to LLM in ONE call to get descriptions for all.
    Much more efficient than calling LLM once per table.
    """
    client = _get_openai_client()
    if client is None:
        return {
            table["name"]: f"Table containing {table['name']} data"
            for table in tables_data
        }

    tables_summary = []
    for table in tables_data:
        column_names = [col["name"] for col in table["columns"]]
        tables_summary.append(f"  {table['name']}: {', '.join(column_names)}")

    tables_text = "\n".join(tables_summary)

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": "You are a data analyst. Return ONLY a JSON object (no markdown, no extra text). Use table names as keys and descriptions as values. Example: {\"orders\": \"Stores customer orders...\", \"customers\": \"Contains customer profile information...\"}",
            },
            {
                "role": "user",
                "content": f"Generate descriptions for these tables:\n{tables_text}",
            },
        ],
    )

    response_text = response.choices[0].message.content.strip()

    try:
        descriptions = json.loads(response_text)
    except json.JSONDecodeError:
        try:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                descriptions = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")
        except Exception:
            print("Warning: failed to parse LLM response, using defaults")
            descriptions = {
                table["name"]: f"Table containing {table['name']} data"
                for table in tables_data
            }

    print(f"Generated descriptions for {len(descriptions)} tables in one LLM call")
    return descriptions


def load_schema_from_db(db_path: str) -> dict:
    """
    Connect to SQLite database, extract all tables and columns,
    get descriptions from LLM in ONE call, build schema dict.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    table_rows = cursor.fetchall()
    tables = [row[0] for row in table_rows]

    tables_data = []
    for table_name in tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_data = cursor.fetchall()

        columns = []
        for col in columns_data:
            columns.append(
                {
                    "name": col[1],
                    "type": col[2],
                    "description": col[1],
                }
            )

        tables_data.append({"name": table_name, "columns": columns})

    conn.close()

    print(f"Generating descriptions for {len(tables_data)} tables in one LLM call...")
    descriptions_dict = generate_descriptions_with_llm(tables_data)

    schema_tables = []
    for table_data in tables_data:
        table_name = table_data["name"]
        description = descriptions_dict.get(table_name, f"{table_name} table")

        schema_tables.append(
            {
                "name": table_name,
                "description": description,
                "columns": table_data["columns"],
            }
        )

    return {
        "data_source_type": "sql",
        "tables": schema_tables,
        "relationships": [],
    }


def generate_and_save_schema(
    db_path: str,
    output_folder: str = "schemas",
) -> dict:
    """
    Smart caching function for schema:
    - If schema JSON already exists, load and return it
    - If schema doesn't exist, generate fresh from DB, save it, and return it
    """
    os.makedirs(output_folder, exist_ok=True)

    db_name = Path(db_path).name
    db_stem = Path(db_name).stem
    output_path = os.path.join(output_folder, f"{db_stem}_schema.json")

    if os.path.exists(output_path):
        print(f"Loading cached schema from: {output_path}")
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print("Schema not found, generating fresh from database...")
    schema = load_schema_from_db(db_path)

    print(f"Saving schema to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    return schema
