from app.state.graph_state import StatusCheckState


def check_nginx_version(state: StatusCheckState) -> dict:
    """
    Checks the version of nginx on a server.
    Args:
        state: The state of the graph.
    Returns:
        raw_issues: Description of the issue and id of server containing it.
        status: The status of the graph.
    """
    server = state["server"]
    ideal = state["ideal"]

    if server["nginx"]["version"] != ideal["expected_nginx_version"]:
        return {
        "raw_issues": {
            f'Nginx version mismatch. Expected {ideal["expected_nginx_version"]}, found {server["nginx"]["version"]}': [server["server_id"]]
        },
        "status": "Verifying nginx version."
        }

    return {
        "status": "Verifying nginx version."
    }