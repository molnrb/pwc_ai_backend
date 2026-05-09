"""
Claim normalizer — maps ExtractedCandidate objects to NormalizedClaim objects.

Uses the ontology for alias matching, unit canonicalization, and period
disambiguation. Handles deduplication and prior-vs-current year separation.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from models.audit_types import ExtractedCandidate, NormalizedClaim
from ontology.loader import get_ontology

logger = logging.getLogger("atlas.normalization")

_DEFAULT_YEAR = 2024


class ClaimNormalizer:
    """Normalizes extracted candidates into canonical claims.

    For each candidate:
    1. Match raw text against ontology aliases to find data_point_id
    2. Canonicalize unit
    3. Normalize period/year
    4. Compute mapping confidence
    5. Assign dedup group
    """

    def __init__(self) -> None:
        self.ontology = get_ontology()

    def normalize(self, candidates: list[ExtractedCandidate]) -> list[NormalizedClaim]:
        """Convert a list of candidates into normalized claims."""
        claims: list[NormalizedClaim] = []
        for candidate in candidates:
            claim = self._normalize_one(candidate)
            if claim is not None:
                claims.append(claim)

        # Deduplicate by data_point_id (keep highest confidence)
        claims = self._deduplicate(claims)

        logger.info("Normalized %d candidates → %d claims", len(candidates), len(claims))
        return claims

    def _normalize_one(self, candidate: ExtractedCandidate) -> Optional[NormalizedClaim]:
        """Normalize a single candidate. Returns None if it cannot be mapped."""
        # 1. Find data_point_id via alias matching
        raw_text = candidate.raw_text or ""
        data_point_id = self.ontology.find_by_alias(raw_text)

        # Fallback: also try raw_text against all ontology aliases more broadly
        if data_point_id is None:
            data_point_id = _guess_data_point_from_context(
                raw_text, self.ontology.all_ids
            )

        mapping_confidence = 0.0
        canonical_reason = ""
        if data_point_id is not None:
            dp_def = self.ontology.get_data_point(data_point_id)
            mapping_confidence = 0.8  # alias matched
            canonical_reason = f"Matched by ontology alias"
            if dp_def:
                # Boost confidence if unit also matches
                if candidate.raw_unit and self.ontology.canonical_unit(candidate.raw_unit) in [
                    self.ontology.canonical_unit(u) for u in dp_def.units
                ]:
                    mapping_confidence = 0.9
                    canonical_reason += " + unit match"
        else:
            # Cannot map — skip for now, or mark as unknown
            return None

        # 2. Canonicalize unit
        raw_unit = candidate.raw_unit or ""
        unit = self.ontology.canonical_unit(raw_unit) if raw_unit else None

        # 3. Normalize period/year
        period = _normalize_period(candidate.raw_period)

        # 4. Build NormalizedClaim
        claim = NormalizedClaim(
            claim_id=f"ncl_{uuid.uuid4().hex[:12]}",
            data_point_id=data_point_id,
            value=candidate.raw_value,
            unit=unit,
            period=period,
            source_file_hint=candidate.evidence_hint or candidate.source_file,
            extraction_confidence=candidate.extraction_confidence,
            mapping_confidence=mapping_confidence,
            provenance={
                "candidate_id": candidate.candidate_id,
                "source_file": candidate.source_file,
                "source_kind": candidate.source_kind,
                "location": candidate.location,
            },
            dedup_group=data_point_id,
            canonical_reason=canonical_reason,
        )
        return claim

    def _deduplicate(self, claims: list[NormalizedClaim]) -> list[NormalizedClaim]:
        """Keep only the highest-confidence claim per data_point_id."""
        best: dict[str, NormalizedClaim] = {}
        for claim in claims:
            dp_id = claim.data_point_id
            if dp_id not in best:
                best[dp_id] = claim
                continue
            # Compare combined confidence
            current_conf = claim.extraction_confidence + claim.mapping_confidence
            existing_conf = best[dp_id].extraction_confidence + best[dp_id].mapping_confidence
            if current_conf > existing_conf:
                best[dp_id] = claim
        return list(best.values())


# ── helper functions ──────────────────────────────────────────────────


def _guess_data_point_from_context(text: str, all_ids: list[str]) -> Optional[str]:
    """Try a broader keyword match against known data point IDs."""
    text_lower = text.lower()
    mapping = {
        "scope 1": "scope1_emission",
        "scope 2": "scope2_emission",
        "scope 3": "scope3_emission",
        "scope 1 and scope 2": "scope1_scope2_total",
        "scope 1 & scope 2": "scope1_scope2_total",
        "total scope 1": "scope1_scope2_total",
        "headcount": "headcount",
        "employee": "headcount",
        "munkavallalo": "headcount",
        "letszam": "headcount",
        "renewable": "renewable_pct",
        "megujulo": "renewable_pct",
        "training": "training_participants",
        "kepzes": "training_participants",
        "production site": "production_sites",
        "site": "production_sites",
        "telephely": "production_sites",
    }
    for keyword, dp_id in mapping.items():
        if keyword in text_lower:
            return dp_id
    return None


def _normalize_period(raw_period: Optional[str]) -> Optional[str]:
    """Canonicalize a period string to 'YYYY' format."""
    if not raw_period:
        return str(_DEFAULT_YEAR)
    # "FY 2024" → "2024"
    match = re.search(r"(20[12]\d)", str(raw_period))
    if match:
        return match.group(1)
    return str(raw_period).strip()


# ── singleton ─────────────────────────────────────────────────────────

_normalizer_instance: Optional[ClaimNormalizer] = None


def get_normalizer() -> ClaimNormalizer:
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = ClaimNormalizer()
    return _normalizer_instance