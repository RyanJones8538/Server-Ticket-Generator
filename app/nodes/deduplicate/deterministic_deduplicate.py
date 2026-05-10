from app.models.models import DeduplicationEntry
from rapidfuzz import fuzz


def deterministic_deduplicate(state: DeduplicationEntry) -> dict:
    existing_tickets = state["existing_tickets"]
    affected_servers = state["candidate_ticket"]["affected_servers"]
    issue = state["candidate_ticket"]["issue"]

    SIMILARITY_THRESHOLD = 85

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

    if not is_duplicate:
        return {
            "post_deterministic_filter_issues": [{**state["candidate_ticket"], "similarity": best_score}],
            "post_deterministic_filter_issues_count": 1,
            "status": "Performed deterministic deduplication."
        }

    return {
        "status": "Performed deterministic deduplication."
    }