from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graphs.deduplicate import build_deduplicate
from app.graphs.collect_data import build_collect_data
from app.graphs.run_diagnostics import build_run_diagnostics
from app.graphs.write_tickets import build_write_tickets
from app.state.graph_state import MainState

def route_after_diagnostics(state):
    """
    Routes graph after analyzing diagnostics. If there are no issues found, prematurely exit the graph. Otherwise, continue.
    Args: 
        state: The current state of the graph.
    Returns:
        string corresponding to the next action to take.
    """
    aggregated_issues_count = state["aggregated_issues_count"]

    if aggregated_issues_count == 0:
        return "terminate"
    else:
        return "continue"
    
def route_after_aggregation(state):
    """
    Routes graph after aggregating and deduplicating issues. If there are no issues found, prematurely exit the graph. Otherwise, continue.
    Args: 
        state: The current state of the graph.
    Returns:
        string corresponding to the next action to take.
    """
    post_filter_issues_count = state["post_deterministic_filter_issues_count"]

    if post_filter_issues_count == 0:
        return "terminate"
    else:
        return "continue"

def build_main_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Builds main graph for ticket generator.
    Returns:
        main_graph.
    """
    
    main_graph = StateGraph(MainState)

    main_graph.add_node("collect_data_subgraph", build_collect_data())
    main_graph.add_node("run_diagnostics_subgraph", build_run_diagnostics())
    main_graph.add_node("deduplicate_subgraph", build_deduplicate())
    main_graph.add_node("write_tickets_subgraph", build_write_tickets())

    main_graph.add_edge(START, "collect_data_subgraph")
    main_graph.add_edge("collect_data_subgraph", "run_diagnostics_subgraph")
    main_graph.add_conditional_edges("run_diagnostics_subgraph",
                                     route_after_diagnostics,
                                     {
                                         "continue": "deduplicate_subgraph",
                                         "terminate": END
                                     }
    )
    main_graph.add_conditional_edges("deduplicate_subgraph",
                                     route_after_aggregation,
                                     {
                                         "continue": "write_tickets_subgraph",
                                         "terminate": END
                                     }
    )
    main_graph.add_edge("write_tickets_subgraph", END)

    graph = main_graph.compile(checkpointer=checkpointer)

    return graph