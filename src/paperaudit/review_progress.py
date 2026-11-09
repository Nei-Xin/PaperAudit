"""Stable modification-plan keys, independent of either UI and report schema."""
from hashlib import sha1
from paperaudit.models import PeerReviewReport


def plan_actions(report: PeerReviewReport) -> list[str]:
    actions = list(report.top_priorities or report.required_changes)
    if not actions:
        actions = [c.suggestion for c in [*report.major_concerns, *report.minor_concerns]
                   if c.suggestion.strip()][:3]
    return list(dict.fromkeys(actions))


def action_key(text: str) -> str:
    return sha1(text.encode('utf-8')).hexdigest()


def empty_progress(report: PeerReviewReport) -> dict:
    return dict(schema_version=1, review_generated_at=report.generated_at,
                review_run_id=report.run_id, items=[])
