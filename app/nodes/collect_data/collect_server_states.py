import json

import httpx

from app.models.models import NginxState, PortsState, ResourcesState, ServerDiagnosticsConfig, ServerState
from app.paths import SERVERS_DIR
from app.state.graph_state import CollectState


def collect_server_states(state: CollectState) -> dict:
    """
    Collects states from servers, calling the actual server if possible, or reading from the file if not.
    I read from the file because Cluster D involves excessive memory and CPU usage,
    which I would prefer to not run on my computer.
    Args:
        state: The state of the graph.
    Returns:
        server_states: A list of the collected states of the servers.
        status: The status of the graph
    """
    cluster_id = state["cluster_id"]
    cluster_dir = SERVERS_DIR / f"server-cluster-{cluster_id.lower()}"

    server_states: dict[str, ServerState] = {}
    for json_path in cluster_dir.rglob("*.json"):
        with open(json_path) as f:
            metadata = json.load(f)

        server_id = metadata["server_id"]
        try:
            response = httpx.get(f"http://{server_id}/status", timeout=3.0)
            response.raise_for_status()
            data = response.json()
            server_states[server_id] = ServerState(**data)
        except Exception:
            server_states[server_id] = ServerState(
                server_id=server_id,
                cluster=metadata["cluster"],
                hostname=metadata["hostname"],
                app_status=metadata["app_status"],
                message=metadata["message"],
                nginx=NginxState(
                    installed=metadata["nginx"]["installed"],
                    version=metadata["nginx"]["version"],
                    status=metadata["nginx"]["status"],
                ),
                ports=PortsState(http=metadata["ports"]["http"]),
                app_port_open=metadata["app_port_open"],
                resources=ResourcesState(
                    cpu_usage_percent=metadata["resources"]["cpu_usage_percent"],
                    memory_usage_percent=metadata["resources"]["memory_usage_percent"],
                ),
                diagnostics_config=ServerDiagnosticsConfig(
                    upstream_timeout_seconds=metadata["diagnostics_config"]["upstream_timeout_seconds"],
                    keepalive_connections=metadata["diagnostics_config"]["keepalive_connections"],
                )

            )

    return {
        "server_states": server_states,
        "status": "Retrieved server statuses.",
    }
