import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graphs.audit_group.evaluate_input import build_evaluate_input
from app.graphs.audit_group.search_for_issues import build_search_issues_graph
from app.graphs.collect_data import build_collect_data
from app.graphs.deduplicate import build_deduplicate
from app.graphs.write_tickets import build_write_tickets
from app.models.models import LLMDeduplicationDecision, LLMDeduplicationResults
from app.state.graph_state import AuditState

logger = logging.getLogger(__name__)

def bypass_deduplication(state: AuditState) -> dict:
    issues = state["aggregated_issues"]
    logger.info("Bypassing deduplication. Issue count: %s", len(issues))
    results = [
        LLMDeduplicationDecision(
            potential_ticket=issue,
            is_duplicate=False,
            explanation="Deduplication skipped."
        )
        for issue in issues
    ]
    return {
        "post_llm_filter_issues_count": len(issues),
        "post_llm_filter_issues": LLMDeduplicationResults(results=results)
    }

def route_deduplication(state: AuditState) -> str:
    if state["perform_deduplication"]:
        return "deduplicate"
    return "bypass"

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
    audit_graph.add_node("deduplicate_subgraph", build_deduplicate())
    audit_graph.add_node("bypass_deduplication", bypass_deduplication)
    audit_graph.add_node("write_tickets", build_write_tickets())

    audit_graph.add_edge(START, "evaluate_input_subgraph")
    audit_graph.add_edge("evaluate_input_subgraph", "collect_data_subgraph")
    audit_graph.add_edge("collect_data_subgraph", "search_issues_subgraph")
    audit_graph.add_conditional_edges(
        "search_issues_subgraph",
        route_deduplication,
        {
            "deduplicate": "deduplicate_subgraph",
            "bypass": "bypass_deduplication"
        }
    )
    audit_graph.add_edge("deduplicate_subgraph", "write_tickets")
    audit_graph.add_edge("bypass_deduplication", "write_tickets")
    audit_graph.add_edge("write_tickets", END)

    return audit_graph.compile(checkpointer=checkpointer)
