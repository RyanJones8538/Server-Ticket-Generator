import json

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph, Send

from app.config import dedupe_llm
from app.models.models import TicketOutput
from app.nodes.deduplicate.deterministic_deduplicate import deterministic_deduplicate
from app.nodes.deduplicate.llm_deduplicate import make_llm_deduplicate
from app.paths import TICKETS_PATH
from app.state.graph_state import DeduplicateState

def dispatch_deterministic_deduplicate(state: DeduplicateState):
    existing_tickets = state["existing_tickets"]
    aggregated_issues = state["aggregated_issues"]
    targets = []

    for issue in aggregated_issues:
        targets.append(Send("deterministic_deduplicate", {
            "candidate_ticket": issue,
            "existing_tickets": existing_tickets
        }))

    return targets

def initialize_node(state: DeduplicateState) -> dict:

    cluster_id=state["cluster_id"]

    with open(TICKETS_PATH) as f:
        raw = json.load(f)
    existing_tickets = [TicketOutput.model_validate(t) for t in raw if t["cluster"] == cluster_id]
    return {
        "existing_tickets": existing_tickets
    }

def route_after_deterministic(state: DeduplicateState):
    issues_count = state["post_deterministic_filter_issues_count"]

    if issues_count == 0:
        return "terminate"
    return "llm_deduplicate"

def build_deduplicate() -> CompiledStateGraph:
    """
    Builds deduplication subgraph for ticket generator.
    Returns:
        deduplicate subgraph.
    """
    
    aggregate_graph = StateGraph(DeduplicateState)

    aggregate_graph.add_node("initialize", initialize_node)
    aggregate_graph.add_node("deterministic_deduplicate", deterministic_deduplicate)
    aggregate_graph.add_node("llm_deduplicate", make_llm_deduplicate(dedupe_llm))

    aggregate_graph.add_edge(START, "initialize")
    aggregate_graph.add_conditional_edges("initialize", dispatch_deterministic_deduplicate)
    aggregate_graph.add_conditional_edges("deterministic_deduplicate",
                                          route_after_deterministic,
                                          {
                                            "terminate": END,
                                            "llm_deduplicate": "llm_deduplicate"      
                                          }
                                        )
    aggregate_graph.add_edge("llm_deduplicate", END)

    graph = aggregate_graph.compile()

    return graph