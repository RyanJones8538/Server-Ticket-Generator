import httpx
import json
import logging
import re
import subprocess

import yaml

from app.models.models import NginxState, PortsState, ResourcesState, ServerDiagnosticsConfig, ServerState
from app.paths import INVENTORY_PATH, SERVERS_DIR
from app.state.graph_state import CollectState

logger = logging.getLogger(__name__)

def collect_from_file(server_id: str, cluster_id: str) -> ServerState:
    json_path = SERVERS_DIR / f"server-cluster-{cluster_id.lower()}" / server_id / f"{server_id}.json"
    with open(json_path) as f:
        metadata = json.load(f)

    logger.info("Loading file for server %s in cluster %s.", server_id, cluster_id)
    server = ServerState(
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
    return server

def run_in_container(server_id: str, *command: str) -> str:
    result = subprocess.run(
        ["docker", "exec", server_id, *command],
        capture_output=True, text=True
    )
    return result.stdout.strip() or result.stderr.strip()

def collect_via_docker(server_id: str, cluster_id: str) -> ServerState:
    # nginx -v writes to stderr, not stdout — capture both
    version_result = subprocess.run(
        ["docker", "exec", server_id, "nginx", "-v"],
        capture_output=True, text=True
    )
    raw_version = version_result.stderr.strip()
    match = re.search(r"nginx/(\S+)", raw_version)
    nginx_version = match.group(1) if match else "unknown"
    nginx_installed = nginx_version != "unknown"

    # pgrep is more reliable than systemctl in Docker (containers rarely run systemd)
    nginx_running = run_in_container(server_id, "pgrep", "-x", "nginx")
    nginx_status = "running" if nginx_running else "stopped"

    # docker stats avoids exec-ing into the container for resource usage
    stats_raw = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}},{{.MemPerc}}", server_id],
        capture_output=True, text=True
    ).stdout.strip()
    cpu_str, mem_str = stats_raw.split(",")
    cpu_pct = float(cpu_str.replace("%", ""))
    mem_pct = float(mem_str.replace("%", ""))

    # check if port 80 is bound — ss may not exist in minimal images, netstat is a fallback
    port_check = subprocess.run(
        ["docker", "exec", server_id, "sh", "-c", "ss -tlnp | grep -q ':80'"],
        capture_output=True
    )
    app_port_open = port_check.returncode == 0

    #This command fetches two HTTP variables. The final product will not use them.

    try:
        response = httpx.get(f"http://{server_id}/status", timeout=3.0)
        response.raise_for_status()
        data = response.json()
        app_status = data["app_status"]
        message = data["message"]
    except Exception:
        logger.warning("Could not reach /status on %s, app_status and message unavailable.", server_id)
        app_status = "unknown"
        message = ""

    return ServerState(
        server_id=server_id,
        cluster=cluster_id,
        hostname=server_id,
        app_status=app_status,
        message=message,
        nginx=NginxState(
            installed=nginx_installed,
            version=nginx_version,
            status=nginx_status,
        ),
        ports=PortsState(http=80),
        app_port_open=app_port_open,
        resources=ResourcesState(
            cpu_usage_percent=cpu_pct,
            memory_usage_percent=mem_pct,
        ),
        diagnostics_config=ServerDiagnosticsConfig(
            upstream_timeout_seconds=0,
            keepalive_connections=0,
        )
    )


def collect_server_states(state: CollectState) -> dict:
    """
    Collects states from servers, calling the actual server if possible. Reads from the file if not, or if inventory.yaml lists Mode as file.
    The file exists to simulate Cluster D, which involves excessive memory and CPU usage that would be undesireable to run on a computer.
    Args:
        state: The state of the graph.
    Returns:
        server_states: A list of the collected states of the servers.
        status: The status of the graph
    """
    cluster_id = state["cluster_id"]
    with open(INVENTORY_PATH) as f:
        inventory = yaml.safe_load(f)
    cluster_config = inventory["clusters"][cluster_id]
    mode = cluster_config.get("mode", "http")
    servers = cluster_config["servers"]

    server_states: dict[str, ServerState] = {}
    
    for entry in servers:
        server_id = entry["server_id"]
        if mode == "http":
            try:
                server_states[server_id] = collect_via_docker(server_id, cluster_id)
            except Exception:
                logger.warning("Docker collection failed for %s, falling back to file.", server_id)
                server_states[server_id] = collect_from_file(server_id, cluster_id)
        else:
            server_states[server_id] = collect_from_file(server_id, cluster_id)

    logger.info("Collected server states. Cluster ID: %s, server states: %s", cluster_id, server_states)
    return {
        "server_states": server_states,
        "status": "Retrieved server statuses.",
    }
