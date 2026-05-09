"""
Generic candidate extraction engine.

Supports two extraction strategies:
1. Deterministic pass — regex-based numeric span search
2. LLM-assisted pass — invoke DeepSeek for context-rich extraction (optional)

The extractor never produces final findings — it always emits ExtractedCandidate
objects that later layers normalize, match, and validate.
"""

from __future__ import annotations

import logging
import re
import time
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from models.audit_types import ExtractedCandidate, CandidateMention, TextBlock, TableBlock

logger = logging.getLogger("atlas.extraction")

# ── Numeric patterns for deterministic extraction ──────────────────────

_NUMERIC_KPI = re.compile(
    r"(\d[\d\s,]*\.?\d*)\s*(?:%|percent|pct|sz[aá]zal[eé]k)?\s*"
    r"(?:tonnes?\s*(?:CO2|CO2eq|CO2\s*equivalent))|"
    r"(?:MWh|megawatt|employees?|fő|sites?|db|participants?)",
    re.IGNORECASE,
)

_NUMBER_PATTERN = re.compile(r"(\d[\d\s,]*\.?\d+)\s*(%|percent|pct)?", re.IGNORECASE)
_UNIT_PATTERN = re.compile(
    r"(tonnes?\s*(?:CO2|CO2eq|CO2\s*equivalent))|"
    r"(MWh|megawatt[- ]?hours?)|"
    r"(employees?|people|staff|FTE|fő|főre?|alkalmazott)|"
    r"(sites?|locations?|facilities?|db|telephely)|"
    r"(participants?|r[eé]sztvev)",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(r"\b(20[12]\d|FY\s*20[12]\d)\b", re.IGNORECASE)
_SOURCE_REF_PATTERN = re.compile(r"\(Source:\s*([^)]+)\)", re.IGNORECASE)


def extract_candidates_deterministic(
    blocks: list[TextBlock | TableBlock],
    source_file: str,
) -> list[ExtractedCandidate]:
    """Deterministic candidate extraction from text blocks.

    Walks every TextBlock and applies a series of regex patterns to find
    numeric KPI-like mentions. Confidence is computed from the number of
    supporting features present (number, unit, year, source ref, heading context).

    Args:
        blocks: Mixed list of TextBlock and TableBlock from ingestion.
        source_file: The filename these blocks came from.

    Returns:
        List of ExtractedCandidate objects ready for normalization.
    """
    candidates: list[ExtractedCandidate] = []

    for block in blocks:
        if isinstance(block, TableBlock):
            # Extract numeric cells from tables
            candidates.extend(_extract_from_table(block, source_file))
            continue

        if not isinstance(block, TextBlock):
            continue

        text = block.text
        page = block.page

        # Find all number mentions in this block
        for num_match in _NUMBER_PATTERN.finditer(text):
            raw_num = num_match.group(1)
            pct_suffix = num_match.group(2)

            # Build context window around the number (±150 chars)
            start = max(0, num_match.start() - 150)
            end = min(len(text), num_match.end() + 150)
            context = text[start:end]

            # Parse numeric value
            try:
                cleaned = raw_num.replace(" ", "").replace(",", "")
                if pct_suffix:
                    value: Optional[float | int] = float(cleaned) if "." in cleaned else int(cleaned)
                else:
                    value = float(cleaned) if "." in cleaned else int(cleaned)
            except ValueError:
                value = None

            # Detect unit
            unit_match = _UNIT_PATTERN.search(context)
            raw_unit = unit_match.group(0) if unit_match else None

            # Detect year/period
            year_match = _YEAR_PATTERN.search(context)
            raw_period = year_match.group(0) if year_match else None

            # Detect source reference
            source_match = _SOURCE_REF_PATTERN.search(context)
            evidence_hint = source_match.group(1).strip() if source_match else None

            # Compute confidence
            confidence = _compute_candidate_confidence(
                has_number=value is not None,
                has_unit=raw_unit is not None,
                has_period=raw_period is not None,
                has_source_ref=evidence_hint is not None,
                is_heading=bool(block.heading_level),
            )

            # Build mention
            mention = CandidateMention(
                text=text[num_match.start():num_match.end()],
                start_char=num_match.start(),
                end_char=num_match.end(),
                kind="percentage" if pct_suffix else "numeric",
            )

            candidate = ExtractedCandidate(
                candidate_id=f"cand_{uuid.uuid4().hex[:12]}",
                source_file=source_file,
                source_kind="pdf_text",
                raw_text=context.strip(),
                raw_value=value,
                raw_unit=raw_unit,
                raw_period=raw_period,
                location={
                    "page": page,
                    "block_id": block.block_id,
                    "char_start": num_match.start(),
                    "char_end": num_match.end(),
                },
                extraction_confidence=confidence,
                evidence_hint=evidence_hint,
                mentions=[mention],
            )
            candidates.append(candidate)

    logger.info(
        "Deterministic extraction: %d candidates from %s (%d blocks)",
        len(candidates), source_file, len(blocks),
    )
    return _deduplicate_candidates(candidates)


def extract_candidates_llm(
    blocks: list[TextBlock | TableBlock],
    source_file: str,
) -> list[ExtractedCandidate]:
    """LLM-assisted candidate extraction — placeholder.

    When the DeepSeek parser is available, this function will send blocks
    to the LLM for richer KPI candidate extraction. For now, falls back to
    deterministic extraction.
    """
    logger.info("LLM extraction not yet implemented — using deterministic fallback")
    return extract_candidates_deterministic(blocks, source_file)


# ── internal helpers ───────────────────────────────────────────────────


def _extract_from_table(table: TableBlock, source_file: str) -> list[ExtractedCandidate]:
    """Extract numeric candidates from table cells."""
    candidates: list[ExtractedCandidate] = []
    for row in table.rows:
        for cell in row:
            if cell.raw_value is None:
                continue
            if not isinstance(cell.raw_value, (int, float)):
                # Try parsing string
                try:
                    cleaned = str(cell.raw_value).replace(",", "").replace(" ", "").replace("%", "")
                    cell.raw_value = float(cleaned)
                except (ValueError, TypeError):
                    continue

            candidate = ExtractedCandidate(
                candidate_id=f"cand_{uuid.uuid4().hex[:12]}",
                source_file=source_file,
                source_kind="pdf_table",
                raw_text=str(cell.raw_value),
                raw_value=cell.raw_value,
                raw_unit=cell.unit,
                raw_period=str(cell.year) if cell.year else None,
                location={
                    "page": table.page,
                    "block_id": table.block_id,
                    "row": cell.row_idx,
                    "col": cell.col_idx,
                    "cell_ref": cell.cell_ref,
                },
                extraction_confidence=0.6 if cell.raw_value is not None else 0.0,
            )
            candidates.append(candidate)
    return candidates


def _compute_candidate_confidence(
    has_number: bool = False,
    has_unit: bool = False,
    has_period: bool = False,
    has_source_ref: bool = False,
    is_heading: bool = False,
) -> float:
    """Score 0.0–1.0 based on supporting features."""
    if not has_number:
        return 0.0
    score = 0.3  # base for having a number
    if has_unit:
        score += 0.2
    if has_period:
        score += 0.15
    if has_source_ref:
        score += 0.2
    if is_heading:
        score += 0.1
    return min(score + 0.05, 1.0)  # slight bonus, capped at 1.0


def _deduplicate_candidates(candidates: list[ExtractedCandidate]) -> list[ExtractedCandidate]:
    """Remove candidates that are near-duplicates (same value, same page, same unit)."""
    seen: set[tuple] = set()
    deduped: list[ExtractedCandidate] = []
    for c in candidates:
        key = (c.raw_value, c.raw_unit, c.raw_period, c.location.get("page"))
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def save_candidates(candidates: list[ExtractedCandidate], workspace_dir: Path) -> None:
    """Persist candidates as JSON for inspection."""
    out_dir = workspace_dir / "candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = [c.model_dump() for c in candidates]
    out_path = out_dir / "all_candidates.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    logger.info("Candidates saved: %d → %s", len(candidates), out_path)