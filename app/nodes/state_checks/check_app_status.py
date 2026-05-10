from app.state.graph_state import StatusCheckState


def check_app_status(state: StatusCheckState) -> dict:
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