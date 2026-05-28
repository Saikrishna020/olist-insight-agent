from typing import TypedDict,Annotated
from operator import add

class OlistAgentState(TypedDict):
    question : str
    schema : dict
    relevant_tables : list
    generated_query : str
    is_valid : bool
    retry_feedback : str
    retry_count : int
    raw_results : list
    execution_error : str
    final_answer : str
    messages : Annotated[list, add]
