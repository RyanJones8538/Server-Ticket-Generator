from dotenv import load_dotenv
load_dotenv()

from langsmith import Client
import json

client = Client()

runs = list(client.list_runs(
    project_name="server-ticket-debugger",
    is_root=True,
    limit=1,
))
last_run = runs[0]

all_runs = list(client.list_runs(
    project_name="server-ticket-debugger",
    trace_id=last_run.trace_id,
))

with open("last_trace.json", "w") as f:
    json.dump([r.dict() for r in all_runs], f, indent=2, default=str)

print(f"Exported {len(all_runs)} runs to last_trace.json")