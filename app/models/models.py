from typing import TypedDict

from pydantic import BaseModel, Field

def merge_issues(
    a: dict[str, list[str]], b: dict[str, list[str]]
) -> dict[str, list[str]]:
    result = dict(a)
    for issue, servers in b.items():
        result.setdefault(issue, []).extend(servers)
    return result

class AggregatedIssue(TypedDict):
    cluster_id: str
    affected_servers: list[str]
    issue: str
    similarity: float

class LLMDeduplicationDecision(BaseModel):
    potential_ticket: AggregatedIssue = Field(description="The potential ticket, exactly as provided to the deduplication LLM.")
    is_duplicate: bool = Field(description="LLM's determination of whether potential_ticket is a duplicate or not. True if duplicate, False if not.")
    explanation: str = Field(description="LLM's reasoning for evaluating potential_ticket's deduplication status.")

class LLMDeduplicationResults(BaseModel):
    results: list[LLMDeduplicationDecision] = Field(description="List of decisions made by the LLM deduplication process.")

class LLMDiagnosticsOutput(BaseModel):
    issue_found: bool = Field(description="True if a configuration issue was found.")
    issue: str = Field(description="Precise description of the issue, or empty string.")

class MergedIssue(BaseModel):
    """Part of Aggregate's output, an individual issue."""
    issue: str = Field(description="Individual issue, precisely described to a degree where a solution and description can be generated from it.")
    affected_servers: list[str] = Field(description="List of servers affected by the issue.")

class AggregationResult(BaseModel):
    "Part of Aggregate's output, a list of issues."
    merged_issues: list[MergedIssue] = Field(description="List of issues found.")

class QueryJudgement(BaseModel):
    is_valid: bool = Field(description="Determination of whether or not query is valid input.")
    explanation: str = Field(description="User-facing message explaining judgement.")

class IssueLLMOutput(BaseModel):
    cluster_id: str = Field(description="Id of cluster to examine.")
    affected_servers: list[str] = Field(description="List of server_ids of all servers affected by a given issue.")
    issue: str = Field(description="Description of the issue. Make it specific enough for a future LLM to use it to generate a longer description and solution in code.")

class IssueFindings(BaseModel):
    findings: list[IssueLLMOutput] = Field(description="All distinct issues found across the servers.")

class ResourcesState(TypedDict):
    cpu_usage_percent: float
    memory_usage_percent: float

class ServerDiagnosticsConfig(TypedDict):
    upstream_timeout_seconds: int
    keepalive_connections: int

class NginxState(TypedDict):
    installed: bool
    version: str
    status: str

class PortsState(TypedDict):
    http: int

class ServerState(TypedDict):
    server_id: str
    cluster: str
    hostname: str
    app_status: str
    message: str
    nginx: NginxState
    ports: PortsState
    app_port_open: bool
    resources: ResourcesState
    diagnostics_config: ServerDiagnosticsConfig

class IdealState(TypedDict):
    expected_nginx_version: str
    expected_nginx_status: str
    expected_app_status: str
    expected_message: str

class TicketOutput(BaseModel):
    ticket_id: str = Field("ID of ticket.")
    cluster: str = Field("Cluster in which servers are located.")
    issue: str = Field(description="Issue provided in AggregatedIssue, the output of the unit test.")
    description: str = Field(description="Issue described in human-readable language.")
    affected_servers: list[str] = Field(description="List of IDs of affected servers.")
    severity: int = Field(..., ge=1, le=5, description="Numerical representation of the severity of the issue.")
    remediation: str = Field(description="Precise instructions to rectify the ticket's issue.")

class DeduplicationEntry(TypedDict):
    candidate_ticket: AggregatedIssue
    existing_tickets: list[TicketOutput]