"""
Excel ingestion — load Excel workbooks into SheetTable objects.

Handles merged-cell normalization, header-row detection, multi-row header
collapse, and year-like column inference.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from models.audit_types import SheetTable

logger = logging.getLogger("atlas.ingestion.excel")

_YEAR_PATTERN = re.compile(r"^(?:19|20)\d{2}$")  # 1900-2099
_PERCENTAGE_COL = re.compile(r"(arány|%|percent|share|rate)$", re.IGNORECASE)


def ingest_excel(path: Path) -> list[SheetTable]:
    """Load all sheets from an Excel workbook.

    Args:
        path: Path to .xlsx or .xls file.

    Returns:
        List of SheetTable, one per sheet.
    """
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    xl = pd.ExcelFile(str(path))
    tables: list[SheetTable] = []

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(str(path), sheet_name=sheet_name, header=None)
        if df.empty:
            logger.debug("Skipping empty sheet: %s/%s", path.name, sheet_name)
            continue

        df = _normalize_merged_cells(df)
        header_idx = _detect_header_row(df)
        columns = _extract_columns(df, header_idx)

        # Build rows as list-of-dicts
        data_start = header_idx + 1
        rows: list[dict[str, Any]] = []
        for row_idx in range(data_start, len(df)):
            row_data: dict[str, Any] = {}
            for col_idx, col_name in enumerate(columns):
                if col_idx < df.shape[1]:
                    raw = df.iloc[row_idx, col_idx]
                    row_data[col_name] = _coerce_cell_value(raw)
            rows.append(row_data)

        table = SheetTable(
            sheet_name=sheet_name,
            source_file=path.name,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            header_row_idx=header_idx,
            merged_cells_normalized=True,
        )
        tables.append(table)

    logger.info(
        "Excel ingested: %s — %d sheets, %d total rows",
        path.name,
        len(tables),
        sum(t.row_count for t in tables),
    )
    return tables


def ingest_excel_as_dataframes(path: Path) -> dict[str, pd.DataFrame]:
    """Backward-compatible: return DataFrames by sheet name.

    Useful during migration — prefer ingest_excel() for new code.
    """
    xl = pd.ExcelFile(str(path))
    dfs: dict[str, pd.DataFrame] = {}
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(str(path), sheet_name=sheet_name, header=None)
        if not df.empty:
            dfs[sheet_name] = _normalize_merged_cells(df)
    return dfs


# ── internal helpers ───────────────────────────────────────────────────


def _normalize_merged_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill to simulate merged-cell unrolling in pandas."""
    return df.ffill(axis=0).ffill(axis=1)


def _detect_header_row(df: pd.DataFrame) -> int:
    """Return the 0-indexed row that looks like a header row.

    Strategy: find the first row where at least half the non-NaN cells
    are strings (column names) and fewer than half are numeric.
    """
    best_idx = 0
    best_score = 0.0

    for row_idx in range(min(10, len(df))):
        row = df.iloc[row_idx]
        non_null = row.dropna()
        if len(non_null) == 0:
            continue
        str_count = sum(1 for v in non_null if isinstance(v, str))
        num_count = len(non_null) - str_count
        score = str_count / max(len(non_null), 1)
        # Penalize rows with too many numbers (likely data, not headers)
        if num_count > str_count:
            score *= 0.5
        if score > best_score:
            best_score = score
            best_idx = row_idx

    return best_idx


def _extract_columns(df: pd.DataFrame, header_idx: int) -> list[str]:
    """Extract column names from the header row, with fallback names."""
    columns: list[str] = []
    if header_idx < len(df):
        for col in range(df.shape[1]):
            raw = df.iloc[header_idx, col]
            name = str(raw).strip() if pd.notna(raw) else f"Col_{col}"
            columns.append(name)
    else:
        columns = [f"Col_{i}" for i in range(df.shape[1])]
    return columns


def _coerce_cell_value(raw: Any) -> Optional[float | str | int]:
    """Normalize a cell value for evidence matching."""
    if pd.isna(raw):
        return None

    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if raw != int(raw) else int(raw)

    text = str(raw).strip()
    # Try numeric after cleaning
    cleaned = text.replace(",", "").replace(" ", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    try:
        value = float(cleaned)
        return int(value) if value.is_integer() else value
    except ValueError:
        return text


# ── Additional profiling helpers ────────────────────────────────────────


def profile_sheet(path: Path, sheet_name: str) -> dict[str, Any]:
    """Return metadata about a specific sheet for tooling use."""
    tables = ingest_excel(path)
    for table in tables:
        if table.sheet_name == sheet_name:
            return {
                "sheet_name": table.sheet_name,
                "columns": table.columns,
                "row_count": table.row_count,
                "sample_rows": table.rows[:5],
                "year_columns": [c for c in table.columns if _YEAR_PATTERN.match(str(c))],
                "percentage_columns": [c for c in table.columns if _PERCENTAGE_COL.search(str(c))],
            }
    return {"error": f"Sheet '{sheet_name}' not found"}


def find_numeric_candidates(
    path: Path, sheet_name: str, data_point_hint: str = "", period_hint: str = ""
) -> list[dict[str, Any]]:
    """Scan a sheet for numeric candidate values matching a data point hint."""
    tables = ingest_excel(path)
    results: list[dict[str, Any]] = []
    for table in tables:
        if table.sheet_name != sheet_name:
            continue
        for row_idx, row_data in enumerate(table.rows):
            for col_name, value in row_data.items():
                if value is None or not isinstance(value, (int, float)):
                    continue
                if period_hint and str(period_hint) in str(col_name):
                    results.append({
                        "sheet": sheet_name,
                        "row": row_idx + table.header_row_idx + 2,
                        "column": col_name,
                        "value": value,
                    })
                elif not period_hint:
                    results.append({
                        "sheet": sheet_name,
                        "row": row_idx + table.header_row_idx + 2,
                        "column": col_name,
                        "value": value,
                    })
    return results