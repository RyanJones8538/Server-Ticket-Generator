from app.state.graph_state import StatusCheckState

def check_expected_message(state: StatusCheckState) -> dict:
    """
        Checks whether expected message matches ideal state.
    """
    ideal = state["ideal"]
    server = state["server"]

    if ideal["expected_message"] != server["message"]:
        return {
            "status": "Checking expected message.",
            "raw_issues": {
                f'Expected message: {ideal["expected_message"]}, actual message: {server["message"]}.': [server["server_id"]]
            }
        }


    return {
        "status": "Checking expected message."
    }