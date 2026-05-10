from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import parse_llm
from app.nodes.parse_query.request_new_input import request_new_input
from app.nodes.parse_query.parse_query import make_parse_query
from app.state.graph_state import ParseState


def route_query(state):
    query_judgement = state["query_judgement"]

    if query_judgement.is_valid:
        return "valid"
    return "invalid"

def build_evaluate_input() -> CompiledStateGraph:
    parse_graph = StateGraph(ParseState)

    parse_graph.add_node("parse_query", make_parse_query(parse_llm))
    parse_graph.add_node("request_new_input", request_new_input)

    parse_graph.add_edge(START, "parse_query")
    parse_graph.add_conditional_edges(
                    "parse_query", 
                    route_query,
                    {
                        "valid": END,
                        "invalid": "request_new_input"
                    })
    parse_graph.add_edge("request_new_input", "parse_query")
    

    return parse_graph.compile()
