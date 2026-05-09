"""
CSV ingestion — detect encoding, delimiter, header row, and column types.

Produces a CsvTable with structured rows ready for evidence retrieval.
"""

from __future__ import annotations

import csv as csv_module
import logging
import re
from pathlib import Path
from typing import Any, Optional

import chardet

from models.audit_types import CsvTable

logger = logging.getLogger("atlas.ingestion.csv")

# Common delimiters in priority order
_DELIMITERS = [",", ";", "\t", "|"]


def ingest_csv(path: Path) -> CsvTable:
    """Load a CSV file with automatic encoding and delimiter detection.

    Args:
        path: Path to the CSV file.

    Returns:
        CsvTable with full row data and metadata.
    """
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    raw_bytes = path.read_bytes()
    encoding = _detect_encoding(raw_bytes)
    delimiter = _detect_delimiter(raw_bytes, encoding)

    text = raw_bytes.decode(encoding)
    lines = text.splitlines()

    if not lines:
        return CsvTable(source_file=path.name, delimiter=delimiter, encoding=encoding)

    # Detect if first row is a header
    has_header = _detect_header(lines, delimiter)
    reader = csv_module.reader(text.splitlines(), delimiter=delimiter)

    rows_raw = list(reader)
    if not rows_raw:
        return CsvTable(source_file=path.name, delimiter=delimiter, encoding=encoding)

    if has_header:
        columns = [c.strip() for c in rows_raw[0]]
        data_start = 1
    else:
        columns = [f"Col_{i}" for i in range(len(rows_raw[0]))]
        data_start = 0

    # Build structured rows
    rows: list[dict[str, Any]] = []
    for row_cells in rows_raw[data_start:]:
        row_data: dict[str, Any] = {}
        for col_idx, cell in enumerate(row_cells):
            if col_idx < len(columns):
                row_data[columns[col_idx]] = _coerce_value(cell)
        if row_data:
            rows.append(row_data)

    table = CsvTable(
        source_file=path.name,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        delimiter=delimiter,
        encoding=encoding,
        has_header=has_header,
    )

    logger.info("CSV ingested: %s — %d rows, %d columns, encoding=%s", path.name, len(rows), len(columns), encoding)
    return table


def ingest_csv_as_dataframe(path: Path):
    """Backward-compatible: return a pandas DataFrame."""
    table = ingest_csv(path)
    import pandas as pd
    return pd.DataFrame(table.rows, columns=table.columns)


# ── internal helpers ───────────────────────────────────────────────────


def _detect_encoding(raw_bytes: bytes) -> str:
    """Detect file encoding using chardet, with UTF-8 as fallback."""
    result = chardet.detect(raw_bytes)
    encoding = result.get("encoding", "utf-8") or "utf-8"
    confidence = result.get("confidence", 0)
    if confidence < 0.5:
        encoding = "utf-8"
    logger.debug("Encoding detected: %s (confidence: %.2f)", encoding, confidence)
    return encoding


def _detect_delimiter(raw_bytes: bytes, encoding: str) -> str:
    """Guess the delimiter by checking which one produces the most consistent column counts."""
    text = raw_bytes.decode(encoding)
    # Take first 50 lines for sampling
    sample_lines = text.splitlines()[:50]
    if not sample_lines:
        return ","

    best_delim = ","
    best_score = -1

    for delim in _DELIMITERS:
        cols_per_line = [len(line.split(delim)) for line in sample_lines if line.strip()]
        if not cols_per_line:
            continue
        # Score by average column count (higher is better) and consistency
        avg_cols = sum(cols_per_line) / len(cols_per_line)
        # Only consider delimiters that produce >1 column
        if avg_cols <= 1:
            continue
        consistency = 1.0 / (1.0 + max(c - avg_cols for c in cols_per_line) - min(c - avg_cols for c in cols_per_line))
        score = avg_cols * consistency
        if score > best_score:
            best_score = score
            best_delim = delim

    logger.debug("Delimiter detected: '%s' (score: %.2f)", best_delim, best_score)
    return best_delim


def _detect_header(lines: list[str], delimiter: str) -> bool:
    """Heuristic: if the first row has mostly strings and subsequent rows have numbers, it's a header."""
    if len(lines) < 2:
        return False

    first_row = [c.strip() for c in lines[0].split(delimiter)]
    second_row = [c.strip() for c in lines[1].split(delimiter)] if len(lines) > 1 else []

    # Count numeric cells in each row
    first_numeric = sum(1 for c in first_row if _is_numeric(c))
    second_numeric = sum(1 for c in second_row if _is_numeric(c))

    # If second row has more numbers than first, first row is likely a header
    return second_numeric > first_numeric


def _is_numeric(text: str) -> bool:
    """Check if a string represents a number."""
    text = text.strip()
    if not text:
        return False
    cleaned = text.replace(",", "").replace("%", "").strip()
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _coerce_value(raw: str) -> Optional[str | int | float]:
    """Normalize a CSV cell value."""
    text = raw.strip()
    if not text:
        return None

    # Try numeric
    cleaned = text.replace(",", "").replace(" ", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        value = float(cleaned)
        return int(value) if value.is_integer() else value
    except ValueError:
        return text


# ── Additional profiling helpers ────────────────────────────────────────


def profile_csv(path: Path) -> dict[str, Any]:
    """Return metadata about a CSV file for tooling use."""
    table = ingest_csv(path)
    return {
        "source_file": table.source_file,
        "columns": table.columns,
        "row_count": table.row_count,
        "delimiter": table.delimiter,
        "encoding": table.encoding,
        "has_header": table.has_header,
        "sample_rows": table.rows[:5],
    }


def search_csv_columns(path: Path, query: str) -> list[dict[str, Any]]:
    """Search CSV columns by name matching."""
    table = ingest_csv(path)
    results: list[dict[str, Any]] = []
    query_lower = query.lower()
    for col in table.columns:
        if query_lower in col.lower():
            # Return distinct values from this column
            values = list({row.get(col) for row in table.rows if row.get(col) is not None})
            results.append({
                "column": col,
                "distinct_count": len(values),
                "sample_values": values[:10],
            })
    return results