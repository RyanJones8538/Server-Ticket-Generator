from app.state.graph_state import StatusCheckState


def check_nginx_status(state: StatusCheckState) -> dict:
    """
    Checks the status of nginx on a server.
    Args:
        state: The state of the graph.
    Returns:
        raw_issues: Description of the issue and id of server containing it.
        status: The status of the graph.
    """
    server = state["server"]
    ideal = state["ideal"]

    if server["nginx"]["status"] != ideal["expected_nginx_status"]:
        return {
        "raw_issues": {
            f'Nginx status mismatch. Expected {ideal["expected_nginx_status"]}, found {server["nginx"]["status"]}': [server["server_id"]]
        },
        "status": "Verifying nginx status."
        }

    return {
        "status": "Verifying nginx status."
    }