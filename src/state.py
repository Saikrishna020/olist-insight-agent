from operator import add
from typing import Annotated, TypedDict


class OlistAgentState(TypedDict, total=False):
    question: str
    db_path: str
    mode: str
    schema: dict
    relevant_tables: list
    generated_query: str
    is_valid: bool
    retry_feedback: str
    retry_count: int
    raw_results: list
    execution_error: str
    final_answer: str
    analysis_summary: str
    analysis_questions: list
    analysis_runs: list
    messages: Annotated[list, add]
