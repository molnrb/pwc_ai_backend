"""
Deterministic CSRD Audit Pipeline — no LLM required for the core audit logic.

This runs the full Parse → Trace → Validate → Report flow using direct
tool calls. It's the reliable fallback and the default execution path.
The deepagents orchestration is available as an advanced/experimental mode.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz  # pymupdf
import pandas as pd

WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace")))
INPUT_DIR = WORKSPACE / "input"
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"
REPORT_PATH = WORKSPACE / "audit_report.json"

# ── Claim extraction patterns ──────────────────────────────────────────

# Each pattern is tuned to match ONLY the primary claim statement, not
# supplementary mentions (e.g., site-level breakdowns, prior-year baselines).
# (pattern, data_point_id, unit, min_value_filter)
CLAIM_PATTERNS: list[tuple[re.Pattern, str, str, int]] = [
    # "The company's Scope 1 emissions for 2024 were 1,850 tonnes CO2 equivalent."
    (re.compile(r"company'?s?\s+Scope\s*1\s+emissions?\s+(?:for\s+)?2024\s+(?:were|was)\s+(\d[\d\s,]*\.?\d*)\s*(?:tonnes?|tonna)\s+CO", re.IGNORECASE),
     "scope1_emission", "tCO2e", 100),

    # "The company's Scope 2 emissions for 2024 were 4,200 tonnes CO2 equivalent."
    (re.compile(r"company'?s?\s+Scope\s*2\s+emissions?\s+(?:for\s+)?2024\s+(?:were|was)\s+(\d[\d\s,]*\.?\d*)\s*(?:tonnes?|tonna)\s+CO", re.IGNORECASE),
     "scope2_emission", "tCO2e", 100),

    # "The total Scope 1 and Scope 2 emissions amount to 6,050 tonnes CO2 equivalent."
    (re.compile(r"(?:total|combined)\s+Scope\s*1\s+(?:and|&)\s+Scope\s*2\s+emissions?\s+(?:amount\s*to|were|was|total|sum)\s+(\d[\d\s,]*\.?\d*)\s*(?:tonnes?|tonna)\s+CO", re.IGNORECASE),
     "scope1_scope2_total", "tCO2e", 100),

    # "The estimated Scope 3 emissions were 18,400 tonnes CO2 equivalent."
    (re.compile(r"estimated\s+Scope\s*3\s+emissions?\s+(?:were|was)\s+(\d[\d\s,]*\.?\d*)\s*(?:tonnes?|tonna)\s+CO", re.IGNORECASE),
     "scope3_emission", "tCO2e", 100),

    # "total headcount as of December 31, 2024 was 2,340 employees"
    (re.compile(r"(?:total\s+)?headcount\s+(?:as\s+of\s+)?(?:December\s+31,?\s+)?2024\s+(?:was|were)\s+(\d[\d\s,]*\.?\d*)\s+employees?", re.IGNORECASE),
     "headcount", "fő", 100),

    # "share of renewable energy in total energy consumption was 67%"
    (re.compile(r"(?:share|aránya)\s+of\s+renewable\s+energy\s+in\s+total\s+energy\s+consumption\s+was\s+(\d+[\.,]?\d*)\s*%", re.IGNORECASE),
     "renewable_pct", "%", 1),

    # "number of participants in training programs was 1,240 employees"
    (re.compile(r"(?:number|száma)\s+of\s+participants\s+in\s+training\s+programs?\s+(?:was|were)\s+(\d[\d\s,]*\.?\d*)\s+employees?", re.IGNORECASE),
     "training_participants", "fő", 10),

    # "company conducts production activities at 3 sites"
    (re.compile(r"company\s+conducts\s+production\s+activities\s+at\s+(\d+)\s+sites?", re.IGNORECASE),
     "production_sites", "db", 1),
]

# ── Source file mapping ────────────────────────────────────────────────

SOURCE_MAP = {
    "scope1_emission": {"file": "energia_2024.xlsx", "sheet": "Scope1_Scope2", "row": "Total", "col": "Scope1_tonna", "green_threshold": 0.005},
    "scope2_emission": {"file": "energia_2024.xlsx", "sheet": "Scope1_Scope2", "row": "Total", "col": "Scope2_tonna", "green_threshold": 0.005},
    "scope1_scope2_total": {"file": "energia_2024.xlsx", "sheet": "Scope1_Scope2", "row": "Total", "computed": "scope1+scope2", "green_threshold": 0.005},
    "renewable_pct": {"file": "energia_2024.xlsx", "sheet": "Megujulo", "row": "2024", "col": "Arany", "green_threshold": 0.01},
    "headcount": {"file": "hr_export_2024.csv", "type": "csv", "filter_col": "statusz", "filter_val": "aktiv", "green_threshold": 0.01},
    "scope3_emission": {"file": "scope3_szallito.xlsx", "sheet": "Scope3", "row": "Total", "col": "Kibocsatas (tonna)", "green_threshold": 0.05},
    "training_participants": None,  # No source file
    "production_sites": None,
}


# ── Public API ─────────────────────────────────────────────────────────


def run_full_audit(
    pdf_filename: str = "atlas_sustainability_statement.pdf",
    progress_callback=None,
) -> dict:
    """Run the complete deterministic audit pipeline.

    Args:
        pdf_filename: PDF in workspace/input/
        progress_callback: Optional callable(stage, detail) — sync or async

    Returns:
        Full audit report dict with metadata, findings, summary
    """
    _ensure_dirs()
    started_at = datetime.now(timezone.utc).isoformat()
    pdf_path = _resolve_pdf_path(pdf_filename)
    pdf_filename = pdf_path.name

    # ── Phase 1: Parse ──
    _emit(progress_callback, "parse_start", {"file": pdf_filename})
    claims = _parse_pdf(pdf_path)
    _emit(progress_callback, "parse_done", {"claims_found": len(claims)})

    # Save raw claims
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    claims_path = CLAIMS_DIR / "all_claims.json"
    claims_path.write_text(json.dumps(claims, indent=2, ensure_ascii=False))

    # ── Phase 2: Trace & Validate ──
    _emit(progress_callback, "trace_start", {"claims_to_trace": len(claims)})
    findings = []
    for i, claim in enumerate(claims):
        dp = claim["data_point"]
        _emit(progress_callback, "trace_item", {
            "data_point": dp,
            "claimed_value": claim["claimed_value"],
            "progress": f"{i+1}/{len(claims)}",
        })
        finding = _trace_and_validate(claim)
        findings.append(finding)

    _emit(progress_callback, "trace_done", {"findings": len(findings)})

    # Save evidence
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / "all_evidence.json"
    evidence_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False))

    # ── Phase 3: Report ──
    _emit(progress_callback, "report_generating", {})
    summary = _compute_summary(findings)

    report = {
        "audit_metadata": {
            "document": pdf_filename,
            "standard": "ESRS E1 — Climate Change",
            "framework": "EU CSRD",
            "pipeline": "deterministic",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "total_pages": _get_page_count(pdf_path),
            "total_claims_found": len(claims),
            "total_findings": len(findings),
        },
        "findings": findings,
        "summary": summary,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    _emit(progress_callback, "complete", summary)

    return report


def reset_workspace() -> dict:
    """Clear all audit outputs for a fresh run."""
    cleared = []
    for d in [CLAIMS_DIR, EVIDENCE_DIR]:
        if d.exists():
            for f in d.glob("*.json"):
                f.unlink()
                cleared.append(str(f))
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()
        cleared.append(str(REPORT_PATH))
    return {"cleared": len(cleared), "files": cleared}


# ── Internal: Parse ────────────────────────────────────────────────────


def _parse_pdf(pdf_path: Path) -> list[dict]:
    """Extract all numerical sustainability claims from a PDF.
    
    Uses precise regex patterns targeting the primary claim statements.
    Deduplicates: only the first (earliest page) match per data_point is kept.
    """
    doc = fitz.open(str(pdf_path))
    claims = []
    seen_data_points: set[str] = set()

    for page_num in range(1, len(doc) + 1):
        page = doc[page_num - 1]
        blocks = page.get_text("blocks")

        for block_idx, block in enumerate(blocks):
            text = block[4].strip()
            if not text:
                continue

            for pattern, dp_id, unit, min_val in CLAIM_PATTERNS:
                if dp_id in seen_data_points:
                    continue  # already captured the primary claim

                m = pattern.search(text)
                if not m:
                    continue

                raw_value = m.group(1).replace(" ", "").replace(",", "")
                try:
                    if "." in raw_value:
                        value = float(raw_value)
                    else:
                        value = int(raw_value)
                except ValueError:
                    continue

                # Filter out obviously wrong small values
                if value < min_val:
                    continue

                source_hint = "unknown"
                if dp_id in SOURCE_MAP and SOURCE_MAP[dp_id]:
                    source_hint = SOURCE_MAP[dp_id].get("file", "unknown")

                claims.append({
                    "data_point": dp_id,
                    "claimed_value": value,
                    "unit": unit,
                    "page": page_num,
                    "paragraph_idx": block_idx,
                    "source_hint": source_hint,
                    "claim_text": text.strip(),
                })
                seen_data_points.add(dp_id)
                break  # one claim per block

    doc.close()
    return claims


# ── Internal: Trace & Validate ─────────────────────────────────────────


def _trace_and_validate(claim: dict) -> dict:
    """Look up the source value and validate against the claim."""
    dp = claim["data_point"]
    source_info = SOURCE_MAP.get(dp)

    base = {
        "data_point": dp,
        "claim_text": claim["claim_text"],
        "claimed_value": claim["claimed_value"],
        "unit": claim["unit"],
        "page": claim["page"],
        "paragraph_idx": claim["paragraph_idx"],
    }

    if source_info is None:
        return {**base, "flag": "grey", "deviation_pct": None, "source_value": None,
                "source_file": None, "source_sheet": None, "source_cell": None,
                "explanation": f"No source document configured for {dp}"}

    source_file = source_info["file"]

    try:
        if "computed" in source_info:
            # Special: computed fields (scope1+scope2)
            return _validate_computed(claim, base, source_info)

        elif source_info.get("type") == "csv":
            # CSV data source
            return _validate_csv(claim, base, source_info)

        else:
            # Excel data source
            return _validate_excel(claim, base, source_info)

    except Exception as e:
        return {**base, "flag": "grey", "deviation_pct": None, "source_value": None,
                "source_file": source_file, "source_sheet": source_info.get("sheet"),
                "source_cell": None,
                "explanation": f"Error reading source: {e}"}


def _validate_excel(claim: dict, base: dict, source_info: dict) -> dict:
    """Validate against an Excel source."""
    filepath = INPUT_DIR / source_info["file"]
    sheet = source_info["sheet"]
    col = source_info["col"]

    df = pd.read_excel(str(filepath), sheet_name=sheet)

    # Handle percentage values like "67%"
    row_mask = df.iloc[:, 0].astype(str).str.contains(str(source_info["row"]), na=False)
    if not row_mask.any():
        # Try exact match in any column for the row label
        for c in df.columns:
            row_mask = df[c].astype(str).str.contains(str(source_info["row"]), na=False)
            if row_mask.any():
                break

    if not row_mask.any():
        return {**base, "flag": "grey", "deviation_pct": None, "source_value": None,
                "source_file": source_info["file"], "source_sheet": sheet,
                "source_cell": None,
                "explanation": f"Row '{source_info['row']}' not found in sheet '{sheet}'"}

    row = df[row_mask]
    idx = row.index[0]

    if col not in df.columns:
        return {**base, "flag": "grey", "deviation_pct": None, "source_value": None,
                "source_file": source_info["file"], "source_sheet": sheet,
                "source_cell": None,
                "explanation": f"Column '{col}' not found. Available: {list(df.columns)}"}

    raw_value = row[col].values[0]
    if pd.isna(raw_value):
        return {**base, "flag": "grey", "deviation_pct": None, "source_value": None,
                "source_file": source_info["file"], "source_sheet": sheet,
                "source_cell": f"{col}{idx+2}",
                "explanation": f"Empty cell at {col}{idx+2}"}

    # Parse percentage
    source_value = _parse_value(raw_value)
    col_idx = list(df.columns).index(col)
    col_letter = chr(65 + col_idx) if col_idx < 26 else f"{chr(64 + col_idx // 26)}{chr(65 + col_idx % 26)}"
    cell_ref = f"{col_letter}{idx + 2}"

    return _validate_and_format(claim, base, source_value, source_info["file"], sheet, cell_ref,
                                source_info.get("green_threshold", 0.01))


def _validate_csv(claim: dict, base: dict, source_info: dict) -> dict:
    """Validate against a CSV source."""
    filepath = INPUT_DIR / source_info["file"]
    df = pd.read_csv(str(filepath))

    filter_col = source_info["filter_col"]
    filter_val = source_info["filter_val"]

    if filter_col not in df.columns:
        return {**base, "flag": "grey", "deviation_pct": None, "source_value": None,
                "source_file": source_info["file"], "source_sheet": "Sheet1",
                "source_cell": None,
                "explanation": f"Column '{filter_col}' not found in CSV"}

    source_value = len(df[df[filter_col] == filter_val])

    return _validate_and_format(claim, base, source_value, source_info["file"], "Sheet1",
                                f"{filter_col}=='{filter_val}' ({source_value} rows)",
                                source_info.get("green_threshold", 0.01))


def _validate_computed(claim: dict, base: dict, source_info: dict) -> dict:
    """Validate a computed field (e.g., scope1+scope2 sum)."""
    filepath = INPUT_DIR / source_info["file"]
    sheet = source_info["sheet"]

    df = pd.read_excel(str(filepath), sheet_name=sheet)
    row_mask = df.iloc[:, 0].astype(str).str.contains("Total", na=False)
    row = df[row_mask]

    scope1 = float(row["Scope1_tonna"].values[0])
    scope2 = float(row["Scope2_tonna"].values[0])
    computed = scope1 + scope2

    return _validate_and_format(claim, base, computed, source_info["file"], sheet,
                                f"Scope1({scope1}) + Scope2({scope2})",
                                source_info.get("green_threshold", 0.01))


def _validate_and_format(claim: dict, base: dict, source_value, source_file: str,
                          source_sheet: str, source_cell: str,
                          green_threshold: float = 0.01) -> dict:
    """Run the deterministic validation math."""
    claimed = claim["claimed_value"]

    if source_value == 0:
        return {**base, "flag": "red", "deviation_pct": 100.0,
                "source_value": source_value, "source_file": source_file,
                "source_sheet": source_sheet, "source_cell": source_cell,
                "explanation": f"Source value is 0 — cannot compute deviation. Claimed: {claimed} {claim['unit']}"}

    deviation = abs(claimed - source_value) / abs(source_value)
    deviation_pct = round(deviation * 100, 2)

    if deviation < green_threshold:
        flag = "green"
    elif deviation <= 0.05:
        flag = "yellow"
    else:
        flag = "red"

    explanation = (f"Claimed: {claimed} {claim['unit']}, "
                   f"Source: {source_value} {claim['unit']}, "
                   f"Deviation: {deviation_pct}%")

    return {**base, "flag": flag, "deviation_pct": deviation_pct,
            "source_value": source_value, "source_file": source_file,
            "source_sheet": source_sheet, "source_cell": source_cell,
            "explanation": explanation}


# ── Helpers ────────────────────────────────────────────────────────────


def _parse_value(raw) -> float | int:
    """Parse a raw cell value, handling percentage strings."""
    if isinstance(raw, str) and raw.endswith("%"):
        return int(raw.replace("%", "").strip())
    return float(raw) if isinstance(raw, (int, float)) else int(raw)


def _resolve_pdf_path(pdf_filename: str) -> Path:
    candidate = INPUT_DIR / pdf_filename
    if candidate.exists():
        return candidate

    pdf_files = sorted(path for path in INPUT_DIR.glob('*.pdf') if path.is_file())
    if len(pdf_files) == 1:
        return pdf_files[0]
    if len(pdf_files) > 1:
        return pdf_files[0]
    raise FileNotFoundError(f'No PDF file found in {INPUT_DIR}')


def _get_page_count(pdf_path: Path) -> int:
    try:
        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def _compute_summary(findings: list[dict]) -> dict:
    green = sum(1 for f in findings if f.get("flag") == "green")
    yellow = sum(1 for f in findings if f.get("flag") == "yellow")
    red = sum(1 for f in findings if f.get("flag") == "red")
    grey = sum(1 for f in findings if f.get("flag") not in ("green", "yellow", "red"))

    red_flags = []
    for f in findings:
        if f.get("flag") == "red":
            red_flags.append({
                "data_point": f["data_point"],
                "claimed": f["claimed_value"],
                "actual": f.get("source_value"),
                "deviation_pct": f.get("deviation_pct"),
                "explanation": f.get("explanation", ""),
            })

    return {
        "green_count": green,
        "yellow_count": yellow,
        "red_count": red,
        "grey_count": grey,
        "total": len(findings),
        "red_flags": red_flags,
        "verdict": "PASS" if red == 0 else "FAIL — material misstatements detected",
        "materiality_note": (
            f"Material errors found: {red}. "
            f"Auditor must investigate red flags before signing off."
        ) if red > 0 else "No material misstatements. Report is consistent with source data.",
    }


def _ensure_dirs():
    for d in [CLAIMS_DIR, EVIDENCE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _emit(callback, stage, detail):
    """Call progress callback if provided. Works sync or async."""
    if callback is None:
        return
    try:
        result = callback(stage, detail)
        # If it returns a coroutine, we can't await here (sync context).
        # Store it for the caller but ignore for now — pipeline is sync.
        if result is not None and hasattr(result, '__await__'):
            pass  # async callback in sync context — silently skip
    except Exception:
        pass
