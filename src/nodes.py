from dotenv import load_dotenv
import os
import json
from openai import OpenAI
from .state import OlistAgentState
from .tools import load_schema, validate_query
import sqlite3

load_dotenv()
github_token = os.getenv('Github_token')
client = OpenAI(
    api_key=github_token,
    base_url="https://models.inference.ai.azure.com",
)

def schema_loader_node(state : OlistAgentState) -> dict:
    schema = load_schema("schemas/olist_schema.json")
    return {"schema": schema}

def question_analyzer_node(state : OlistAgentState) -> dict:
    schema = state['schema']
    question = state['question'] 
    
    # Build table summary using a for loop
    table_summary = []
    for table in schema['tables']:
        summary_line = f"- {table['name']}: {table['description']}"
        table_summary.append(summary_line)
    
    table_summary_text = "\n".join(table_summary)
    
    # Send to LLM with question
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {
                "role": "system", 
                "content": "You are a data analyst. Given a question and available tables, identify which tables are needed to answer the question. Return ONLY a JSON array of table names. Example: [\"orders\", \"customers\"]"
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nAvailable tables:\n{table_summary_text}"
            }
        ]
    )
    
    # Parse the LLM response
    raw_response = response.choices[0].message.content.strip()
    
    try:
        relevant_tables = json.loads(raw_response)
    except:
        relevant_tables = [table['name'] for table in schema['tables']]
    
    return {"relevant_tables": relevant_tables}


def query_generator_node(state : OlistAgentState) -> dict:
    schema = state['schema']
    question = state['question']
    relevant_tables = state.get('relevant_tables', [])
    retry_count = state.get('retry_count', 0)
    retry_feedback = state.get('retry_feedback', '')

    relevant_schema = []
    for table in schema['tables']:
        if table['name'] in relevant_tables:
            relevant_schema.append(table)

    schema_context = json.dumps(relevant_schema, indent=2)

    retry_note = ""
    if retry_feedback:
        retry_note = f"\n\nPrevious query failed with this error: {retry_feedback}\nFix the error."

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {"role": "system", "content": """You are a SQL expert. Generate a SQLite SQL query to answer the question.
        Return ONLY the SQL query, no explanation, no markdown, no backticks."""},
            {"role": "user", "content": f"Question: {question}\n\nSchema:\n{schema_context}{retry_note}"}
        ]
    )

    query = response.choices[0].message.content.strip()
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
            "retry_count": retry_count + 1
        }
    
    return {
        "is_valid": True,
        "validation_error": "",
        "retry_feedback": "",
        "retry_count": retry_count
    }

# ── NODE 5 ──────────────────────────────────────────────
def query_executor_node(state: OlistAgentState) -> dict:
    query = state.get("generated_query", "")
    
    if not state.get("is_valid"):
        return {"raw_results": [], "execution_error": "query was not valid"}
    
    try:
        conn = sqlite3.connect("data/olist.sqlite/olist.sqlite")
        cursor = conn.cursor()
        cursor.execute(query)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        # convert to list of dicts
        results = [dict(zip(columns, row)) for row in rows]
        return {"raw_results": results, "execution_error": ""}
    
    except Exception as e:
        return {"raw_results": [], "execution_error": str(e)}

# ── NODE 6 ──────────────────────────────────────────────
def insight_synthesizer_node(state: OlistAgentState) -> dict:
    question = state["question"]
    raw_results = state.get("raw_results", [])
    execution_error = state.get("execution_error", "")
    
    if execution_error or not raw_results:
        return {"final_answer": f"Could not retrieve data. Error: {execution_error}"}
    
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=500,
        messages=[
            {"role": "system", "content": """You are a business analyst. Given a question and raw data results,
        write a clear plain English insight. Be specific with numbers.
        Keep it to 2-3 sentences maximum."""},
            {"role": "user", "content": f"Question: {question}\n\nData: {json.dumps(raw_results, indent=2)}"}
        ]
    )
    
    answer = response.choices[0].message.content.strip()
    return {"final_answer": answer}

    