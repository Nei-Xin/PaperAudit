from __future__ import annotations

from collections.abc import Sequence
from .hy3_client import Hy3Client, Hy3ResponseError
from .models import (
    EvidenceAnchor,
    PeerReviewReport,
    RebuttalItem,
    ReviewConcern,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    IssueSupportType,
    ParsedPaper,
    PeerReviewVenue,
    RelatedWorkComparison,
    RelatedWorkReference,
    ReviewSeverity,
)
from .peer_review_rules import (
    peer_review_rubric_metadata,
    normalize_peer_review_weights,
    recalculate_peer_review,
    peer_review_consistency_warnings,
    _dedupe_review_concerns,
    _concern_consistency_warnings,
)
from .evidence import (
    _neighbor_context,
    _validated_evidence_quote,
    _quote_rects,
    _evidence_locator,
)


class PeerReviewService:
    """Peer review generation and author-response assessment using a shared client."""

    def __init__(self, client: Hy3Client):
        self.client = client

    def generate_peer_review(
        self,
        paper: ParsedPaper,
        *,
        venue: PeerReviewVenue = PeerReviewVenue.GENERAL,
        rubric_weights: dict[str, float] | None = None,
    ) -> PeerReviewReport:
        """Generate a venue-agnostic simulated peer review with locally verified evidence."""
        normalized_weights = normalize_peer_review_weights(rubric_weights)
        if venue == PeerReviewVenue.GENERAL and not rubric_weights:
            generated = self.client.generate_peer_review(paper.title, paper.chunks)
        else:
            generated = self.client.generate_peer_review(
                paper.title,
                paper.chunks,
                venue=venue,
                rubric_weights=normalized_weights,
            )
        rubric_version, rubric_updated_at, rubric_change_note = peer_review_rubric_metadata(
            venue, normalized_weights
        )
        chunk_map = {chunk.chunk_id: chunk for chunk in paper.chunks}
        chunk_positions = {chunk.chunk_id: index for index, chunk in enumerate(paper.chunks)}
        invalid_evidence_count = 0

        def enrich(anchors: Sequence[EvidenceAnchor]) -> list[EvidenceAnchor]:
            nonlocal invalid_evidence_count
            result: list[EvidenceAnchor] = []
            seen: set[str] = set()
            for anchor in anchors[:3]:
                if anchor.chunk_id in seen:
                    continue
                chunk = chunk_map.get(anchor.chunk_id)
                if chunk is None:
                    continue
                quote = _validated_evidence_quote(anchor.quote, chunk.content) if anchor.quote else None
                if not quote:
                    invalid_evidence_count += 1
                    continue
                result.append(
                    EvidenceAnchor(
                        chunk_id=chunk.chunk_id,
                        page=chunk.page,
                        text=chunk.content,
                        quote=quote,
                        locator=_evidence_locator(chunk.chunk_id, paper.chunks, chunk_positions),
                        rects=_quote_rects(chunk, quote),
                        context_text=_neighbor_context(chunk.chunk_id, paper.chunks, chunk_positions),
                    )
                )
                seen.add(anchor.chunk_id)
            return result

        dimensions = [item.model_copy(update={"evidence": enrich(item.evidence)}) for item in generated.dimensions[:6]]

        def normalize_concern(item: ReviewConcern) -> tuple[ReviewConcern, list[str]]:
            evidence = enrich(item.evidence)
            updates: dict[str, object] = {"evidence": evidence}
            raw_category = getattr(item, "category", IssueCategory.OTHER)
            try:
                category = raw_category if isinstance(raw_category, IssueCategory) else IssueCategory(str(raw_category))
            except (TypeError, ValueError):
                category = IssueCategory.OTHER
                updates["ai_category"] = IssueCategory.OTHER
                updates["status"] = IssueStatus.NEEDS_REVIEW
            updates["category"] = category
            raw_level = getattr(item, "severity_level", None)
            try:
                level = raw_level if isinstance(raw_level, IssueSeverity) else IssueSeverity(str(raw_level))
            except (TypeError, ValueError):
                level = IssueSeverity.MAJOR if item.severity == ReviewSeverity.MAJOR else IssueSeverity.MINOR
                updates["status"] = IssueStatus.NEEDS_REVIEW
            updates["severity_level"] = level
            try:
                confidence = int(item.confidence)
            except (TypeError, ValueError):
                confidence = 2
                updates["status"] = IssueStatus.NEEDS_REVIEW
            confidence = max(1, min(5, confidence))
            updates["confidence"] = confidence
            checked = item.model_copy(update={
                "evidence": evidence,
                "category": category,
                "severity_level": level,
                "confidence": confidence,
            })
            concern_warnings = _concern_consistency_warnings(checked)
            if concern_warnings:
                updates.update({
                    "status": IssueStatus.NEEDS_REVIEW,
                    "confidence": min(confidence, 2),
                    "support_type": IssueSupportType.INSUFFICIENT_EVIDENCE,
                })
            # A claim labelled as an evidence gap is never strong enough to be
            # an acceptance blocker, even when the model attached a nearby
            # context quote.  Keep the original AI level for auditability but
            # expose a conservative product-facing level.
            if item.support_type == IssueSupportType.INSUFFICIENT_EVIDENCE and not evidence and level in {
                IssueSeverity.FATAL,
                IssueSeverity.MAJOR,
            }:
                updates.update({
                    "severity_level": IssueSeverity.MAJOR if level == IssueSeverity.FATAL else IssueSeverity.MINOR,
                    "severity": ReviewSeverity.MAJOR if level == IssueSeverity.FATAL else ReviewSeverity.MINOR,
                    "confidence": min(confidence, 2),
                    "status": IssueStatus.NEEDS_REVIEW,
                })
                level = IssueSeverity.MAJOR if level == IssueSeverity.FATAL else IssueSeverity.MINOR
            elif not evidence and level in {IssueSeverity.FATAL, IssueSeverity.MAJOR}:
                updates.update({
                    # An unverified P0 remains a review-required P1 for safety;
                    # an unverified P1 is conservatively capped at P2.
                    "severity_level": IssueSeverity.MAJOR if level == IssueSeverity.FATAL else IssueSeverity.MINOR,
                    "severity": ReviewSeverity.MAJOR if level == IssueSeverity.FATAL else ReviewSeverity.MINOR,
                    "confidence": min(confidence, 2),
                    "status": IssueStatus.NEEDS_REVIEW,
                    "support_type": IssueSupportType.INSUFFICIENT_EVIDENCE,
                })
            return item.model_copy(update=updates), concern_warnings

        normalized_major: list[ReviewConcern] = []
        normalized_minor: list[ReviewConcern] = []
        concern_warnings: list[str] = []
        for item in generated.major_concerns[:6]:
            normalized, warnings = normalize_concern(item)
            normalized_major.append(normalized)
            concern_warnings.extend(warnings)
        for item in generated.minor_concerns[:6]:
            normalized, warnings = normalize_concern(item)
            normalized_minor.append(normalized)
            concern_warnings.extend(warnings)
        major = _dedupe_review_concerns(normalized_major)
        minor = _dedupe_review_concerns(normalized_minor)
        if not dimensions:
            raise Hy3ResponseError("模拟评审缺少维度评分。")
        enriched = generated.model_copy(
            update={
                "paper_title": paper.title,
                "venue": venue,
                "dimensions": dimensions,
                "major_concerns": major,
                "minor_concerns": minor,
                "rubric_version": rubric_version,
                "rubric_updated_at": rubric_updated_at,
                "rubric_change_note": rubric_change_note,
                "rubric_weights": normalized_weights,
                "model_raw_score": generated.overall_score,
                "questions_for_authors": [],
                "review_limitations": list(dict.fromkeys([
                    *generated.review_limitations,
                    "本评审仅基于上传论文文本；代码、完整附录、数据泄漏和未报告实验无法独立验证。",
                ])),
                "parse_warnings": [
                    *paper.warnings,
                    *concern_warnings,
                    *(["部分评审证据缺少可逐字核验的原文引文，已移除并标记为需人工复核。"] if invalid_evidence_count else []),
                ],
            }
        )
        enriched = recalculate_peer_review(enriched, normalized_weights)
        consistency_warnings = peer_review_consistency_warnings(enriched)
        return enriched.model_copy(
            update={
                "parse_warnings": list(dict.fromkeys(
                    [*enriched.parse_warnings, *consistency_warnings]
                ))
            }
        )

    def compare_related_work(
        self,
        paper: ParsedPaper,
        references: Sequence[RelatedWorkReference],
    ) -> RelatedWorkComparison:
        """Compare novelty only against references explicitly supplied by the user."""
        if not references:
            raise ValueError("请至少提供一条相关工作记录。")
        if len(references) > 5:
            raise ValueError("最多支持 5 条相关工作记录。")
        payload = [item.model_dump(mode="json") for item in references]
        result = self.client.compare_related_work(paper.title, paper.chunks, payload)
        return result.model_copy(update={"references": list(references)})

    def assess_rebuttal(
        self,
        report: PeerReviewReport,
        concern: ReviewConcern,
        response: str,
    ) -> RebuttalItem:
        """Ask Hy3 to classify one author response against the cited concern evidence."""
        evidence = "\n".join(
            anchor.quote or anchor.text[:600]
            for anchor in concern.evidence[:3]
        )
        draft = self.client.assess_rebuttal(
            report.paper_title,
            concern.title,
            concern.description,
            response.strip(),
            evidence,
        )
        return RebuttalItem(
            issue_id=concern.issue_id,
            concern_title=concern.title,
            response=response.strip(),
            resolution=draft.resolution,
            assessment=draft.assessment,
        )
