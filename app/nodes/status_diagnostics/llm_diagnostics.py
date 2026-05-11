import logging

from app.state.graph_state import StatusDiagnosticsState

logger = logging.getLogger(__name__)

def make_evaluate_server(llm):
    """
    Wrapper function to create evaluate_server, which searches a server's state for issues when deterministic tests fail.
    Args:
        llm: llm used to study server
    Returns:
        evaluate_server node
    """
    def evaluate_server(state: StatusDiagnosticsState):
        """
        Searches a given server for issues if previous checks fail.
        Args:
            state: The state of the graph.
        Returns: 
            raw_issues: Description of the issue and id of server containing it.
            status: The status of the graph.
        """
        server = state.get("server")
        cluster = state.get("cluster_id")

        model = llm()

        logger.info("Deterministic checks failed. Running LLM check. Cluster: %s, server: %s", cluster, server)

        prompt = f"""
                You are a server diagnostics expert. Server {server.get("server_id")} of cluster {cluster} is reporting a degraded app_status.
                Prior automated checks have already ruled out a closed app port and excessive memory usage as the cause.

                Here is the full server state:
                {server}

                Investigate why the app is degraded. Identify all configuration anomalies that could be contributing — not just the first one you find.
                Describe them together as a single cohesive finding, precise enough to generate a helpdesk ticket and an accompanying solution.
                """
        
        result = model.invoke(prompt)

        logger.info("LLM diagnostic output: %s", result)

        if result.issue_found:
            return {
                "raw_issues": {
                    result.issue: [server["server_id"]]
                },
                "status": "Evaluated app's status with LLM."
        }

        return {
            "status": "Evaluated app's status with LLM."
        }
    return evaluate_server