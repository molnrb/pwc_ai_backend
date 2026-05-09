"""
PDF ingestion — extract text blocks and table-like regions from PDF files.

Produces lists of TextBlock and TableBlock that downstream layers consume.
Bounding-box provenance and page numbers are preserved on every block.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

import fitz  # pymupdf

from models.audit_types import TextBlock, TableBlock, TableCell

logger = logging.getLogger("atlas.ingestion.pdf")

# Heuristic: blocks whose text is short (<120 chars), ends without a period,
# and the first word stands alone in the block are likely headings.
_HEADING_CANDIDATE = re.compile(r"^[A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\s]{2,60}$")
_TABLE_ROW_PATTERN = re.compile(r"^\s*([\d.,%-]+\s+){2,}")  # at least 2 numeric tokens


def ingest_pdf(pdf_path: Path) -> list[TextBlock | TableBlock]:
    """Load a PDF and return its page blocks as TextBlock and TableBlock objects.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Mixed list of TextBlock and TableBlock, ordered by page then position.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    blocks: list[TextBlock | TableBlock] = []
    block_counter = 0

    try:
        for page_num in range(1, len(doc) + 1):
            page = doc[page_num - 1]
            page_blocks = page.get_text("blocks")
            for raw_block in page_blocks:
                block_counter += 1
                text = (raw_block[4] or "").strip()
                if not text:
                    continue

                bbox: Optional[tuple[float, float, float, float]] = None
                if len(raw_block) >= 4:
                    bbox = (float(raw_block[0]), float(raw_block[1]), float(raw_block[2]), float(raw_block[3]))

                # Detect heading
                heading_level = _detect_heading_level(text)

                # Detect table-like regions
                if _looks_like_table(text):
                    table_block = _block_to_table(block_counter, page_num, text, bbox)
                    blocks.append(table_block)
                else:
                    tb = TextBlock(
                        page=page_num,
                        block_id=f"pdf_b{block_counter}_p{page_num}",
                        text=text,
                        bbox=bbox,
                        heading_level=heading_level,
                    )
                    blocks.append(tb)

        logger.info("PDF ingested: %s — %d pages, %d blocks", pdf_path.name, len(doc), len(blocks))
    finally:
        doc.close()

    return blocks


def ingest_pdf_pages(pdf_path: Path) -> list[dict[str, Any]]:
    """Backward-compatible: return page/paragraph dicts like the old pipeline.

    Use this as a bridge while migrating — prefer ingest_pdf() for new code.
    """
    doc = fitz.open(str(pdf_path))
    result: list[dict[str, Any]] = []
    try:
        for page_num in range(1, len(doc) + 1):
            page = doc[page_num - 1]
            for block_idx, block in enumerate(page.get_text("blocks")):
                text = (block[4] or "").strip()
                if text:
                    result.append({"page": page_num, "paragraph_idx": block_idx, "text": text})
    finally:
        doc.close()
    return result


# ── internal helpers ───────────────────────────────────────────────────


def _detect_heading_level(text: str) -> Optional[int]:
    """Return 1, 2, or None based on heading-like heuristics."""
    first_line = text.split("\n")[0].strip()
    if _HEADING_CANDIDATE.match(first_line):
        if len(first_line) < 50:
            return 1
        return 2
    # All-caps short lines
    if len(first_line) < 80 and first_line.isupper():
        return 2
    return None


def _looks_like_table(text: str) -> bool:
    """Heuristic: two or more numeric tokens in the same line suggest a table row."""
    lines = text.split("\n")
    numeric_line_count = sum(1 for line in lines if _TABLE_ROW_PATTERN.search(line))
    return numeric_line_count >= 2


def _block_to_table(block_id: int, page: int, text: str, bbox) -> TableBlock:
    """Convert a text block that looks like a table into a TableBlock."""
    lines = text.split("\n")
    rows: list[list[TableCell]] = []
    for row_idx, line in enumerate(lines):
        parts = _tokenize_table_row(line)
        cells = []
        for col_idx, part in enumerate(parts):
            cell = TableCell(
                row_idx=row_idx,
                col_idx=col_idx,
                raw_value=part,
                cell_ref=f"pdf_b{block_id}_p{page}_r{row_idx}_c{col_idx}",
            )
            cells.append(cell)
        rows.append(cells)

    return TableBlock(
        block_id=f"pdf_tbl_{block_id}_p{page}",
        page=page,
        rows=rows,
        header_rows=1,
    )


def _tokenize_table_row(line: str) -> list[str]:
    """Split a table row into cell tokens on 2+ whitespace."""
    return [token.strip() for token in re.split(r"\s{2,}", line) if token.strip()]


# ── Optional OCR fallback hook (not implemented) ────────────────────────


def ingest_pdf_with_ocr(pdf_path: Path) -> list[TextBlock | TableBlock]:
    """Placeholder: falls back to regular text extraction.

    If OCR packages become available, this function can route to OCR-based
    extraction for scanned pages that yield no text blocks.
    """
    logger.warning("OCR fallback not yet available — using text extraction only")
    return ingest_pdf(pdf_path)