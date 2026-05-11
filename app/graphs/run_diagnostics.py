import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph, Send

from app.config import aggregate_llm
from app.graphs.status_checks import build_status_checks
from app.graphs.status_diagnostics import build_status_diagnostics
from app.nodes.run_diagnostics.aggregate import make_aggregate_issues
from app.state.graph_state import DiagnosticsState

logger = logging.getLogger(__name__)

def dispatch_status_checks_by_server(state: DiagnosticsState):
    """
    Dispatches tasks to check status by server.
    Args: 
        state: State of the graph.
    Returns:
        result of the dispatches.
    """
    request_id = state["request_id"]
    server_states = state["server_states"]
    ideal_state = state["ideal_state"]
    targets = []

    for _, server_state in server_states.items():
        targets.append(Send("status_checks_subgraph", {
            "request_id": request_id,
            "server": server_state,
            "ideal": ideal_state,
            "status": "Entering status checks subgraph.",
            "routing_flags": {},
            "raw_issues": {}
        }))

    return targets

def dispatch_status_diagnostics_by_server(state: DiagnosticsState):
    """
    Dispatches servers with app_status outside ideal to a subgraph which will provide more specific diagnostics.
    Args:
        state: State of the graph.
    Returns:
        Results of the server dispatch.
    """
    routing_flags = state.get("routing_flags", {})
    raw_issues = state.get("raw_issues", {})

    if not routing_flags and not raw_issues:
        return "terminate"

    if not routing_flags:
        return "aggregate"

    targeted_servers = set()
    for servers in routing_flags.values():
        targeted_servers.update(servers)

    return [
        Send("status_diagnostics_subgraph", {
            "request_id": state["request_id"],
            "cluster_id": state["cluster_id"],
            "server": state["server_states"][server_id],
            "ideal": state["ideal_state"],
            "status": "Entering status diagnostics.",
            "raw_issues": {},
            "port_issue_found": False,
            "memory_issue_found": False,
        })
        for server_id in targeted_servers
        if server_id in state["server_states"]
    ]

def build_run_diagnostics() -> CompiledStateGraph:
    """Builds diagnostics graph for ticket generator.
    This graph runs typical, unit-test style diagnostics and records the results.
    Returns:
        run_diagnostics graph.
    """
    
    diagnostics_graph = StateGraph(DiagnosticsState)

    diagnostics_graph.add_node("status_checks_subgraph", build_status_checks())
    diagnostics_graph.add_node("status_diagnostics_subgraph", build_status_diagnostics())
    diagnostics_graph.add_node("aggregate_issues", make_aggregate_issues(aggregate_llm()))

    diagnostics_graph.add_conditional_edges(START, dispatch_status_checks_by_server)
    diagnostics_graph.add_conditional_edges("status_checks_subgraph", dispatch_status_diagnostics_by_server,
                                            {
                                                "terminate": END,
                                                "aggregate": "aggregate_issues"
                                            })
    diagnostics_graph.add_edge("status_diagnostics_subgraph", "aggregate_issues")

    diagnostics_graph.add_edge("aggregate_issues", END)


    

    graph = diagnostics_graph.compile()

    return graph