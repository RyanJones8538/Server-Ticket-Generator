"""
Demonstration: executing shell commands from Python.

Shows how bash/docker commands can be called from within the application — for example,
to apply ticket remediation scripts or manage server containers directly from code.

None of these functions are wired into the main graph. They are reference patterns only.
"""

import shlex
import subprocess

from app.models.models import TicketOutput


def run_shell_command(command: str) -> tuple[int, str, str]:
    """Run a shell command; returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        shlex.split(command),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


# ── Ticket remediation ─────────────────────────────────────────────────────────

def execute_remediation(ticket: TicketOutput) -> dict:
    """
    Execute the bash remediation script embedded in a ticket.

    Usage:
        from app.utils.bash_demo import execute_remediation
        result = execute_remediation(ticket)
        if result["success"]:
            print("Remediation applied.")
    """
    returncode, stdout, stderr = run_shell_command(ticket.remediation)
    return {
        "ticket_id": ticket.ticket_id,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "success": returncode == 0,
    }


# ── Server / nginx management ──────────────────────────────────────────────────

def reload_nginx(container_name: str) -> tuple[int, str, str]:
    """
    Reload nginx config inside a running container without downtime.

    Equivalent bash:
        docker exec server-a2 nginx -s reload
    """
    return run_shell_command(f"docker exec {container_name} nginx -s reload")


def check_nginx_config(container_name: str) -> tuple[int, str, str]:
    """
    Test nginx config validity inside a container.

    Equivalent bash:
        docker exec server-a1 nginx -t
    """
    return run_shell_command(f"docker exec {container_name} nginx -t")


# ── Cluster lifecycle ──────────────────────────────────────────────────────────

def start_cluster(cluster_id: str) -> tuple[int, str, str]:
    """
    Start all servers in a cluster via Docker Compose profiles.

    Equivalent bash:
        docker compose --profile cluster-a up -d
    """
    return run_shell_command(
        f"docker compose --profile cluster-{cluster_id.lower()} up -d"
    )


def stop_server(server_id: str) -> tuple[int, str, str]:
    """
    Stop a specific server container.

    Equivalent bash:
        docker compose stop server-b1
    """
    return run_shell_command(f"docker compose stop {server_id}")
