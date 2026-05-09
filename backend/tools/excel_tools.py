import json
import os
import pandas as pd
from langchain_core.tools import tool

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "workspace")


def _coerce_excel_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    normalized = str(value).strip().replace(",", "")
    if normalized.endswith("%"):
        normalized = normalized[:-1].strip()

    try:
        return float(normalized)
    except ValueError:
        return str(value)


def _input_path(filename: str) -> str:
    return os.path.join(WORKSPACE_DIR, "input", filename)


def _evidence_path(filename: str) -> str:
    return os.path.join(WORKSPACE_DIR, "evidence", filename)


@tool
def read_excel_cell(filename: str, sheet: str, row_label: str, col_label: str) -> str:
    """Reads an Excel cell value by row and column label. Returns value, cell reference, and sheet.
    
    Args:
        filename: Excel filename (e.g. 'energia_2024.xlsx')
        sheet: Sheet name (e.g. 'Scope1_Scope2')
        row_label: Text to match in the first column (e.g. 'Total')
        col_label: Column header to read (e.g. 'Scope2_tonna')
        
    Returns:
        JSON with value, cell reference, and sheet name
    """
    filepath = _input_path(filename)
    df = pd.read_excel(filepath, sheet_name=sheet)
    
    # Find the row containing the label
    row_mask = df.iloc[:, 0].astype(str).str.contains(row_label, na=False)
    if not row_mask.any():
        return json.dumps({"error": f"Row with label '{row_label}' not found in sheet '{sheet}'"})
    
    row = df[row_mask]
    if col_label not in df.columns:
        return json.dumps({"error": f"Column '{col_label}' not found. Available: {list(df.columns)}"})
    
    value = row[col_label].values[0]
    # Excel cell reference (1-indexed row + column letter)
    row_num = row.index[0] + 2  # +2 for 0-index + header
    col_idx = list(df.columns).index(col_label)
    col_letter = chr(65 + col_idx) if col_idx < 26 else f"{chr(64 + col_idx // 26)}{chr(65 + col_idx % 26)}"
    cell_ref = f"{col_letter}{row_num}"
    
    return json.dumps({
        "value": _coerce_excel_value(value),
        "cell": cell_ref,
        "sheet": sheet,
        "filename": filename
    })


@tool
def read_excel_summary(filename: str) -> str:
    """Returns sheet names and column headers for an Excel file.
    
    Args:
        filename: Excel filename (e.g. 'energia_2024.xlsx')
        
    Returns:
        JSON with sheet names and their columns/row counts
    """
    filepath = _input_path(filename)
    xl = pd.ExcelFile(filepath)
    
    sheets = {}
    for sheet in xl.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet)
        sheets[sheet] = {
            "columns": list(df.columns),
            "row_count": len(df),
            "first_rows": df.head(3).to_dict(orient="records")
        }
    
    return json.dumps(sheets, indent=2, default=str)


@tool
def count_csv_rows(filename: str, filter_col: str, filter_val: str) -> str:
    """Counts CSV rows matching a filter condition.
    
    Args:
        filename: CSV filename (e.g. 'hr_export_2024.csv')
        filter_col: Column to filter on (e.g. 'statusz')
        filter_val: Value to match (e.g. 'aktiv')
        
    Returns:
        JSON with count and filter info
    """
    filepath = _input_path(filename)
    df = pd.read_csv(filepath)
    
    if filter_col not in df.columns:
        return json.dumps({"error": f"Column '{filter_col}' not found. Available: {list(df.columns)}"})
    
    count = len(df[df[filter_col] == filter_val])
    total = len(df)
    
    return json.dumps({
        "count": count,
        "total_rows": total,
        "filter": f"{filter_col} == '{filter_val}'",
        "filename": filename
    })


@tool
def write_evidence(batch_name: str, evidence: str) -> str:
    """Saves traced and validated evidence to the shared filesystem.
    
    Args:
        batch_name: identifier (e.g. 'batch_1')
        evidence: JSON string of evidence objects
    """
    os.makedirs(os.path.join(WORKSPACE_DIR, "evidence"), exist_ok=True)
    
    path = _evidence_path(f"{batch_name}.json")
    with open(path, "w") as f:
        f.write(evidence)
    return f"Evidence saved to {path}"
