import json
import logging
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph, Send

from app.config import writer_llm
from app.state.graph_state import AuditWriterState

logger = logging.getLogger(__name__)

def make_audit_ticket_writer(llm):
    def ticket_writer(state):
        model = llm()
        affected_servers = state["affected_servers"]
        issue = state["issue"]
        cluster_id = state["cluster_id"]
        ticket_id = str(uuid4())
        affected_servers_json = json.dumps(affected_servers)

        prompt = f"""
            You are a QA person writing tickets for issues affecting a server network.
            You will examine the provided issue and affected servers, and generate a description, severity and remediation.
            DO NOT edit issue, cluster_id, ticket_id or affected_servers.

            Here are the affected servers: {affected_servers_json}

            Here is the cluster_id: {cluster_id}

            Here is the issue: {issue}

            The ticket ID is: {ticket_id}

            Severity: 1 = informational, 2 = minor, 3 = moderate, 4 = major, 5 = critical (service down)

            For the remediation field, apply the following rules strictly:

            - If the issue has a single, unambiguous root cause and a known fix (e.g. a version mismatch
              where the correct version is known), provide executable Bash, Nginx or Ansible code.
              If multiple servers require the same fix, prefer Ansible. Code must be clearly readable
              and executable. You may include brief instructional text alongside the code.

            - If the issue is a symptom whose root cause cannot be determined from the information
              provided (e.g. a server that is not responding — which could be caused by a crash,
              resource exhaustion, a bad config, a network fault, or many other things), do NOT
              provide a fix. Instead, describe the investigation steps an engineer should take to
              determine the cause before attempting a remediation. List the specific commands they
              should run and what to look for in the output.

            The output will be displayed in markdown; feel free to use it.
        """
        result = model.invoke(prompt)

        return {
            "tickets_created": [result],
            "status": "Writing tickets."
        }

    return ticket_writer


def dispatch_audit_ticket_writer(state: AuditWriterState):
    return [Send("ticket_writer", issue.model_dump()) for issue in state["issues"]]


def build_write_audit_tickets() -> CompiledStateGraph:
    writer_graph = StateGraph(AuditWriterState)

    writer_graph.add_node("ticket_writer", make_audit_ticket_writer(writer_llm))

    writer_graph.add_conditional_edges(START, dispatch_audit_ticket_writer)
    writer_graph.add_edge("ticket_writer", END)

    return writer_graph.compile()
