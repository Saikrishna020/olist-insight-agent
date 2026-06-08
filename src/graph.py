from langgraph.graph import END, START, StateGraph

from .nodes import (
    analysis_executor_node,
    analysis_planner_node,
    insight_synthesizer_node,
    query_executor_node,
    query_generator_node,
    query_validator_node,
    question_analyzer_node,
    schema_loader_node,
)
from .state import OlistAgentState


def should_use_analysis_flow(state: OlistAgentState) -> str:
    mode = (state.get("mode") or "").lower()
    question = (state.get("question") or "").lower()
    analysis_keywords = ("why", "analyze", "analyse", "investigate", "compare", "cause", "trend")

    if mode == "analysis":
        return "analysis"

    if any(keyword in question for keyword in analysis_keywords):
        return "analysis"

    return "single"


def should_retry_after_validation(state: OlistAgentState) -> str:
    if not state.get("is_valid") and state.get("retry_count", 0) < 3:
        return "retry"
    return "done"


def should_retry_after_execution(state: OlistAgentState) -> str:
    if state.get("execution_error") and state.get("retry_count", 0) < 3:
        return "retry"
    return "done"


def build_graph():
    graph = StateGraph(OlistAgentState)

    graph.add_node("schema_loader", schema_loader_node)
    graph.add_node("question_analyzer", question_analyzer_node)
    graph.add_node("query_generator", query_generator_node)
    graph.add_node("query_validator", query_validator_node)
    graph.add_node("query_executor", query_executor_node)
    graph.add_node("analysis_planner", analysis_planner_node)
    graph.add_node("analysis_executor", analysis_executor_node)
    graph.add_node("insight_synthesizer", insight_synthesizer_node)

    graph.add_edge(START, "schema_loader")

    graph.add_conditional_edges(
        "schema_loader",
        should_use_analysis_flow,
        {
            "single": "question_analyzer",
            "analysis": "analysis_planner",
        },
    )

    graph.add_edge("question_analyzer", "query_generator")
    graph.add_edge("analysis_planner", "analysis_executor")
    graph.add_edge("analysis_executor", "insight_synthesizer")

    graph.add_edge("query_generator", "query_validator")

    graph.add_conditional_edges(
        "query_validator",
        should_retry_after_validation,
        {
            "retry": "query_generator",
            "done": "query_executor",
        },
    )

    graph.add_conditional_edges(
        "query_executor",
        should_retry_after_execution,
        {
            "retry": "query_generator",
            "done": "insight_synthesizer",
        },
    )

    graph.add_edge("insight_synthesizer", END)

    return graph.compile()
