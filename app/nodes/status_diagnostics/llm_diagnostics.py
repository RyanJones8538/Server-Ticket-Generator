from app.models.models import QueryJudgement
from app.state.graph_state import StatusDiagnosticsState


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
        Parses the users's query for comprehensibility as a request, and for security purposes.
        Args:
            state: graph_state
        Returns: 
            A boolean determining the judgement, and a user-facing message explaining it.
        """
        server = state.get("server")
        cluster = state.get("cluster_id")

        model = llm

        prompt = f"""
                You are a server diagnostics expert. Server {server.get("server_id")} of cluster {cluster} is reporting a degraded app_status.
                Prior automated checks have already ruled out a closed app port and excessive memory usage as the cause.

                Here is the full server state:
                {server}

                Investigate why the app is degraded. Identify all configuration anomalies that could be contributing — not just the first one you find.
                Describe them together as a single cohesive finding, precise enough to generate a helpdesk ticket and an accompanying solution.
                """
        
        result = model.invoke(prompt)

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