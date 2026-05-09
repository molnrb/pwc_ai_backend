"""
Tabular evidence search — find evidence candidates in Excel and CSV source files.

Implements ranked retrieval using:
- header alias match
- row label alias match
- year column preference
- total row preference (for aggregate KPIs)
- source value normalization
- top-k candidate return with scores
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from models.audit_types import (
    NormalizedClaim,
    EvidenceCandidate,
    SheetTable,
    CsvTable,
)
from ontology.loader import get_ontology

logger = logging.getLogger("atlas.retrieval.tabular")

_ontology = get_ontology()


def find_tabular_evidence(
    claim: NormalizedClaim,
    tables: list[SheetTable | CsvTable],
) -> list[EvidenceCandidate]:
    """Search Excel/CSV tables for evidence matching a normalized claim.

    Args:
        claim: The normalized claim to find evidence for.
        tables: List of SheetTable or CsvTable from ingestion.

    Returns:
        Ranked list of EvidenceCandidate objects (score descending).
    """
    candidates: list[EvidenceCandidate] = []

    for table in tables:
        if isinstance(table, SheetTable):
            candidates.extend(_search_sheet(claim, table))
        elif isinstance(table, CsvTable):
            candidates.extend(_search_csv(claim, table))

    # Sort by retrieval confidence descending
    candidates.sort(key=lambda c: c.retrieval_confidence, reverse=True)
    return candidates


def _search_sheet(claim: NormalizedClaim, table: SheetTable) -> list[EvidenceCandidate]:
    """Search a single Excel sheet for evidence."""
    dp_def = _ontology.get_data_point(claim.data_point_id)
    candidates: list[EvidenceCandidate] = []

    # Build scoring columns list: prefer year columns, then percentage columns
    year_cols = [c for c in table.columns if re.search(r"(?:19|20)\d{2}", str(c))]
    pct_cols = [c for c in table.columns if re.search(r"(arány|%|percent|share)", str(c), re.IGNORECASE)]
    preferred_cols = year_cols + pct_cols + table.columns

    for row_idx, row in enumerate(table.rows):
        # Score row label match
        row_label_match = False
        first_val = list(row.values())[0] if row else None
        if first_val and claim.data_point_id:
            row_label_match = _fuzzy_match(str(first_val), claim.data_point_id)

        for col_name in preferred_cols:
            value = row.get(col_name)
            if value is None or not isinstance(value, (int, float)):
                continue

            # Compute score
            score = 0.0
            match_features: dict[str, Any] = {}

            # Column label match against ontology aliases
            if claim.data_point_id and dp_def:
                for alias in dp_def.aliases:
                    if alias.lower() in str(col_name).lower():
                        score += 0.3
                        match_features["alias_col_match"] = alias
                        break

            # Row label match
            if row_label_match:
                score += 0.2
                match_features["row_label_match"] = True

            # Year/period match
            if claim.period:
                for yc in year_cols:
                    if str(claim.period) in str(yc) or str(yc) in (str(claim.period)):
                        score += 0.2
                        match_features["year_col"] = yc
                        break

            # Unit match
            if claim.unit and dp_def:
                canonical_claim_unit = _ontology.canonical_unit(claim.unit)
                for u in dp_def.units:
                    if _ontology.canonical_unit(u) == canonical_claim_unit:
                        score += 0.15
                        match_features["unit_match"] = True
                        break

            # Total/aggregate row preference
            if str(first_val).lower() in ("total", "összesen", "összes", "sum", "total emissions"):
                score += 0.1
                match_features["total_row"] = True

            # Clamp score
            retrieval_confidence = min(score + 0.05, 1.0)

            candidate = EvidenceCandidate(
                evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
                data_point_guess=claim.data_point_id,
                file_name=table.source_file,
                source_kind="excel",
                location={
                    "sheet": table.sheet_name,
                    "row": row_idx + table.header_row_idx + 2,
                    "column": col_name,
                },
                raw_value=value,
                normalized_value=value,
                unit=claim.unit,
                period=claim.period,
                retrieval_confidence=retrieval_confidence,
                match_features=match_features,
            )
            candidates.append(candidate)

    return candidates


def _search_csv(claim: NormalizedClaim, table: CsvTable) -> list[EvidenceCandidate]:
    """Search a CSV for evidence."""
    candidates: list[EvidenceCandidate] = []

    for row_idx, row in enumerate(table.rows):
        for col_name, value in row.items():
            if value is None or not isinstance(value, (int, float)):
                continue

            score = 0.3  # Base score for numeric value

            # Column match against claim
            if claim.period and str(claim.period) in str(col_name):
                score += 0.2
            if _fuzzy_match(str(col_name), claim.data_point_id):
                score += 0.2

            retrieval_confidence = min(score + 0.05, 1.0)

            candidate = EvidenceCandidate(
                evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
                data_point_guess=claim.data_point_id,
                file_name=table.source_file,
                source_kind="csv",
                location={
                    "row": row_idx + 1,
                    "column": col_name,
                },
                raw_value=value,
                normalized_value=value,
                unit=claim.unit,
                period=claim.period,
                retrieval_confidence=retrieval_confidence,
                match_features={"column": col_name},
            )
            candidates.append(candidate)

    return candidates


def _fuzzy_match(text: str, target: str) -> bool:
    """Check if target appears as a substring or acronym in text."""
    text_lower = text.lower()
    target_lower = target.lower().replace("_", " ")
    if target_lower in text_lower:
        return True
    # Try individual words
    for word in target_lower.split():
        if len(word) > 2 and word in text_lower:
            return True
    return False