from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.nodes.state_checks.check_app_status import check_app_status
from app.nodes.state_checks.check_nginx_status import check_nginx_status
from app.nodes.state_checks.check_nginx_version import check_nginx_version
from app.nodes.state_checks.check_expected_message import check_expected_message

from app.state.graph_state import StatusCheckState, StatusCheckStateOutput



def build_status_checks() -> CompiledStateGraph:
    """
    Builds status checks graph for ticket generator.
    This graph runs basic, high-level diagnostics for future processing.
    Returns:
        status_checks graph.
    """
    
    state_check = StateGraph(StatusCheckState, output_schema=StatusCheckStateOutput)

    state_check.add_node("check_app_status", check_app_status)
    state_check.add_node("check_nginx_version", check_nginx_version)
    state_check.add_node("check_nginx_status", check_nginx_status)
    state_check.add_node("check_expected_message", check_expected_message)

    state_check.add_edge(START, "check_app_status")
    state_check.add_edge(START, "check_nginx_version")
    state_check.add_edge(START, "check_nginx_status")
    state_check.add_edge(START, "check_expected_message")

    state_check.add_edge("check_app_status", END)
    state_check.add_edge("check_nginx_version", END)
    state_check.add_edge("check_nginx_status", END)
    state_check.add_edge("check_expected_message", END)

    graph = state_check.compile()

    return graph