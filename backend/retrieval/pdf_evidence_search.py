"""
PDF evidence search — find evidence candidates in source PDF documents.

Searches text blocks and table blocks for numeric evidence that matches
a normalized claim based on semantic labels, units, and periods.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from models.audit_types import (
    NormalizedClaim,
    EvidenceCandidate,
    TextBlock,
    TableBlock,
)
from ontology.loader import get_ontology

logger = logging.getLogger("atlas.retrieval.pdf")

_ontology = get_ontology()


def find_pdf_evidence(
    claim: NormalizedClaim,
    pdf_blocks: list[TextBlock | TableBlock],
) -> list[EvidenceCandidate]:
    """Search PDF blocks for evidence matching a normalized claim.

    Args:
        claim: The normalized claim to find evidence for.
        pdf_blocks: List of TextBlock and TableBlock from PDF ingestion.

    Returns:
        Ranked list of EvidenceCandidate objects.
    """
    candidates: list[EvidenceCandidate] = []

    for block in pdf_blocks:
        if isinstance(block, TextBlock):
            candidates.extend(_search_text_block(claim, block))
        elif isinstance(block, TableBlock):
            candidates.extend(_search_table_block(claim, block))

    candidates.sort(key=lambda c: c.retrieval_confidence, reverse=True)
    return candidates


def _search_text_block(claim: NormalizedClaim, block: TextBlock) -> list[EvidenceCandidate]:
    """Search a text block for numeric evidence hit."""
    candidates: list[EvidenceCandidate] = []
    text = block.text.lower()
    dp_def = _ontology.get_data_point(claim.data_point_id)

    # Only proceed if the text contains relevant keywords
    has_relevant = False
    if dp_def:
        for alias in dp_def.aliases:
            if alias.lower() in text:
                has_relevant = True
                break
    if not has_relevant:
        # Try generic keyword matching
        if claim.data_point_id and _fuzzy_text_match(text, claim.data_point_id):
            has_relevant = True
    if not has_relevant:
        return candidates

    # Find all numbers in this block
    number_matches = re.finditer(r"(\d[\d\s,]*\.?\d+)\s*(%|percent|pct)?", text, re.IGNORECASE)
    for num_match in number_matches:
        raw_num = num_match.group(1)
        suffix = num_match.group(2)

        try:
            cleaned = raw_num.replace(" ", "").replace(",", "")
            value = float(cleaned) if "." in cleaned else int(cleaned)
            if suffix and not _ontology.is_percentage_unit(claim.unit or ""):
                # Percentage found but claim unit is not percentage — still include
                pass
        except ValueError:
            continue

        score = 0.3  # Base for finding a number in context
        match_features: dict[str, Any] = {"block_id": block.block_id}

        # Unit presence boosts score
        unit_match = re.search(
            r"(tonnes?|CO2|MWh|employees?|fő|sites?|db|participants?)",
            text[max(0, num_match.start() - 100):num_match.end() + 100],
            re.IGNORECASE,
        )
        if unit_match:
            score += 0.2
            match_features["unit_in_context"] = unit_match.group(0)

        # Year/period presence
        year_match = re.search(r"(20[12]\d)", text[max(0, num_match.start() - 100):num_match.end() + 100])
        if year_match and year_match.group(1) == str(claim.period):
            score += 0.2
            match_features["year_match"] = year_match.group(1)

        retrieval_confidence = min(score + 0.05, 1.0)

        candidate = EvidenceCandidate(
            evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
            data_point_guess=claim.data_point_id,
            file_name="source_pdf",
            source_kind="pdf",
            location={
                "page": block.page,
                "block_id": block.block_id,
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


def _search_table_block(claim: NormalizedClaim, table: TableBlock) -> list[EvidenceCandidate]:
    """Search a table block for numeric evidence."""
    candidates: list[EvidenceCandidate] = []
    for row in table.rows:
        for cell in row:
            if cell.raw_value is None:
                continue
            if not isinstance(cell.raw_value, (int, float)):
                try:
                    cleaned = str(cell.raw_value).replace(",", "").replace(" ", "").replace("%", "")
                    cell.raw_value = float(cleaned)
                except (ValueError, TypeError):
                    continue

            candidate = EvidenceCandidate(
                evidence_id=f"ev_{uuid.uuid4().hex[:12]}",
                data_point_guess=claim.data_point_id,
                file_name="source_pdf",
                source_kind="pdf_table",
                location={
                    "page": table.page,
                    "block_id": table.block_id,
                    "row": cell.row_idx,
                    "col": cell.col_idx,
                },
                raw_value=cell.raw_value,
                normalized_value=cell.raw_value,
                unit=cell.unit or claim.unit,
                period=str(cell.year) if cell.year else claim.period,
                retrieval_confidence=0.4,  # Moderate confidence for table cells
                match_features={"cell_ref": cell.cell_ref},
            )
            candidates.append(candidate)

    return candidates


def _fuzzy_text_match(text: str, data_point_id: str) -> bool:
    """Check if data_point_id keywords appear in text."""
    id_lower = data_point_id.lower().replace("_", " ")
    if id_lower in text:
        return True
    for word in id_lower.split():
        if len(word) > 2 and word in text:
            return True
    return False