from app.state.graph_state import StatusCheckState


def check_nginx_version(state: StatusCheckState) -> dict:
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