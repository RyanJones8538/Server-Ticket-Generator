import json

from app.models.models import LLMDeduplicationResults
from app.state.graph_state import DeduplicateState


def make_llm_deduplicate(llm):
    """
    Wrapper function for llm deduplication.
    Args: 
        get_llm: LLM with AggregatedIssue structured output.
    Returns:
        llm_deduplicate node.
    """
    def llm_deduplicate(state: DeduplicateState):
        """
        Function to compare a set of AggregatedIssues against a record of existing help desk tickets to prevent duplicate issues being raised.
        Args:
            state: DeduplicateState
        Returns: 
            A list of entries, each containing the potential ticket, the LLM's duplicate evaluation, and the explanation for the decision.
        """
        model = llm()

        existing_tickets = state["existing_tickets"]
        post_deterministic_filter_issues = state["post_deterministic_filter_issues"]

        existing_tickets_json = json.dumps([t.model_dump() for t in existing_tickets], indent=2)
        candidates_json = json.dumps(post_deterministic_filter_issues, indent=2)

        prompt = f"""
            You are evaluating a selection of potential tickets against the collection of existing tickets for a given cluster of servers.
            Evaluate whether or not you think each ticket is a duplicate.

            Potential Tickets: {candidates_json}

            Existing Tickets: {existing_tickets_json}

            For each potential ticket, evaluate whether it is a duplicate of any existing ticket and explain your reasoning.

            By duplicate, I refer to two tickets with identical issues. To be a duplicate, the potential ticket's affected servers
            must be a subset of the existing ticket's. If the potential ticket's servers are not a subset, the ticket is not a duplicate.

            In your response, reproduce the issue text exactly as it appears in hte potential ticket.
        """

        result = model.invoke(prompt)
        number_of_non_duplicates_found = sum(not d.is_duplicate for d in result.results)

        return {
            "post_llm_filter_issues_count": number_of_non_duplicates_found,
            "post_llm_filter_issues": result,
            "status": "Performed LLM deduplication."
        }

    return llm_deduplicate