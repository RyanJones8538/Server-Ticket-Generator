import logging

from app.models.models import DeduplicationEntry
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

def deterministic_deduplicate(state: DeduplicationEntry) -> dict:
    """
    Performs deduplication of potential tickets against existing tickets in a deterministic fashion.
    Args:
        state: The state of the graph.
    Returns:
        post_deterministic_filter_issues: List of issues that survive the filter
        post_deterministic_filter_issues_count: Number of issues that survive the filter (aggregated through annotation)
        status: The status of the graph.
    """
    existing_tickets = state["existing_tickets"]
    affected_servers = state["candidate_ticket"]["affected_servers"]
    issue = state["candidate_ticket"]["issue"]

    SIMILARITY_THRESHOLD = 85

    logger.info("Starting deterministic deduplicate. Issue: %s", issue)

    scores = [
        (fuzz.token_set_ratio(issue, t.issue), t)
        for t in existing_tickets
    ]

    passing_scores = [
        score for score, t in scores
        if score >= SIMILARITY_THRESHOLD
        and set(affected_servers) <= set(t.affected_servers)
    ]

    is_duplicate = bool(passing_scores)
    best_score = max(passing_scores, default=0.0)

    logger.info("Deterministic deduplication finished. Is_duplicate: %s, best_score: %s", is_duplicate, best_score)

    if not is_duplicate:
        return {
            "post_deterministic_filter_issues": [{**state["candidate_ticket"], "similarity": best_score}],
            "post_deterministic_filter_issues_count": 1,
            "status": "Performed deterministic deduplication."
        }

    return {
        "status": "Performed deterministic deduplication."
    }