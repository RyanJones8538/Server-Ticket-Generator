from app.state.graph_state import StatusCheckState


def check_nginx_status(state: StatusCheckState) -> dict:
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