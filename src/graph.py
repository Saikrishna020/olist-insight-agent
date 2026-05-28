from langgraph.graph import StateGraph, START, END
from .state import OlistAgentState
from .nodes import (
    schema_loader_node,
    question_analyzer_node,
    query_generator_node,
    query_validator_node,
    query_executor_node,
    insight_synthesizer_node
)

def should_retry(state: OlistAgentState) -> str:
    if not state.get("is_valid") and state.get("retry_count", 0) < 3:
        return "retry"
    return "done"

def build_graph():
    graph = StateGraph(OlistAgentState)
    
    graph.add_node("schema_loader", schema_loader_node)
    graph.add_node("question_analyzer", question_analyzer_node)
    graph.add_node("query_generator", query_generator_node)
    graph.add_node("query_validator", query_validator_node)
    graph.add_node("query_executor", query_executor_node)
    graph.add_node("insight_synthesizer", insight_synthesizer_node)
    
    graph.add_edge(START, "schema_loader")
    graph.add_edge("schema_loader", "question_analyzer")
    graph.add_edge("question_analyzer", "query_generator")
    graph.add_edge("query_generator", "query_validator")
    
    graph.add_conditional_edges(
        "query_validator",
        should_retry,
        {
            "retry": "query_generator",
            "done": "query_executor"
        }
    )
    
    graph.add_edge("query_executor", "insight_synthesizer")
    graph.add_edge("insight_synthesizer", END)
    
    return graph.compile()