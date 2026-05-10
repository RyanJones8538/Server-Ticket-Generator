from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "expected_config.json"
SERVERS_DIR = PROJECT_ROOT / "servers"
TICKETS_PATH = PROJECT_ROOT / "tickets" / "simulated_ticket.json"