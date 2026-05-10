from langgraph.types import interrupt

from app.state.graph_state import ParseState


def request_new_input(state: ParseState):
    """
    Interrupts the graph to request a new input if the previous was considered invalid.
    """
    request_id = state["request_id"]
    query_judgement = state["query_judgement"]

    new_query = interrupt(
        {
            "message": query_judgement.explanation
        }
    )

    return {
        "query": new_query,
        "status": "Requested new query."
    }