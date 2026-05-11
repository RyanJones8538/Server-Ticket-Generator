from app.state.graph_state import StatusDiagnosticsState

def check_memory_usage(state: StatusDiagnosticsState) -> dict:
    """
    Checks the status of memory usage on a server.
    Args:
        state: The state of the graph.
    Returns:
        raw_issues: Description of the issue and id of server containing it.
        status: The status of the graph.
    """
    server = state["server"]
    resources = server.get("resources")
    memory = resources.get("memory_usage_percent")
    
    if memory >= 90:
        return {
        "raw_issues": {
            f"Critical memory exhaustion: memory_usage_percent at {memory:.0f}%": [server["server_id"]]
        },
        "status": "Checking memory usage.",
        "memory_issue_found": True
        }
    return {
        "status": "Checking memory usage."
    }