import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
import subprocess
import shlex
import httpx
import json

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import ALLOWED_COMMANDS, SHELL_OPERATORS, get_llm, issue_extractor_llm
from app.models.models import AggregatedIssue
from app.state.graph_state import SearchIssuesOutput, SearchIssuesState

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS=5

@tool
def read_only_shell(command: str) -> str:
    """
    Run a read-only shell command. Useful for reading config files and scripts mounted at /app/servers/.
    Args:
        command: The requested command.
    Returns: The result of that command.
    """
    if any(op in command for op in SHELL_OPERATORS):
        return "Piped or chained commands are not permitted."
    root = shlex.split(command)[0]
    if root not in ALLOWED_COMMANDS:
        return f"Command '{root}' is not permitted."
    result = subprocess.run(shlex.split(command), capture_output=True, text=True)
    return result.stdout or result.stderr

@tool
def http_probe(server_id: str, path: str = "/app") -> str:
    """
    Make a GET request to a named server container by its server_id (e.g. 'server-c1'). 
    Returns HTTP status and response body. Use path='/status' or path='/app'.
    Args: 
        server_id: id of relevant server.
        path: path of server.
    Returns:
        Result of GET request.
    """
    try:
        url = f"http://{server_id}{path}"
        response = httpx.get(url, timeout=5.0)
        return f"HTTP {response.status_code}\n{response.text[:1000]}"
    except Exception as e:
        return f"Connection error: {str(e)}"

def route_search_issues(state):
    """
    Routes to tools if the LLM made tool calls, otherwise ends the agent loop.
    The tool count limit is enforced in route_after_tools, after pending calls are executed,
    so we never leave unanswered tool_call_ids in the message history.
    Args:
        state: The state of the graph.
    Returns:
        Correct node to visit.
    """
    if tools_condition(state) == "tools":
        return "tools"
    return "issues_extractor"

def route_after_tools(state):
    """
    Routes after tool calls given. If the max has not been reached, return result to LLM.
    If it has, move on to the next node.
    Args:
        state: The state of the graph.
    Returns: 
        string corresponding to the next node to visit.
    """
    messages = state.get("messages", [])
    tool_call_count = sum(1 for m in messages if m.type == "tool")
    if tool_call_count >= MAX_TOOL_CALLS:
        return "issues_extractor"
    return "issues_agent"
    
_EXTRACTOR_BASE = (
    "Using only the diagnostic snapshot in the system message above — the entrypoint scripts, "
    "nginx config files, and HTTP responses — extract every distinct net harm. "
    "For each issue describe the ROOT CAUSE: what is in the entrypoint script or config file "
    "that produces the problem. Do not report an HTTP status code as the issue itself. "
    "Name the specific server_id(s) affected by each issue. "
    "For each issue you report, cite the specific file and line that proves the root cause. "
    "Do not generate a finding that cannot be traced to a concrete line in an entrypoint script or config file. "
    "If you observe an HTTP error but cannot find its cause in the available evidence, omit it — do not infer an explanation. "
    "Write exactly one ticket per distinct root cause. "
    "If two servers share the same underlying misconfiguration, they appear in one ticket. "
    "Each ticket must be anchored to a specific change in a specific file. "
    "Do not group two servers into one ticket unless the exact same misconfiguration appears in both their files. "
    "Different entrypoint scripts doing different things are always separate tickets. "
    "Within the same entrypoint, multiple operations that combine toward a single harmful outcome are one ticket — report the ultimate consequence as the root cause, not each operation separately."
)

def make_extractor_prompt(query: str) -> HumanMessage:
    if not query:
        return HumanMessage(_EXTRACTOR_BASE)
    return HumanMessage(
        _EXTRACTOR_BASE +
        f"\n\nCRITICAL FILTER — QUERY IN EFFECT: \"{query}\"\n"
        "1. Only extract findings that directly explain what the query describes. "
        "Discard any finding that is not clearly relevant to the query.\n"
        "2. Find the PROXIMATE cause: the specific script operation or config line that directly produces the symptom in the query. "
        "Do not report a background condition (e.g. a missing service) as the root cause if there is a more direct operation responsible.\n"
        "3. The grouping rule ('multiple operations that combine toward a single harmful outcome are one ticket') does NOT apply here. "
        "When a query is active, report each distinct mechanism separately, even if they contribute to the same surface symptom."
    )

def make_issues_extractor(llm):
    """
    Creates node to extract issues from LLM output.
    Args:
        llm: The llm used to perform the extraction.
    Returns:
        issues_extractor node.
    """
    model = llm()
    def issues_extractor(state: SearchIssuesState):
        """
        Extracts issues from LLM output.
        Args:
            state: The state of the graph.
        Returns:
            issues: List of issues discovered.
        """
        cluster_id = state["cluster_id"]
        query = state.get("query", "")
        messages = state["messages"]
        logger.info("Extracting issues. Messages: %s", messages)
        result = model.invoke(messages + [make_extractor_prompt(query)])
        aggregated_issues = [
            AggregatedIssue(
                cluster_id=cluster_id,
                issue=issue.issue,
                affected_servers=issue.affected_servers,
                similarity=0
            )
            for issue in result.findings
        ]
        logger.info("Extracted results. Issues: %s", aggregated_issues)
        return {
            "aggregated_issues": aggregated_issues,
            "aggregated_issues_count": len(aggregated_issues),
            "status": "Extracted issues from LLM output."
        }
    return issues_extractor

def collect_server_diagnostics(server_ids: list[str], cluster_id: str) -> dict:
    """
    Retrieves server diagnostics.
    Args:
        cluster_id: ID of cluster.
        server_ids: List of relevant server_ids.
    Returns:
        data output
    """
    cluster_dir = f"/app/servers/server-cluster-{cluster_id.lower()}"
    data = {}
    for server_id in server_ids:
        server_dir = f"{cluster_dir}/{server_id}"
        entry = {}

        r = subprocess.run(["ls", server_dir], capture_output=True, text=True)
        entry["files"] = r.stdout.strip() or "(none)"

        r = subprocess.run(["cat", f"{server_dir}/entrypoint.sh"], capture_output=True, text=True)
        if r.stdout:
            entry["entrypoint.sh"] = r.stdout

        r = subprocess.run(["cat", f"{server_dir}/nginx.conf.template"], capture_output=True, text=True)
        if r.stdout:
            entry["nginx.conf.template"] = r.stdout

        r = subprocess.run(["ls", "-la", f"/app/logs/{server_id}"], capture_output=True, text=True)
        if r.stdout:
            entry[f"ls -la /app/logs/{server_id}"] = r.stdout

        try:
            resp = httpx.get(f"http://{server_id}/status", timeout=5.0)
            entry["GET /status"] = f"HTTP {resp.status_code} — {resp.text[:400]}"
        except Exception as e:
            entry["GET /status"] = f"Connection error: {e}"

        try:
            resp = httpx.get(f"http://{server_id}/app", timeout=5.0)
            entry["GET /app"] = f"HTTP {resp.status_code} — {resp.text[:400]}"
        except Exception as e:
            entry["GET /app"] = f"Connection error: {e}"

        data[server_id] = entry
    return data


def make_issues_agent(llm, tools):
    """
    Factory function to build the issues_agent node, which queries a collection of servers with read-only bash commands using a tool.
    Args:
        llm: The language model used by the agent
        tools: The bash tool
    Returns:
        issues_agent node
    """
    llm_with_tools = llm().bind_tools(tools)
    def issues_agent(state: SearchIssuesState):
        """
        Searches a cluster of servers for issues. Can be used with or without a user-prompt.
        Args: 
            state: The state of the graph.
        Returns:
            messages: The output of the LLM.
            status: The status of the graph.
        """
        messages = state.get("messages", [])

        logger.info("Starting issues_agent. Messages: %s", len(messages))

        if not messages:
            query = state.get("query", "")
            cluster_id = state["cluster_id"]
            server_states = state["server_states"]
            ideal_state = state["ideal_state"]
            diagnostics = collect_server_diagnostics(list(server_states.keys()), cluster_id)

            scope_section = (
                "## Investigation Scope\n"
                "Perform a general audit covering all common failure modes."
                if not query else
                f"## Investigation Scope — STRICT CONSTRAINT\n"
                f"Your investigation is strictly limited to: \"{query}\".\n"
                f"Do NOT investigate, analyse, or report any issue outside this scope, even if it appears significant.\n"
                f"When the query describes a symptom (e.g. a file filling up, errors appearing), "
                f"trace it to the most PROXIMATE cause: the specific script line or operation that directly produces the symptom. "
                f"A background condition that merely enables the symptom (e.g. a missing service) is not the finding — "
                f"the operation that actively triggers the symptom is."
            )
            system_message = SystemMessage(f"""You are a systems reliability engineer auditing the servers of cluster {cluster_id}.

                    {scope_section}

                    Server states (from the monitoring system): {server_states}
                    Ideal configuration: {ideal_state}

                    ## Pre-collected diagnostic snapshot

                    The following data has already been gathered for every server in the cluster. Analyse it to identify issues, then use the available tools to investigate further if needed.

                    {json.dumps(diagnostics, indent=2)}

                    For each server, list every deviation from the ideal state across all its files. 
                    Then, for each deviation, ask: does this change produce harm on its own, or does its effect depend on one or more of the other deviations on this server? 
                    Group deviations that only produce harm in combination into a single finding. 
                    Name the finding by the net observable harm to users or operators, not by the mechanism that causes it.

                    Before treating any deviation as a standalone finding, ask: if this deviation were removed, would any other deviation on this server become pointless or significantly less harmful? 
                    If yes, group them into one finding named by the net harm to users or operators, not by the mechanism. 
                    Only report a deviation separately if it produces distinct harm regardless of what else is present on the server.


                    ## Tool constraints
                    read_only_shell allows: {", ".join(sorted(ALLOWED_COMMANDS))}
                    Shell operators NOT allowed: {", ".join(sorted(SHELL_OPERATORS))}
                    """)
            messages = [system_message]
            response = llm_with_tools.invoke(messages)
            
            logger.info("Finished issues_agent iteration. Response: %s", response)

            return {
                "messages": [system_message, response],
                "status": "Searching for issues."
            }

        response = llm_with_tools.invoke(messages)

        logger.info("Finished issues_agent iteration. Response: %s", response)

        return {
            "messages": [response],
            "status": "Searching for issues."
        }
    return issues_agent

def build_search_issues_graph():
    """
    Builds the search issues subgraph, which uses an LLM with tool use to make calls to servers and evaluate the output.
    Args: 
        llm: The language model used for the graph
    Returns:
        The search issues subgraph
    """

    tools = [read_only_shell, http_probe]
    tool_node = ToolNode(tools)

    issues_graph = StateGraph(SearchIssuesState, output_schema=SearchIssuesOutput)
    issues_graph.add_node("issues_agent", make_issues_agent(get_llm, tools))
    issues_graph.add_node("tools", tool_node)
    issues_graph.add_node("issues_extractor", make_issues_extractor(issue_extractor_llm))

    issues_graph.add_edge(START, "issues_agent")
    issues_graph.add_conditional_edges("issues_agent", route_search_issues)
    issues_graph.add_conditional_edges("tools", route_after_tools)
    issues_graph.add_edge("issues_extractor", END)

    return issues_graph.compile()
    