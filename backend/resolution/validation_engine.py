"""
Deterministic validation engine — pure Python math, no LLM.

Takes ValidationResult objects from the match resolver and computes
deviations, flags, and explanations. Strict separation: LLM never computes
final deviation numbers.
"""

from __future__ import annotations

import logging
from typing import Optional

from models.audit_types import (
    ValidationResult,
    AuditFinding,
    NormalizedClaim,
    EvidenceCandidate,
)
from ontology.loader import get_ontology

logger = logging.getLogger("atlas.validation")

_ontology = get_ontology()


def validate(
    claim: NormalizedClaim,
    evidence: Optional[EvidenceCandidate] = None,
    pre_result: Optional[ValidationResult] = None,
) -> AuditFinding:
    """Run deterministic validation on a claim-evidence pair.

    This is the ONLY place where deviation is computed. LLM modules feed into
    the pipeline, but the final math lives here.

    Args:
        claim: The normalized claim from the PDF.
        evidence: Optional resolved evidence candidate (None = no source).
        pre_result: Optional pre-built ValidationResult from match_resolver.

    Returns:
        AuditFinding with flag, deviation, confidence, explanation, and provenance.
    """
    dp_def = _ontology.get_data_point(claim.data_point_id)

    # Base flags and thresholds
    green_threshold = 0.005
    yellow_threshold = 0.05
    allow_missing_source = False
    if dp_def:
        green_threshold = dp_def.validation_thresholds.green_threshold
        yellow_threshold = dp_def.validation_thresholds.yellow_threshold
        allow_missing_source = dp_def.validation_thresholds.allow_missing_source

    # Build provenance
    provenance = {
        "claim_id": claim.claim_id,
        "data_point_id": claim.data_point_id,
        "period": claim.period,
        "canonical_reason": claim.canonical_reason,
    }
    if pre_result and pre_result.provenance:
        provenance.update(pre_result.provenance)

    # If no evidence candidate — grey or exception
    if evidence is None:
        is_grey = (
            not allow_missing_source
            or (pre_result is not None and pre_result.flag == "grey")
        )
        if allow_missing_source:
            # Explicitly acceptable missing source
            return AuditFinding(
                data_point=claim.data_point_id,
                claimed_value=claim.value,
                source_value=None,
                unit=claim.unit,
                flag="grey",
                deviation_pct=None,
                extraction_confidence=claim.extraction_confidence,
                mapping_confidence=claim.mapping_confidence,
                retrieval_confidence=0.0,
                review_required=True,
                explanation=f"No source document available for '{claim.data_point_id}'. "
                f"Manual verification required — auditor must locate supporting documentation.",
                provenance=provenance,
                review_reason="missing_source",
            )
        return AuditFinding(
            data_point=claim.data_point_id,
            claimed_value=claim.value,
            source_value=None,
            unit=claim.unit,
            flag="grey",
            deviation_pct=None,
            extraction_confidence=claim.extraction_confidence,
            mapping_confidence=claim.mapping_confidence,
            retrieval_confidence=pre_result.provenance.get("retrieval_confidence", 0.0) if pre_result else 0.0,
            review_required=True,
            explanation=f"No matching evidence found for '{claim.data_point_id}'. "
            f"Manual verification required.",
            provenance=provenance,
            review_reason="no_evidence_match",
        )

    # ── Evidence exists — run the math ────────────────────────────

    claimed_val = _coerce_numeric(claim.value)
    source_val = _coerce_numeric(evidence.normalized_value)

    if source_val is None or source_val == 0:
        zero_handling = dp_def.validation_thresholds.source_value_zero_handling if dp_def else "red"
        if zero_handling == "grey":
            return AuditFinding(
                data_point=claim.data_point_id,
                claimed_value=claimed_val,
                source_value=source_val,
                unit=claim.unit,
                flag="grey",
                deviation_pct=None,
                extraction_confidence=claim.extraction_confidence,
                mapping_confidence=claim.mapping_confidence,
                retrieval_confidence=evidence.retrieval_confidence,
                review_required=True,
                explanation=f"Source value is zero or missing — cannot compute deviation. "
                f"Claimed: {claimed_val} {claim.unit or ''}. Manual review required.",
                provenance=provenance,
                review_reason="source_zero",
            )
        return AuditFinding(
            data_point=claim.data_point_id,
            claimed_value=claimed_val,
            source_value=source_val,
            unit=claim.unit,
            flag="red",
            deviation_pct=100.0,
            extraction_confidence=claim.extraction_confidence,
            mapping_confidence=claim.mapping_confidence,
            retrieval_confidence=evidence.retrieval_confidence,
            review_required=True,
            explanation=f"Source value is zero — cannot compute deviation. "
            f"Claimed: {claimed_val} {claim.unit or ''}. Requires immediate auditor investigation.",
            provenance=provenance,
            review_reason="source_zero",
        )

    # Compute deviation
    deviation = abs(claimed_val - source_val) / abs(source_val)
    deviation_pct = round(deviation * 100, 2)

    # Determine flag
    if deviation < green_threshold:
        flag = "green"
    elif deviation <= yellow_threshold:
        flag = "yellow"
    else:
        flag = "red"

    # Review required?
    review_required = flag == "red"
    if claim.extraction_confidence < 0.4 or claim.mapping_confidence < 0.4 or evidence.retrieval_confidence < 0.4:
        review_required = True

    explanation = (
        f"Claimed: {claimed_val} {claim.unit or ''}, "
        f"Source: {source_val} {claim.unit or ''}, "
        f"Deviation: {deviation_pct}%"
    )

    return AuditFinding(
        data_point=claim.data_point_id,
        claimed_value=claimed_val,
        source_value=source_val,
        unit=claim.unit,
        flag=flag,
        deviation_pct=deviation_pct,
        extraction_confidence=claim.extraction_confidence,
        mapping_confidence=claim.mapping_confidence,
        retrieval_confidence=evidence.retrieval_confidence,
        review_required=review_required,
        explanation=explanation,
        provenance=provenance,
        source_file=evidence.file_name,
        source_sheet=evidence.location.get("sheet"),
        source_cell=str(evidence.location.get("cell_ref") or evidence.location.get("column", "")),
        review_reason="low_confidence" if (
            claim.extraction_confidence < 0.4 or claim.mapping_confidence < 0.4 or evidence.retrieval_confidence < 0.4
        ) else None,
    )


def validate_all(
    claims: list[NormalizedClaim],
    resolved: dict[str, Optional[EvidenceCandidate]],
) -> list[AuditFinding]:
    """Run validation across all claims.

    Args:
        claims: All normalized claims.
        resolved: Mapping of claim_id → evidence (None = no evidence found).

    Returns:
        List of AuditFinding objects.
    """
    findings: list[AuditFinding] = []
    for claim in claims:
        evidence = resolved.get(claim.claim_id)
        finding = validate(claim, evidence)
        findings.append(finding)
    return findings


# ── helpers ──────────────────────────────────────────────────────────


def _coerce_numeric(value) -> float:
    """Safely convert any value to float for math comparison."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).strip().replace(",", "").replace(" ", "").replace("%", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0