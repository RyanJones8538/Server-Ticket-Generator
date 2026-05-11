import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graphs.audit_group.evaluate_input import build_evaluate_input
from app.graphs.audit_group.search_for_issues import build_search_issues_graph
from app.graphs.audit_group.write_audit_tickets import build_write_audit_tickets
from app.graphs.collect_data import build_collect_data
from app.state.graph_state import AuditState

logger = logging.getLogger(__name__)

def build_audit_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """
    Generates the audit graph, used to perform a search for issues outside standard diagnostics.
    Callable with a prompt that can focus the search for more specific results,
    or without a prompt to find issues that have not yet been considered.
    """
    audit_graph = StateGraph(AuditState)

    audit_graph.add_node("evaluate_input_subgraph", build_evaluate_input())
    audit_graph.add_node("collect_data_subgraph", build_collect_data())
    audit_graph.add_node("search_issues_subgraph", build_search_issues_graph())
    audit_graph.add_node("write_tickets", build_write_audit_tickets())

    audit_graph.add_edge(START, "evaluate_input_subgraph")
    audit_graph.add_edge("evaluate_input_subgraph", "collect_data_subgraph")
    audit_graph.add_edge("collect_data_subgraph", "search_issues_subgraph")
    audit_graph.add_edge("search_issues_subgraph", "write_tickets")
    audit_graph.add_edge("write_tickets", END)


    return audit_graph.compile(checkpointer=checkpointer)
