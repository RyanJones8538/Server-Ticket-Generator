from typing import Annotated, Optional, TypedDict

from langgraph.graph import add_messages

from app.models.models import AggregatedIssue, IdealState, IssueFindings, IssueLLMOutput, LLMDeduplicationResults, QueryJudgement, merge_issues, ServerState, TicketOutput

import operator

class MainState(TypedDict):
    request_id: str
    cluster_id: str
    status: str
    graph_type: str
    server_states: Annotated[dict[str, ServerState], operator.or_]
    ideal_state: IdealState
    aggregated_issues_count: int
    aggregated_issues: list[AggregatedIssue]
    post_llm_filter_issues_count: int
    post_llm_filter_issues: LLMDeduplicationResults
    tickets_created: list[TicketOutput]

class CollectState(TypedDict):
    request_id: str
    cluster_id: str
    status: str
    server_states: Annotated[dict[str, ServerState], operator.or_]
    ideal_state: IdealState

class DiagnosticsState(TypedDict):
    request_id: str
    cluster_id: str
    status: Annotated[str, lambda _, b: b]
    server_states: Annotated[dict[str, ServerState], operator.or_]
    ideal_state: IdealState
    routing_flags: Annotated[dict[str, list[str]], merge_issues]
    raw_issues: Annotated[dict[str, list[str]], merge_issues]
    aggregated_issues_count: int
    aggregated_issues: list[AggregatedIssue]

class DeduplicateState(TypedDict):
    request_id: str
    cluster_id: str
    status: Annotated[str, lambda _, b: b]
    aggregated_issues_count: int
    aggregated_issues: list[AggregatedIssue]
    existing_tickets: list[TicketOutput]
    post_deterministic_filter_issues_count: Annotated[int, operator.add]
    post_deterministic_filter_issues: Annotated[list[AggregatedIssue], operator.add]
    post_llm_filter_issues_count: int
    post_llm_filter_issues: LLMDeduplicationResults

class WriterState(TypedDict):
    request_id: str
    cluster_id: str
    status: Annotated[str, lambda _, b: b]
    post_llm_filter_issues_count: int
    post_llm_filter_issues: LLMDeduplicationResults
    tickets_created: Annotated[list[TicketOutput], operator.add]

class StatusCheckState(TypedDict):
    request_id: str
    status: Annotated[str, lambda _, b: b]
    server: ServerState
    ideal: IdealState
    routing_flags: Annotated[dict[str, list[str]], merge_issues]
    raw_issues: Annotated[dict[str, list[str]], merge_issues]

class StatusCheckStateOutput(TypedDict):
    routing_flags: Annotated[dict[str, list[str]], merge_issues]
    raw_issues: Annotated[dict[str, list[str]], merge_issues]
    status: str

class AuditState(TypedDict):
    request_id: str
    cluster_id: str
    graph_type: str
    query: str
    query_judgement: Optional[QueryJudgement]
    server_states: Annotated[dict[str, ServerState], operator.or_]
    ideal_state: IdealState
    issues: list[IssueLLMOutput]
    status: str
    tickets_created: list[TicketOutput]

class SearchIssuesState(TypedDict):
    request_id: str
    cluster_id: str
    query: str
    server_states: dict[str, ServerState]
    ideal_state: IdealState
    messages: Annotated[list, add_messages]
    issues: list[IssueLLMOutput]
    status: str

class SearchIssuesOutput(TypedDict):
    issues: list[IssueLLMOutput]
    status: str

class AuditWriterState(TypedDict):
    issues: list[IssueLLMOutput]
    tickets_created: Annotated[list[TicketOutput], operator.add]
    status: Annotated[str, lambda _, b: b]

class ParseState(TypedDict):
    request_id: str
    query: str
    query_judgement: QueryJudgement
    status: str

class StatusDiagnosticsState(TypedDict):
    request_id: str
    cluster_id: str
    status: Annotated[str, lambda _, b: b]
    server: ServerState
    ideal: IdealState
    raw_issues: Annotated[dict[str, list[str]], merge_issues]
    port_issue_found: bool
    memory_issue_found: bool

class StatusDiagnosticsStateOutput(TypedDict):
    raw_issues: Annotated[dict[str, list[str]], merge_issues]
    status: str