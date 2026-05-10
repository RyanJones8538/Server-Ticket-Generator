import json

from app.models.models import IdealState
from app.paths import CONFIG_PATH
from app.state.graph_state import CollectState


def retrieve_ideal_state(state: CollectState) -> dict:
    """
    Retrieves the ideal state of a server configuration from .json.
    Args:
        state: State of the graph
    Returns:
        status: Status of the graph.
        ideal_state: Ideal State as a Python class.
    """
    cluster_id = state["cluster_id"]

    with open(CONFIG_PATH) as f:
        expected_config = json.load(f)

    ideal_state = IdealState(
            expected_nginx_version=expected_config["expected_nginx_version"],
            expected_nginx_status=expected_config["expected_nginx_status"],
            expected_app_status=expected_config["expected_app_status"],
            expected_message=expected_config["clusters"][cluster_id]["expected_message"]
    )

    return {
        "ideal_state": ideal_state,
        "status": "Collected ideal state"
    }