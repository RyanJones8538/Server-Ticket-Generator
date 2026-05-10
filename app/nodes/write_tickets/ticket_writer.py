import json
from uuid import uuid4

from app.models.models import AggregatedIssue

def make_ticket_writer(llm):
    """
    Wrapper function for ticket_writer node, which takes a single potential ticket stub and generates a ticket out of it.
    Args:
        llm: The language model used for writing the ticket.
    Returns:
        ticket_writer function, which can be used as a node in the graph.
    """
    def ticket_writer(state: AggregatedIssue):
        """
        Writes a ticket for every potential ticket that has not been rated as a duplicate.
        Args:
            state: A single issue that has been rated a non-duplicate.
        Returns:
            ticket_writer node.
        """
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