"""CSV tooling — LangChain tools for deepagents to use during audit tracing."""

import json
import os
import logging
from pathlib import Path

import pandas as pd
from langchain_core.tools import tool

from input_bundle import resolve_input_path

logger = logging.getLogger("atlas.tools.csv")

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent.parent / "workspace"))


def _input_path(filename: str) -> str:
    return str(resolve_input_path(filename, WORKSPACE_DIR))


@tool
def profile_csv(filename: str) -> str:
    """Returns metadata for a CSV file: columns, row count, delimiter, encoding.

    Args:
        filename: CSV filename (e.g. 'hr_export_2024.csv')

    Returns:
        JSON with columns, row_count, sample rows
    """
    try:
        from ingestion.csv_ingestor import profile_csv as do_profile
        result = do_profile(Path(_input_path(filename)))
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error("profile_csv failed for %s: %s", filename, e)
        return json.dumps({"error": str(e)})


@tool
def search_csv_columns(filename: str, query: str) -> str:
    """Search CSV column names for a query string and return distinct values.

    Args:
        filename: CSV filename
        query: Search term for column names (e.g. 'headcount', 'statusz')

    Returns:
        JSON with matching columns and sample values
    """
    try:
        from ingestion.csv_ingestor import search_csv_columns as do_search
        result = do_search(Path(_input_path(filename)), query)
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error("search_csv_columns failed for %s: %s", filename, e)
        return json.dumps({"error": str(e)})


@tool
def find_csv_numeric_candidates(filename: str, data_point_hint: str = "", period_hint: str = "") -> str:
    """Find numeric candidate values in a CSV file matching a data point hint.

    Args:
        filename: CSV filename
        data_point_hint: Optional data point name to look for
        period_hint: Optional year/period to filter by

    Returns:
        JSON array of numeric candidates with row/column info
    """
    try:
        from ingestion.csv_ingestor import ingest_csv
        table = ingest_csv(Path(_input_path(filename)))
        results = []
        for row_idx, row in enumerate(table.rows):
            for col_name, value in row.items():
                if value is None or not isinstance(value, (int, float)):
                    continue
                if period_hint and str(period_hint) not in str(col_name):
                    continue
                if data_point_hint and data_point_hint.lower() not in col_name.lower():
                    continue
                results.append({
                    "row": row_idx + 1,
                    "column": col_name,
                    "value": value,
                })
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        logger.error("find_csv_numeric_candidates failed for %s: %s", filename, e)
        return json.dumps({"error": str(e)})