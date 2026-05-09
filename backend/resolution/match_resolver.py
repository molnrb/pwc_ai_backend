"""
Match resolver — selects the best evidence candidate for each normalized claim.

Implements tie-handling, confidence thresholds, and review-required decisions.
Low-confidence matches result in grey + review, never forced claims.
"""

from __future__ import annotations

import logging
from typing import Optional

from models.audit_types import (
    NormalizedClaim,
    EvidenceCandidate,
    EvidenceMatch,
    ValidationResult,
)
from ontology.loader import get_ontology

logger = logging.getLogger("atlas.resolution")

_ontology = get_ontology()

# Thresholds
TOP_SCORE_MINIMUM = 0.35  # Below this, don't even attempt matching
REVIEW_SCORE_THRESHOLD = 0.5  # Below this, force review


def resolve_best_match(
    claim: NormalizedClaim,
    evidence_candidates: list[EvidenceCandidate],
) -> Optional[EvidenceMatch]:
    """Select the best evidence candidate for a claim.

    Returns None if no candidate reaches the minimum threshold.
    """
    if not evidence_candidates:
        logger.debug("No evidence candidates for %s", claim.data_point_id)
        return None

    # Filter by minimum threshold
    viable = [c for c in evidence_candidates if c.retrieval_confidence >= TOP_SCORE_MINIMUM]
    if not viable:
        logger.debug(
            "All %d evidence candidates below threshold (%.2f) for %s",
            len(evidence_candidates), TOP_SCORE_MINIMUM, claim.data_point_id,
        )
        return None

    # Sort by confidence descending
    viable.sort(key=lambda c: c.retrieval_confidence, reverse=True)
    best = viable[0]

    # Tie detection
    is_tie = False
    if len(viable) > 1:
        second = viable[1]
        score_diff = best.retrieval_confidence - second.retrieval_confidence
        if score_diff < 0.05:  # Close scores → tie
            is_tie = True

    # Decision
    decision = "selected"
    reason = None
    if best.retrieval_confidence < REVIEW_SCORE_THRESHOLD:
        decision = "selected"  # Still selected, but flagged for review downstream
        reason = f"Low retrieval confidence ({best.retrieval_confidence:.2f})"
    if is_tie:
        decision = "tie"
        reason = (
            f"Tie with next candidate (score diff < 0.05). "
            f"Selected top: {best.retrieval_confidence:.2f}"
        )

    match = EvidenceMatch(
        claim_id=claim.claim_id,
        evidence_id=best.evidence_id,
        score=best.retrieval_confidence,
        decision=decision,
        reason=reason,
    )
    return match


def apply_match(
    claim: NormalizedClaim,
    evidence: EvidenceCandidate,
    match: EvidenceMatch,
) -> ValidationResult:
    """Create a pre-validation result from a resolved match.

    This does NOT run the deterministic math — it only sets up the
    ValidationResult with provenance and confidence. The validation_engine
    runs the actual number comparison.
    """
    dp_def = _ontology.get_data_point(claim.data_point_id)
    green_threshold = 0.005
    if dp_def:
        green_threshold = dp_def.validation_thresholds.green_threshold

    review_required = match.score < REVIEW_SCORE_THRESHOLD or match.decision == "tie"

    return ValidationResult(
        data_point=claim.data_point_id,
        claimed_value=claim.value,
        source_value=evidence.normalized_value,
        unit=claim.unit,
        flag="grey",  # Will be updated by validation_engine
        deviation_pct=None,
        green_threshold=green_threshold,
        explanation="",
        provenance={
            "claim_id": claim.claim_id,
            "evidence_id": evidence.evidence_id,
            "match_score": match.score,
            "match_decision": match.decision,
            "retrieval_confidence": evidence.retrieval_confidence,
            "evidence_location": evidence.location,
            "evidence_file": evidence.file_name,
        },
    )


def resolve_for_claims(
    claims: list[NormalizedClaim],
    all_evidence: dict[str, list[EvidenceCandidate]],  # claim_id → candidates
) -> dict[str, tuple[EvidenceMatch, EvidenceCandidate] | None]:
    """Resolve evidence matches for all claims at once."""
    resolved: dict[str, tuple[EvidenceMatch, EvidenceCandidate] | None] = {}
    for claim in claims:
        candidates = all_evidence.get(claim.claim_id, [])
        match = resolve_best_match(claim, candidates)
        if match is None:
            resolved[claim.claim_id] = None
            continue
        # Find the matching evidence candidate
        evidence = next((c for c in candidates if c.evidence_id == match.evidence_id), None)
        if evidence is None:
            resolved[claim.claim_id] = None
        else:
            resolved[claim.claim_id] = (match, evidence)
    return resolved