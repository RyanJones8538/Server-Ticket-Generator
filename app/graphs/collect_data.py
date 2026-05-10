from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.nodes.collect_data.collect_ideal_state import retrieve_ideal_state
from app.nodes.collect_data.collect_server_states import collect_server_states
from app.state.graph_state import CollectState



def build_collect_data() -> CompiledStateGraph:
    """
    Builds data-collection subgraph for ticket generator.
    It collects information on all servers within a cluster, as well as their ideal states.
    Returns:
        collect_data graph.
    """
    
    collect_graph = StateGraph(CollectState)

    collect_graph.add_node("collect_ideal_state", retrieve_ideal_state)
    collect_graph.add_node("collect_server_states", collect_server_states)

    collect_graph.add_edge(START, "collect_ideal_state")
    collect_graph.add_edge("collect_ideal_state", "collect_server_states")
    collect_graph.add_edge("collect_server_states", END)

    graph = collect_graph.compile()

    return graph