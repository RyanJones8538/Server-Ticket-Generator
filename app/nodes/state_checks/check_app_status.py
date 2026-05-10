from app.state.graph_state import StatusCheckState


def check_app_status(state: StatusCheckState) -> dict:
    """
    Checks the status of the app. 
    Rather than adding the issue to raw_issues, it adds them to routing_flags, which sends the issue to a subgraph for further diagnosis.
    Args:
        state: The state of the graph.
    Returns:
        routing_flags: A description of the issue, and accompanying server id.
        status: The status of the graph.
    """
    server = state["server"]
    ideal = state["ideal"]
    
    if server["app_status"] != ideal["expected_app_status"]:
        return {
            "routing_flags": {
                "App status mismatch.": [server["server_id"]]
            },
            "status": "Checking app status."
        }
    return {
        "status": "Checking app status."
    }