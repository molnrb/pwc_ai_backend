"""
PDF-specific candidate extraction wrapper.

Combines the ingestion PDF blocks with the generic candidate extractor.
Provides step-by-step extraction with context building and confidence scoring.
"""

from __future__ import annotations

import logging
from pathlib import Path

from models.audit_types import ExtractedCandidate, TextBlock, TableBlock
from ingestion.pdf_ingestor import ingest_pdf
from extraction.candidate_extractor import extract_candidates_deterministic, extract_candidates_llm

logger = logging.getLogger("atlas.extraction.pdf")


def extract_pdf_candidates(
    pdf_path: Path,
    use_llm: bool = False,
) -> list[ExtractedCandidate]:
    """Full PDF candidate extraction pipeline.

    1. Ingest PDF → list[TextBlock | TableBlock]
    2. Extract candidates (deterministic or LLM-assisted)
    3. Return deduplicated ExtractedCandidate list
    """
    blocks = ingest_pdf(pdf_path)
    if use_llm:
        return extract_candidates_llm(blocks, pdf_path.name)
    return extract_candidates_deterministic(blocks, pdf_path.name)


def extract_candidates_from_string(
    text: str,
    source_file: str = "inline",
    page: int = 1,
) -> list[ExtractedCandidate]:
    """Quick extraction from a plain string — useful for testing."""
    block = TextBlock(
        page=page,
        block_id="inline_0",
        text=text,
    )
    return extract_candidates_deterministic([block], source_file)