# pip install fastapi "uvicorn[standard]"
import asyncio
import json
import logging
import threading
from typing import AsyncGenerator
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

load_dotenv()

from app.graphs.standard_diagnostics_graph import build_standard_diagnostics_graph
from app.graphs.audit_group.audit_group import build_audit_graph
from app.models.models import IdealState, LLMDeduplicationResults, QueryJudgement
from app.state.graph_state import MainState, AuditState
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Server Ticket Debugger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    cluster_id: str


class AuditRequest(BaseModel):
    cluster_id: str
    query: str = ""


def make_serializable(obj):
    if isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        return make_serializable(obj.model_dump())
    if hasattr(obj, "dict"):
        return make_serializable(obj.dict())
    return obj


def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/run")
async def run_endpoint(request: RunRequest):
    return StreamingResponse(
        run_stream(request.cluster_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def run_stream(cluster_id: str) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def put(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def run_graph():
        try:
            request_id = str(uuid4())
            initial_state: MainState = {
                "request_id": request_id,
                "cluster_id": cluster_id,
                "graph_type": "tests",
                "status": f"Initializing Ticket Generator for Cluster {cluster_id}",
                "server_states": {},
                "ideal_state": IdealState(
                    expected_nginx_version="",
                    expected_nginx_status="",
                    expected_app_status="",
                    expected_message="",
                ),
                "aggregated_issues_count": 0,
                "aggregated_issues": [],
                "post_llm_filter_issues_count": 0,
                "post_llm_filter_issues": LLMDeduplicationResults(results=[]),
                "tickets_created": [],
            }
            config: RunnableConfig = {
                "metadata": {"request_id": request_id},
                "configurable": {"thread_id": request_id},
            }

            checkpointer = MemorySaver()
            graph = build_standard_diagnostics_graph(checkpointer)

            prev = {
                "status": initial_state["status"],
                "aggregated_issues_count": 0,
                "post_llm_filter_issues_count": 0,
            }
            state = initial_state

            for state in graph.stream(initial_state, config, stream_mode="values"):
                update = {}
                for key in ("status", "aggregated_issues_count", "post_llm_filter_issues_count"):
                    val = state.get(key)
                    if val != prev.get(key):
                        update[key] = val
                        prev[key] = val
                if update:
                    put(("update", update))

            tickets = make_serializable(state.get("tickets_created", []))
            put(("complete", {
                "tickets_created": tickets,
                "aggregated_issues_count": prev.get("aggregated_issues_count", 0),
                "post_llm_filter_issues_count": prev.get("post_llm_filter_issues_count", 0),
                "status": prev.get("status", "Run complete."),
                "last_run_count": len(tickets),
            }))
        except Exception as exc:
            logger.exception("Graph execution error")
            put(("error", str(exc)))

    threading.Thread(target=run_graph, daemon=True).start()
    yield sse({"type": "started", "cluster_id": cluster_id})

    while True:
        kind, data = await queue.get()
        if kind == "update":
            yield sse({"type": "update", **data})
        elif kind == "complete":
            yield sse({"type": "complete", **data})
            break
        elif kind == "error":
            yield sse({"type": "error", "message": data})
            break


@app.post("/audit")
async def audit_endpoint(request: AuditRequest):
    return StreamingResponse(
        audit_stream(request.cluster_id, request.query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def audit_stream(cluster_id: str, query: str) -> AsyncGenerator[str, None]:
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def put(item):
        loop.call_soon_threadsafe(queue.put_nowait, item)

    def run_graph():
        try:
            request_id = str(uuid4())
            initial_state: AuditState = {
                "request_id": request_id,
                "cluster_id": cluster_id,
                "graph_type": "audit",
                "query": query,
                "query_judgement": QueryJudgement(
                    is_valid=False,
                    explanation=""
                ),
                "server_states": {},
                "ideal_state": IdealState(
                    expected_nginx_version="",
                    expected_nginx_status="",
                    expected_app_status="",
                    expected_message="",
                ),
                "status": f"Initializing audit for Cluster {cluster_id}",
                "issues": [],
                "tickets_created": [],
            }
            config: RunnableConfig = {
                "metadata": {"request_id": request_id},
                "configurable": {"thread_id": request_id},
            }

            checkpointer = MemorySaver()
            graph = build_audit_graph(checkpointer)

            prev_status = initial_state["status"]
            prev_issues_count = 0
            state = initial_state

            for state in graph.stream(initial_state, config, stream_mode="values"):
                update = {}
                val = state.get("status")
                if val != prev_status:
                    prev_status = val
                    update["status"] = val
                issues_count = len(state.get("issues", []))
                if issues_count != prev_issues_count:
                    prev_issues_count = issues_count
                    update["issues_count"] = issues_count
                if update:
                    put(("update", update))

            tickets = make_serializable(state.get("tickets_created", []))
            query_judgement = state.get("query_judgement")

            explanation = query_judgement.explanation if query_judgement else None
            if explanation is None:
                snapshot = graph.get_state(config)
                for task in snapshot.tasks:
                    for intr in task.interrupts:
                        if isinstance(intr.value, dict):
                            explanation = intr.value.get("message")
                        if explanation:
                            break

            put(("complete", {
                "tickets_created": tickets,
                "issues_count": prev_issues_count,
                "status": prev_status,
                "query_explanation": explanation,
            }))
        except Exception as exc:
            logger.exception("Audit graph execution error")
            put(("error", str(exc)))

    threading.Thread(target=run_graph, daemon=True).start()
    yield sse({"type": "started", "cluster_id": cluster_id})

    while True:
        kind, data = await queue.get()
        if kind == "update":
            yield sse({"type": "update", **data})
        elif kind == "complete":
            yield sse({"type": "complete", **data})
            break
        elif kind == "error":
            yield sse({"type": "error", "message": data})
            break


@app.get("/health")
async def health():
    return {"ok": True}
