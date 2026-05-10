from app.state.graph_state import StatusDiagnosticsState


def check_port_binding(state: StatusDiagnosticsState) -> dict:
    server = state["server"]
    app_port_open = server.get("app_port_open")
    
    if app_port_open is False:
        return {
        "raw_issues": {
            f'Application port not bound: service in unreachable.': [server["server_id"]]
        },
        "port_issue_found": True,
        "status": "Checking port status."
        }
    return {
        "status": "Checking port status."
    }