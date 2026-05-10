from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph, Send

from app.config import writer_llm
from app.nodes.write_tickets.ticket_writer import make_ticket_writer
from app.state.graph_state import WriterState

def dispatch_ticket_writer_by_issue(state: WriterState):
    """
    Dispatches the ticket writer for each approved ticket.
    Returns:
        List of generated tickets.
    """
    post_llm_filter_issues = state["post_llm_filter_issues"]
    targets = []

    for issue in post_llm_filter_issues.results:
        if issue.is_duplicate:
            continue
        targets.append(Send("ticket_writer", issue.potential_ticket))

    return targets


def build_write_tickets() -> CompiledStateGraph:
    """
    Builds writer graph for ticket generator to generate helpdesk tickets based off provided issues.
    Returns:
        write_tickets graph.
    """
    
    writer_graph = StateGraph(WriterState)

    writer_graph.add_node("ticket_writer", make_ticket_writer(writer_llm))

    writer_graph.add_conditional_edges(START, dispatch_ticket_writer_by_issue)
    writer_graph.add_edge("ticket_writer", END)

    graph = writer_graph.compile()

    return graph