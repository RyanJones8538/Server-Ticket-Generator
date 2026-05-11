import logging

from typing import cast
from uuid import uuid4
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver

from app.graphs.standard_diagnostics_graph import build_standard_diagnostics_graph
from app.graphs.audit_group.audit_group import build_audit_graph
from app.state.graph_state import MainState, AuditState
from app.models.models import IdealState, LLMDeduplicationResults, QueryJudgement


load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)

logger = logging.getLogger(__name__)

def start_run(cluster_id: str) -> MainState:
    """
    Starts run of Server Ticket Debugger via standard_diagnostics_graph.
    Returns:
        Final MainState after graph execution.
    """
    logger.info("Starting new run from main.py.")

    request_id = str(uuid4())
    initial_state: MainState = {
        "request_id": request_id,
        "cluster_id": cluster_id,
        "status": f"Initializing Ticket Generator for Cluster {cluster_id}",
        "graph_type": "tests",
        "server_states": {},
        "ideal_state": IdealState(
            expected_nginx_version="",
            expected_nginx_status="",
            expected_app_status="",
            expected_message="",
        ),
        "aggregated_issues_count": 0,
        "aggregated_issues": [],
        "post_llm_filter_issues_count": 0,
        "post_llm_filter_issues": LLMDeduplicationResults(results=[]),
        "tickets_created": [],
    }
    config: RunnableConfig = {
        "metadata": {"request_id": request_id},
        "configurable": {"thread_id": request_id}
    }

    checkpointer = MemorySaver()
    graph = build_standard_diagnostics_graph(checkpointer)

    logger.info("Invoking main graph for request_id: %s", request_id)
    final_state = cast(MainState, graph.invoke(initial_state, config))

    tickets = final_state.get("tickets_created", [])
    logger.info("Run complete. %d ticket(s) created.", len(tickets))
    for ticket in tickets:
        logger.info("Ticket %s — severity %d — %s", ticket.ticket_id, ticket.severity, ticket.issue)

    return final_state


def start_audit(cluster_id: str, query: str = "", perform_deduplication: bool = False) -> AuditState:
    """
    Starts a cluster audit run via audit_group graph.
    Returns:
        Final AuditState after graph execution.
    """
    logger.info("Starting audit from main.py.")

    request_id = str(uuid4())
    initial_state: AuditState = {
        "request_id": request_id,
        "cluster_id": cluster_id,
        "graph_type": "audit",
        "query": query,
        "query_judgement": QueryJudgement(
            is_valid=False,
            explanation=""
        ),
        "server_states": {},
        "ideal_state": IdealState(
            expected_nginx_version="",
            expected_nginx_status="",
            expected_app_status="",
            expected_message="",
        ),
        "perform_deduplication": perform_deduplication,
        "status": f"Initializing audit for Cluster {cluster_id}",
        "aggregated_issues": [],
        "aggregated_issues_count": 0,
        "post_llm_filter_issues": LLMDeduplicationResults(results=[]),
        "post_llm_filter_issues_count": 0,
        "tickets_created": [],
    }
    config: RunnableConfig = {
        "metadata": {"request_id": request_id},
        "configurable": {"thread_id": request_id},
    }

    checkpointer = MemorySaver()
    graph = build_audit_graph(checkpointer)

    logger.info("Invoking audit graph for request_id: %s", request_id)
    final_state = cast(AuditState, graph.invoke(initial_state, config))

    tickets = final_state.get("tickets_created", [])
    logger.info("Audit complete. %d tickets created.", len(tickets))

    return final_state


if __name__ == "__main__":
    start_run("A")