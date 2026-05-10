import json

from app.models.models import AggregatedIssue
from app.state.graph_state import DiagnosticsState

def make_aggregate_issues(llm):
    def aggregate_issues(state: DiagnosticsState)-> dict:
        raw_issues = state["raw_issues"]
        cluster_id = state["cluster_id"]

        length = len(raw_issues)

        if length == 0:
            return {
            "status": "Aggregating issues.",
            "aggregated_issues_count": length,
            "aggregated_issues": []
        }

        if length == 1:
            issue, affected_servers = next(iter(raw_issues.items()))
            return {
                "status": "Aggregating issues.",
                "aggregated_issues_count": length,
                "aggregated_issues": [AggregatedIssue(
                    cluster_id=cluster_id,
                    issue=issue,
                    affected_servers=affected_servers,
                    similarity=0,
                )]
            }
        
        prompt = f"""
            You are aggregating a set of server issues into a clean list of helpdesk tickets.
            The input is a dictionary where each key is an issue description and each value is a list of affected server IDs.

            Here is the input: {json.dumps(raw_issues)}

            Rules you must follow:

            1. STRICT SERVER ATTRIBUTION: A server may only appear in a merged issue's affected_servers
               if it was explicitly listed under one of the source issues being merged.
               Do not infer, extend, or add servers based on similarity, analogy, or shared symptoms.

            2. MERGING: Merge two or more issues only if they describe the same root cause and would be
               resolved by the same fix. The affected_servers of the merged result is the union of the
               affected_servers of the source issues — no more, no less.

            Return the full list of issues after applying these rules.
            """

        result = llm.invoke(prompt)

        merged_issues = result.merged_issues

        aggregated_issues = []

        for single_issue in merged_issues:
            aggregated_issues.append(AggregatedIssue(
                cluster_id=cluster_id,
                issue=single_issue.issue,
                affected_servers=single_issue.affected_servers,
                similarity=0,
            ))


        count = len(aggregated_issues)
        
        return {
            "status": "Aggregating issues.",
            "aggregated_issues_count": count,
            "aggregated_issues": aggregated_issues
        }
    return aggregate_issues