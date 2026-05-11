import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import evaluate_server_llm
from app.nodes.status_diagnostics.check_memory_usage import check_memory_usage
from app.nodes.status_diagnostics.check_port_binding import check_port_binding
from app.nodes.status_diagnostics.llm_diagnostics import make_evaluate_server
from app.state.graph_state import StatusDiagnosticsState, StatusDiagnosticsStateOutput

logger = logging.getLogger(__name__)

def route_after_memory(state: StatusDiagnosticsState):
    """
    Routes the graph to exit if an issue with memory has been found.
    Args:
        state: The state of the graph.
    Returns:
        String corresponding to the next node to enter.
    """
    memory_issue_found = state.get("memory_issue_found")

    if memory_issue_found:
        return "terminate"
    return "llm"

def route_after_port(state: StatusDiagnosticsState):
    """
    Routes the graph to exit if an issue with ports has been found.
    Args:
        state: The state of the graph.
    Returns:
        String corresponding to the next node to enter.
    """
    port_issue_found = state.get("port_issue_found")

    if port_issue_found:
        return "terminate"
    return "memory"

def build_status_diagnostics() -> CompiledStateGraph:
    """
    Subgraph to analyze issues on a deeper level. Runs deterministic checks first,
    and routes to an LLM if an issue is not found through those.
    Returns:
        status_diagnostics graph.
    """

    status_diagnostics = StateGraph(StatusDiagnosticsState, output_schema=StatusDiagnosticsStateOutput)

    status_diagnostics.add_node("check_port_binding", check_port_binding)
    status_diagnostics.add_node("check_memory_usage", check_memory_usage)
    status_diagnostics.add_node("evaluate_server", make_evaluate_server(evaluate_server_llm))

    status_diagnostics.add_edge(START, "check_port_binding")
    status_diagnostics.add_conditional_edges("check_port_binding", route_after_port, 
                                             {
                                                "terminate": END,
                                                "memory": "check_memory_usage"
                                             })
    status_diagnostics.add_conditional_edges("check_memory_usage", 
                                             route_after_memory, {
                                                 "terminate": END,
                                                 "llm": "evaluate_server"
                                             })
    status_diagnostics.add_edge("evaluate_server", END)

    return status_diagnostics.compile()