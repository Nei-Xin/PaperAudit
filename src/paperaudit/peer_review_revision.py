"""Deterministic comparison helpers for asynchronous paper revisions."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from paperaudit.models import ParsedPaper, PeerReviewReport
from paperaudit.service import build_revision_diff


def build_revision_payload(
    original: ParsedPaper,
    revised: ParsedPaper,
    previous: PeerReviewReport,
    report: PeerReviewReport,
) -> dict[str, Any]:
    """Match old concerns to a new review using stable text/evidence signals."""

    old_items = [*previous.major_concerns, *previous.minor_concerns]
    new_items = [*report.major_concerns, *report.minor_concerns]

    def match_score(old_item: Any, new_item: Any) -> float:
        title_score = SequenceMatcher(
            None,
            " ".join(old_item.title.casefold().split()),
            " ".join(new_item.title.casefold().split()),
        ).ratio()
        old_evidence = {anchor.chunk_id for anchor in old_item.evidence}
        new_evidence = {anchor.chunk_id for anchor in new_item.evidence}
        evidence_score = len(old_evidence & new_evidence) / max(len(old_evidence), 1)
        category_score = 0.15 if old_item.category == new_item.category else 0.0
        return 0.65 * title_score + 0.2 * evidence_score + category_score

    matched_new: dict[str, Any] = {}
    used_new_ids: set[int] = set()
    ambiguous_matches: list[str] = []
    for old_item in old_items:
        candidates = sorted(
            (
                (match_score(old_item, item), index, item)
                for index, item in enumerate(new_items)
                if index not in used_new_ids
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        if candidates and candidates[0][0] >= 0.48:
            _, new_index, new_item = candidates[0]
            matched_new[old_item.issue_id or old_item.title] = new_item
            used_new_ids.add(new_index)
            if (
                len(candidates) > 1
                and candidates[1][0] >= 0.48
                and candidates[0][0] - candidates[1][0] < 0.08
            ):
                ambiguous_matches.append(old_item.title)

    resolved_concerns = sorted(
        item.title for item in old_items if (item.issue_id or item.title) not in matched_new
    )
    remaining_concerns = sorted(
        item.title for item in old_items if (item.issue_id or item.title) in matched_new
    )
    old_by_title = {item.title: item for item in old_items}
    resolved_issue_ids = sorted(
        old_by_title[title].issue_id
        for title in resolved_concerns
        if old_by_title[title].issue_id
    )
    remaining_issue_ids = sorted(
        old_by_title[title].issue_id
        for title in remaining_concerns
        if old_by_title[title].issue_id
    )
    matched_new_ids = {id(item) for item in matched_new.values()}
    new_concerns = sorted(item.title for item in new_items if id(item) not in matched_new_ids)
    return {
        "diff": build_revision_diff(original, revised),
        "resolved_concerns": resolved_concerns,
        "remaining_concerns": remaining_concerns,
        "resolved_issue_ids": resolved_issue_ids,
        "remaining_issue_ids": remaining_issue_ids,
        "new_concerns": new_concerns,
        "ambiguous_matches": sorted(set(ambiguous_matches)),
    }
