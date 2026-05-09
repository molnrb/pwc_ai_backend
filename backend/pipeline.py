"""
Deterministic CSRD Audit Pipeline — no LLM required for the core audit logic.

This runs the full Parse → Trace → Validate → Report flow using direct
tool calls. It's the reliable fallback and the default execution path.
The deepagents orchestration is available as an advanced/experimental mode.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import fitz  # pymupdf
import pandas as pd
from dotenv import load_dotenv

from input_bundle import get_input_dir, get_statement_filename, load_audit_manifest

try:
    from langchain_core.messages import HumanMessage
    from langchain_deepseek import ChatDeepSeek
except Exception:  # pragma: no cover - optional live LLM path
    HumanMessage = None
    ChatDeepSeek = None

# ── New generic pipeline imports (Phase 1-6 modules) ──────────────────
try:
    from ingestion.document_store import DocumentStore, get_document_store
    from extraction.candidate_extractor import extract_candidates_deterministic
    from extraction.pdf_candidate_extractor import extract_pdf_candidates
    from normalization.claim_normalizer import ClaimNormalizer, get_normalizer
    from retrieval.evidence_retriever import EvidenceRetriever, get_retriever
    from retrieval.tabular_evidence_search import find_tabular_evidence
    from retrieval.pdf_evidence_search import find_pdf_evidence
    from resolution.match_resolver import resolve_best_match
    from resolution.validation_engine import validate as validate_claim_generic
    from ontology.loader import get_ontology
    _GENERIC_PIPELINE_AVAILABLE = True
except ImportError as _gen_err:  # pragma: no cover
    _GENERIC_PIPELINE_AVAILABLE = False
    logger = None  # will be set below

load_dotenv()

WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace")))
INPUT_DIR = get_input_dir(WORKSPACE)
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"
REPORT_PATH = WORKSPACE / "audit_report.json"
PARSER_MODEL = os.environ.get("PARSER_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None
LLM_MAX_PARSE_RETRIES = int(os.environ.get("LLM_MAX_PARSE_RETRIES", "3"))

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=os.environ.get("ATLAS_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

logger = logging.getLogger("atlas.pipeline")
logger.setLevel(os.environ.get("ATLAS_LOG_LEVEL", "INFO"))

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

DATA_POINT_UNITS = {data_point: unit for _, data_point, unit, _ in CLAIM_PATTERNS}


# ── Public API ─────────────────────────────────────────────────────────


def run_full_audit(
    pdf_filename: str = "atlas_sustainability_statement.pdf",
    progress_callback=None,
    parser_mode: str = "auto",
) -> dict:
    """Run the complete deterministic audit pipeline.

    Args:
        pdf_filename: PDF in workspace/input/
        progress_callback: Optional callable(stage, detail) — sync or async

    Returns:
        Full audit report dict with metadata, document_inventory, findings, summary
    """
    _ensure_dirs()
    started_at = datetime.now(timezone.utc).isoformat()
    pdf_path = _resolve_pdf_path(pdf_filename)
    pdf_filename = pdf_path.name
    parser_mode_used = _resolve_parser_mode(parser_mode)

    # ── Phase: catalog_inputs ──
    _emit(progress_callback, "phase", {"phase": "catalog_inputs", "message": "Cataloging input documents..."})
    input_files = sorted(
        [{"name": f.name, "size_kb": round(f.stat().st_size / 1024, 1), "type": f.suffix} for f in INPUT_DIR.iterdir() if f.is_file()],
        key=lambda x: x["name"],
    )
    _emit(progress_callback, "phase", {"phase": "catalog_inputs", "message": f"Found {len(input_files)} input files", "files": input_files})

    # ── Phase: build_audit_plan ──
    _emit(progress_callback, "phase", {"phase": "build_audit_plan", "message": "Building audit plan for ESRS E1 — Climate Change"})
    todos = _build_todo_list(SOURCE_MAP)
    _emit(progress_callback, "todo", {"items": todos, "total": len(todos)})
    _emit(progress_callback, "phase", {"phase": "build_audit_plan", "message": f"Audit plan ready — {len(CLAIM_PATTERNS)} claim patterns, {len(SOURCE_MAP)} data points with source mappings"})

    # ── Phase: parse_claims (Parser agent) ──
    parse_message = (
        "Parser analyzing sustainability statement with DeepSeek..."
        if parser_mode_used == "llm"
        else "Parser analyzing sustainability statement..."
    )
    _emit(progress_callback, "phase", {"phase": "parse_claims", "message": parse_message})
    _emit(progress_callback, "agent_start", {
        "agent": "Parser",
        "task": f"Extracting ESRS E1 claims from {pdf_filename}",
        "mode": parser_mode_used,
    })
    try:
        claims = _parse_pdf_with_llm(pdf_path) if parser_mode_used == "llm" else _parse_pdf(pdf_path)
    except Exception as exc:
        if parser_mode_used != "llm":
            raise
        parser_mode_used = "deterministic_fallback"
        _emit(progress_callback, "status", {
            "message": f"LLM parser unavailable. Falling back to deterministic extraction. Reason: {exc}",
            "mode": "live_deterministic",
        })
        claims = _parse_pdf(pdf_path)
    if parser_mode_used == "llm":
        claims, backfilled = _merge_claim_sets(claims, _parse_pdf(pdf_path))
        if backfilled:
            parser_mode_used = "llm_hybrid"
            _emit(progress_callback, "status", {
                "message": f"LLM parser missed {backfilled} claim(s). Atlas backfilled them deterministically.",
                "mode": "live_llm_hybrid",
            })
    for i, claim in enumerate(claims):
        _emit(progress_callback, "agent_progress", {
            "agent": "Parser",
            "data_point": claim["data_point"],
            "claimed_value": claim["claimed_value"],
            "unit": claim["unit"],
            "page": claim["page"],
            "progress": f"{i+1}/{len(claims)}",
        })
    _emit(progress_callback, "agent_done", {
        "agent": "Parser",
        "claims_found": len(claims),
        "mode": parser_mode_used,
        "message": (
            f"{len(claims)} claims extracted with LLM assistance"
            if parser_mode_used == "llm"
            else f"{len(claims)} claims extracted with LLM assistance and deterministic backfill"
            if parser_mode_used == "llm_hybrid"
            else f"{len(claims)} claims extracted deterministically"
        ),
    })
    _emit(progress_callback, "phase", {"phase": "parse_claims", "message": f"Parsing complete — {len(claims)} claims extracted"})

    # Save raw claims
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    claims_path = CLAIMS_DIR / "all_claims.json"
    claims_path.write_text(json.dumps(claims, indent=2, ensure_ascii=False))

    # ── Phase: trace_sources (Tracer agent) ──
    _emit(progress_callback, "phase", {"phase": "trace_sources", "message": "Tracer resolving source documents..."})
    _emit(progress_callback, "agent_start", {"agent": "Tracer", "task": f"Tracing {len(claims)} claims to source documents"})
    findings = []
    for i, claim in enumerate(claims):
        dp = claim["data_point"]
        _emit(progress_callback, "agent_progress", {
            "agent": "Tracer",
            "data_point": dp,
            "claimed_value": claim["claimed_value"],
            "progress": f"{i+1}/{len(claims)}",
        })
        finding = _trace_and_validate(claim)
        findings.append(finding)
        if finding.get("flag") == "red":
            _emit(progress_callback, "finding", {
                "agent": "Tracer",
                "data_point": dp,
                "flag": "red",
                "claimed_value": finding.get("claimed_value"),
                "source_value": finding.get("source_value"),
                "deviation_pct": finding.get("deviation_pct"),
                "message": f"DISCREPANCY — {finding.get('deviation_pct')}% deviation",
            })

    _emit(progress_callback, "agent_done", {"agent": "Tracer", "findings": len(findings),
        "sources_resolved": sum(1 for f in findings if f.get("source_file"))})
    _emit(progress_callback, "phase", {"phase": "trace_sources", "message": f"Trace complete — {len(findings)} findings"})

    # Save evidence
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / "all_evidence.json"
    evidence_path.write_text(json.dumps(findings, indent=2, ensure_ascii=False))

    # ── Phase: validate_findings (Validator agent) ──
    _emit(progress_callback, "phase", {"phase": "validate_findings", "message": "Validator running deterministic checks..."})
    _emit(progress_callback, "agent_start", {"agent": "Validator", "task": "Running deterministic validation on all findings"})
    red_count = sum(1 for f in findings if f.get("flag") == "red")
    yellow_count = sum(1 for f in findings if f.get("flag") == "yellow")
    green_count = sum(1 for f in findings if f.get("flag") == "green")
    grey_count = sum(1 for f in findings if f.get("flag") == "grey")
    _emit(progress_callback, "agent_progress", {
        "agent": "Validator",
        "green": green_count, "yellow": yellow_count, "red": red_count, "grey": grey_count,
    })
    _emit(progress_callback, "agent_done", {"agent": "Validator",
        "message": f"Validation complete — {green_count} green, {yellow_count} yellow, {red_count} red, {grey_count} grey"})
    _emit(progress_callback, "phase", {"phase": "validate_findings", "message": f"Validation complete — {red_count} material misstatements" if red_count > 0 else "Validation complete — all clear"})

    # ── Phase: build_report (Reporter agent) ──
    _emit(progress_callback, "phase", {"phase": "build_report", "message": "Reporter assembling evidence package..."})
    _emit(progress_callback, "agent_start", {"agent": "Reporter", "task": "Building audit report and evidence package"})
    summary = _compute_summary(findings)
    completed_at = datetime.now(timezone.utc).isoformat()

    # Build document inventory
    document_inventory = []
    for f in sorted(INPUT_DIR.glob("*")):
        if f.is_file():
            document_inventory.append({
                "filename": f.name,
                "type": f.suffix,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "role": _infer_document_role(f.name),
            })

    report = {
        "audit_metadata": {
            "document": pdf_filename,
            "standard": "ESRS E1 — Climate Change",
            "framework": "EU CSRD",
            "pipeline": "llm-assisted" if parser_mode_used in {"llm", "llm_hybrid"} else "deterministic",
            "parser_mode": parser_mode_used,
            "started_at": started_at,
            "completed_at": completed_at,
            "total_pages": _get_page_count(pdf_path),
            "total_claims_found": len(claims),
            "total_findings": len(findings),
        },
        "document_inventory": document_inventory,
        "findings": findings,
        "summary": summary,
        "red_flags": summary.get("red_flags", []),
        "review_required": summary.get("review_required", False),
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    _emit(progress_callback, "agent_done", {"agent": "Reporter", "message": "Evidence package saved to audit_report.json"})
    _emit(progress_callback, "phase", {"phase": "build_report", "message": "Report complete — evidence package ready"})
    _emit(progress_callback, "complete", {
        "pipeline": report["audit_metadata"]["pipeline"],
        "parser_mode": report["audit_metadata"]["parser_mode"],
        "summary": summary,
        "total_findings": len(findings),
        "review_required": summary.get("review_required", False),
    })

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
    claims = []
    seen_data_points: set[str] = set()

    for block in _extract_pdf_blocks(pdf_path):
        page_num = block["page"]
        block_idx = block["paragraph_idx"]
        text = block["text"]

        for pattern, dp_id, unit, min_val in CLAIM_PATTERNS:
            if dp_id in seen_data_points:
                continue

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
            break

    return claims


def _parse_pdf_with_llm(pdf_path: Path) -> list[dict]:
    """Extract claims with an LLM-first parser and normalize to the audit schema."""
    if not _llm_parser_available():
        raise RuntimeError("DeepSeek parser is not configured")

    blocks = _extract_pdf_blocks(pdf_path)
    if not blocks:
        return []

    prompt = (
        "You are extracting audit claims from a sustainability statement. "
        "Return JSON only. Use only these data_point values: "
        f"{', '.join(sorted(SOURCE_MAP))}. "
        "For each supported numerical claim, return: data_point, claimed_value, unit, page, paragraph_idx, claim_text. "
        "Use the exact page and paragraph_idx from the provided blocks. "
        "Return a JSON array and do not include commentary."
    )
    block_payload = json.dumps(blocks, ensure_ascii=False)
    last_error = None

    for attempt in range(1, LLM_MAX_PARSE_RETRIES + 1):
        try:
            model = _make_parser_model()
            response = model.invoke([
                HumanMessage(content=f"{prompt}\n\nDocument blocks:\n{block_payload}")
            ])
            raw_payload = _message_content_to_text(response.content)
            parsed = _parse_llm_json_payload(raw_payload)
            claims = _normalize_llm_claims(parsed, blocks)
            if claims:
                return claims
            raise ValueError("LLM returned no supported claims")
        except Exception as exc:  # pragma: no cover - external service path
            last_error = exc
            if attempt < LLM_MAX_PARSE_RETRIES:
                time.sleep(attempt)

    raise RuntimeError(f"DeepSeek parse failed after {LLM_MAX_PARSE_RETRIES} attempt(s): {last_error}")


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
        # A4 — Explicit grey finding with meaningful explanation
        return {
            **base,
            "flag": "grey",
            "deviation_pct": None,
            "source_value": None,
            "source_file": None,
            "source_sheet": None,
            "source_cell": None,
            "explanation": f"Missing evidence: No source document configured for '{dp}'. Manual verification required — auditor must locate supporting documentation.",
            "review_required": True,
        }

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
        # A4 — Error reading source also produces grey finding with review flag
        return {
            **base,
            "flag": "grey",
            "deviation_pct": None,
            "source_value": None,
            "source_file": source_file,
            "source_sheet": source_info.get("sheet"),
            "source_cell": None,
            "explanation": f"Error reading source file '{source_file}': {e}. Manual verification required.",
            "review_required": True,
        }


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
        return {
            **base,
            "flag": "grey",
            "deviation_pct": None,
            "source_value": None,
            "source_file": source_info["file"],
            "source_sheet": sheet,
            "source_cell": None,
            "explanation": f"Row '{source_info['row']}' not found in sheet '{sheet}'. Source structure may have changed — manual verification required.",
            "review_required": True,
        }

    row = df[row_mask]
    idx = row.index[0]

    if col not in df.columns:
        return {
            **base,
            "flag": "grey",
            "deviation_pct": None,
            "source_value": None,
            "source_file": source_info["file"],
            "source_sheet": sheet,
            "source_cell": None,
            "explanation": f"Column '{col}' not found in sheet '{sheet}'. Available columns: {list(df.columns)}. Source structure may have changed — manual verification required.",
            "review_required": True,
        }

    raw_value = row[col].values[0]
    if pd.isna(raw_value):
        return {
            **base,
            "flag": "grey",
            "deviation_pct": None,
            "source_value": None,
            "source_file": source_info["file"],
            "source_sheet": sheet,
            "source_cell": f"{col}{idx + 2}",
            "explanation": f"Empty cell at {col}{idx + 2} in sheet '{sheet}'. Source value is missing — manual verification required.",
            "review_required": True,
        }

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
        return {
            **base,
            "flag": "grey",
            "deviation_pct": None,
            "source_value": None,
            "source_file": source_info["file"],
            "source_sheet": "Sheet1",
            "source_cell": None,
            "explanation": f"Column '{filter_col}' not found in CSV. Source structure may have changed — manual verification required.",
            "review_required": True,
        }

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
    """Run the deterministic validation math. Sets flag and review_required."""
    claimed = claim["claimed_value"]

    if source_value == 0:
        return {
            **base,
            "flag": "red",
            "deviation_pct": 100.0,
            "source_value": source_value,
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_cell": source_cell,
            "explanation": f"Source value is 0 — cannot compute deviation. Claimed: {claimed} {claim['unit']}. Requires immediate auditor investigation.",
            "review_required": True,
        }

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

    return {
        **base,
        "flag": flag,
        "deviation_pct": deviation_pct,
        "source_value": source_value,
        "source_file": source_file,
        "source_sheet": source_sheet,
        "source_cell": source_cell,
        "explanation": explanation,
        "review_required": flag == "red",
    }


# ── Helpers ────────────────────────────────────────────────────────────


def _parse_value(raw) -> float | int:
    """Parse a raw cell value, handling percentage strings."""
    if isinstance(raw, str) and raw.endswith("%"):
        return int(raw.replace("%", "").strip())
    return float(raw) if isinstance(raw, (int, float)) else int(raw)


def _extract_pdf_blocks(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract non-empty paragraph blocks with stable page/paragraph coordinates."""
    doc = fitz.open(str(pdf_path))
    blocks: list[dict[str, Any]] = []
    for page_num in range(1, len(doc) + 1):
        page = doc[page_num - 1]
        for block_idx, block in enumerate(page.get_text("blocks")):
            text = block[4].strip()
            if text:
                blocks.append({"page": page_num, "paragraph_idx": block_idx, "text": text})
    doc.close()
    return blocks


def _resolve_parser_mode(parser_mode: str) -> str:
    if parser_mode == "llm":
        return "llm"
    if parser_mode == "deterministic":
        return "deterministic"
    return "llm" if _llm_parser_available() else "deterministic"


def _llm_parser_available() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY")) and ChatDeepSeek is not None and HumanMessage is not None


def _make_parser_model() -> Any:
    if ChatDeepSeek is None:
        raise RuntimeError("langchain-deepseek is not installed")
    return ChatDeepSeek(
        model=PARSER_MODEL,
        temperature=0,
        max_tokens=4096,
        base_url=DEEPSEEK_API_BASE,
        timeout=60.0,
        max_retries=2,
        disabled_params={"thinking": None},
    )


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            else:
                parts.append(json.dumps(item, ensure_ascii=False))
        return "\n".join(parts)
    return str(content)


def _parse_llm_json_payload(raw_payload: str) -> Any:
    cleaned = raw_payload.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"(^```(?:json)?\s*)|(\s*```$)", "", cleaned, flags=re.DOTALL).strip()

    for candidate in (cleaned, _extract_json_candidate(cleaned, "[", "]"), _extract_json_candidate(cleaned, "{", "}")):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("Could not parse JSON from LLM response")


def _extract_json_candidate(text: str, start_token: str, end_token: str) -> str | None:
    start_idx = text.find(start_token)
    end_idx = text.rfind(end_token)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None
    return text[start_idx:end_idx + 1]


def _normalize_llm_claims(raw_claims: Any, blocks: list[dict[str, Any]]) -> list[dict]:
    if isinstance(raw_claims, dict):
        raw_claims = raw_claims.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ValueError("LLM payload must be a list of claims")

    block_lookup = {(item["page"], item["paragraph_idx"]): item["text"] for item in blocks}
    normalized = []
    seen_data_points: set[str] = set()

    def _sort_key(item: dict) -> tuple[int, int]:
        return (int(item.get("page", 0) or 0), int(item.get("paragraph_idx", 0) or 0))

    for item in sorted((claim for claim in raw_claims if isinstance(claim, dict)), key=_sort_key):
        data_point = item.get("data_point")
        if data_point not in SOURCE_MAP or data_point in seen_data_points:
            continue

        page = int(item.get("page", 0) or 0)
        paragraph_idx = int(item.get("paragraph_idx", 0) or 0)
        if page < 1:
            continue

        claimed_value = _coerce_numeric(item.get("claimed_value"))
        claim_text = str(item.get("claim_text") or block_lookup.get((page, paragraph_idx), "")).strip()
        if claimed_value is None or not claim_text:
            continue

        source_info = SOURCE_MAP.get(data_point)
        source_hint = source_info.get("file", "unknown") if source_info else "unknown"
        normalized.append({
            "data_point": data_point,
            "claimed_value": claimed_value,
            "unit": str(item.get("unit") or DATA_POINT_UNITS.get(data_point, "")),
            "page": page,
            "paragraph_idx": paragraph_idx,
            "source_hint": source_hint,
            "claim_text": claim_text,
        })
        seen_data_points.add(data_point)

    return normalized


def _merge_claim_sets(primary_claims: list[dict], fallback_claims: list[dict]) -> tuple[list[dict], int]:
    """Keep primary claims and backfill missing data points from a fallback parser."""
    merged = list(primary_claims)
    seen = {claim["data_point"] for claim in primary_claims}
    backfilled = 0

    for claim in fallback_claims:
        if claim["data_point"] in seen:
            continue
        merged.append(claim)
        seen.add(claim["data_point"])
        backfilled += 1

    merged.sort(key=lambda item: (item.get("page", 0), item.get("paragraph_idx", 0)))
    return merged, backfilled


def _coerce_numeric(raw_value: Any) -> int | float | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return int(raw_value) if float(raw_value).is_integer() else float(raw_value)

    cleaned = str(raw_value).strip().replace(" ", "").replace(",", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    if not cleaned:
        return None

    try:
        value = float(cleaned)
    except ValueError:
        return None
    return int(value) if value.is_integer() else value


def _resolve_pdf_path(pdf_filename: str) -> Path:
    candidate_names = []
    configured_statement = get_statement_filename(default_filename=None, workspace_dir=WORKSPACE)
    if configured_statement:
        candidate_names.append(configured_statement)
    if pdf_filename and pdf_filename not in candidate_names:
        candidate_names.append(pdf_filename)

    for candidate_name in candidate_names:
        candidate = INPUT_DIR / candidate_name
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


def _infer_document_role(filename: str) -> str:
    """Infer the role of a document from its filename."""
    manifest = load_audit_manifest(WORKSPACE)
    if manifest is not None:
        statement = manifest.get("statement_document")
        if isinstance(statement, dict) and Path(str(statement.get("path", ""))).name == filename:
            return "statement"
        if filename == "audit_index.json":
            return "manifest_internal"

    name = filename.lower()
    if "statement" in name or "sustainability" in name:
        return "statement"
    if "excerpt" in name:
        return "statement"
    if "energia" in name and "szamla" in name:
        return "supporting_invoice"
    if "energia" in name:
        return "energy_source"
    if "hr" in name or "human" in name:
        return "hr_source"
    if "scope3" in name or "szallito" in name:
        return "scope3_source"
    if "invoice" in name:
        return "source_document"
    if "register" in name:
        return "registry"
    if "workbook" in name:
        return "calculation_workbook"
    return "supporting"


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

    # A7 — review_required: true if any red or grey (missing evidence) findings
    has_red = red > 0
    has_missing_evidence = grey > 0
    review_required = has_red or has_missing_evidence

    return {
        "green_count": green,
        "yellow_count": yellow,
        "red_count": red,
        "grey_count": grey,
        "total": len(findings),
        "material_red_count": red,
        "red_flags": red_flags,
        "review_required": review_required,
        "verdict": "PASS" if not has_red else "FAIL — material misstatements detected",
        "materiality_note": (
            f"Material errors found: {red}. "
            f"Auditor must investigate red flags before signing off."
        ) if has_red else "No material misstatements. Report is consistent with source data.",
    }


def _build_todo_list(source_map: dict) -> list[str]:
    """Build a human-readable audit task list from the source map."""
    todos = [
        "Analyze PDF structure (ESRS E1 claims)",
        "Extract all numerical claims from sustainability statement",
    ]
    for dp_id, info in source_map.items():
        if info is None:
            todos.append(f"Trace {dp_id} — NO SOURCE (manual verification needed)")
        elif "computed" in info:
            todos.append(f"Trace {dp_id} → {info['file']} ({info['sheet']}) — computed field")
        elif info.get("type") == "csv":
            todos.append(f"Trace {dp_id} → {info['file']} (CSV row count)")
        else:
            todos.append(f"Trace {dp_id} → {info['file']} ({info['sheet']} / {info.get('col', '?')})")
    todos.append("Run deterministic validation on all claims")
    todos.append("Generate audit evidence package (audit_report.json)")
    return todos


def _ensure_dirs():
    for d in [CLAIMS_DIR, EVIDENCE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _log_event(stage: str, detail: Any) -> None:
    if not isinstance(detail, dict):
        logger.info("[%s] %s", stage.upper(), detail)
        return

    if stage == "phase":
        logger.info("[PHASE] %s", detail.get("message", detail.get("phase", "")))
        return
    if stage == "agent_start":
        logger.info("[AGENT:%s] START %s", detail.get("agent", "unknown"), detail.get("task", ""))
        return
    if stage == "agent_progress":
        parts = []
        if detail.get("data_point"):
            parts.append(str(detail["data_point"]))
        if detail.get("claimed_value") is not None:
            parts.append(str(detail["claimed_value"]))
        if detail.get("unit"):
            parts.append(str(detail["unit"]))
        if detail.get("progress"):
            parts.append(f"({detail['progress']})")
        if not parts:
            parts.append(json.dumps(detail, ensure_ascii=False))
        logger.info("[AGENT:%s] PROGRESS %s", detail.get("agent", "unknown"), " ".join(parts))
        return
    if stage == "agent_done":
        logger.info("[AGENT:%s] DONE %s", detail.get("agent", "unknown"), detail.get("message", json.dumps(detail, ensure_ascii=False)))
        return
    if stage == "finding":
        logger.warning(
            "[FINDING] %s flag=%s claimed=%s source=%s deviation=%s",
            detail.get("data_point", "unknown"),
            detail.get("flag", "unknown"),
            detail.get("claimed_value"),
            detail.get("source_value"),
            detail.get("deviation_pct"),
        )
        return
    if stage == "complete":
        logger.info("[COMPLETE] %s", json.dumps(detail, ensure_ascii=False))
        return
    if stage == "error":
        logger.error("[ERROR] %s", detail.get("message", json.dumps(detail, ensure_ascii=False)))
        return
    if stage == "status":
        logger.info("[STATUS] %s", detail.get("message", json.dumps(detail, ensure_ascii=False)))
        return
    if stage == "todo":
        logger.info("[TODO] %s items planned", detail.get("total", len(detail.get("items", []))))
        return

    logger.info("[%s] %s", stage.upper(), json.dumps(detail, ensure_ascii=False))


# ── Generic Pipeline (Phase 7 integration) ────────────────────────────


def run_generic_audit(
    pdf_filename: str = "atlas_sustainability_statement.pdf",
    progress_callback=None,
) -> dict:
    """Run the full generic pipeline using layers 1-6.

    This is the new pipeline path that uses:
    - Ingestion → Candidate Extraction → Normalization → Evidence Retrieval
    - Resolution → Deterministic Validation → Report

    Falls back to run_full_audit() if the generic pipeline modules are unavailable.
    """
    if not _GENERIC_PIPELINE_AVAILABLE:
        logger.warning("Generic pipeline modules unavailable — using legacy pipeline")
        return run_full_audit(pdf_filename=pdf_filename, progress_callback=progress_callback)

    _ensure_dirs()
    started_at = datetime.now(timezone.utc).isoformat()
    pdf_path = _resolve_pdf_path(pdf_filename)
    pdf_filename = pdf_path.name

    # ── Phase: ingest_documents ──
    _emit(progress_callback, "phase", {"phase": "ingest_documents", "message": "Ingesting all input documents..."})
    store = DocumentStore()
    store.ingest_all(INPUT_DIR)
    _emit(progress_callback, "phase", {"phase": "ingest_documents", "message": f"Ingested {len(store.assets)} documents"})

    # ── Phase: extract_candidates ──
    _emit(progress_callback, "phase", {"phase": "extract_candidates", "message": "Extracting claim candidates from statement PDF..."})
    candidates = extract_pdf_candidates(pdf_path)
    _emit(progress_callback, "phase", {"phase": "extract_candidates", "message": f"Extracted {len(candidates)} candidates"})

    # ── Phase: normalize_claims ──
    _emit(progress_callback, "phase", {"phase": "normalize_claims", "message": "Normalizing candidates to canonical claims..."})
    normalizer = get_normalizer()
    claims = normalizer.normalize(candidates)
    _emit(progress_callback, "phase", {"phase": "normalize_claims", "message": f"Normalized {len(claims)} claims"})

    # ── Phase: retrieve_evidence ──
    _emit(progress_callback, "phase", {"phase": "retrieve_evidence", "message": "Retrieving evidence candidates..."})
    retriever = get_retriever()
    for filename, sheet_tables in store.sheet_tables.items():
        retriever.add_excel_sheets(filename, sheet_tables)
    for filename, csv_table in store.csv_tables.items():
        retriever.add_csv_table(filename, csv_table)
    for filename, pdf_blocks in store.pdf_blocks.items():
        if filename != pdf_filename:  # Don't search the statement PDF for evidence of itself
            retriever.add_pdf_blocks(filename, pdf_blocks)

    all_evidence: dict[str, list] = {}
    for claim in claims:
        all_evidence[claim.claim_id] = retriever.retrieve(claim)
    _emit(progress_callback, "phase", {"phase": "retrieve_evidence", "message": f"Retrieved evidence for {len(claims)} claims"})

    # ── Phase: resolve_matches ──
    _emit(progress_callback, "phase", {"phase": "resolve_matches", "message": "Resolving best evidence matches..."})
    from resolution.match_resolver import resolve_for_claims
    resolved = resolve_for_claims(claims, all_evidence)
    resolved_evidence: dict[str, Optional[Any]] = {}
    for claim_id, match_tuple in resolved.items():
        if match_tuple is not None:
            resolved_evidence[claim_id] = match_tuple[1]  # EvidenceCandidate
        else:
            resolved_evidence[claim_id] = None
    _emit(progress_callback, "phase", {"phase": "resolve_matches", "message": f"Resolved matches for {len(resolved)} claims"})

    # ── Phase: validate_findings ──
    _emit(progress_callback, "phase", {"phase": "validate_findings", "message": "Running deterministic validation..."})
    from resolution.validation_engine import validate_all
    findings = validate_all(claims, resolved_evidence)
    _emit(progress_callback, "phase", {"phase": "validate_findings", "message": f"Validated {len(findings)} findings"})

    # ── Phase: build_report ──
    _emit(progress_callback, "phase", {"phase": "build_report", "message": "Assembling audit report..."})
    summary = _compute_summary_generic(findings)
    completed_at = datetime.now(timezone.utc).isoformat()

    document_inventory = []
    for f in sorted(INPUT_DIR.glob("*")):
        if f.is_file():
            document_inventory.append({
                "filename": f.name,
                "type": f.suffix,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "role": _infer_document_role(f.name),
            })

    # Convert findings to dicts for JSON
    findings_dicts = [_generic_finding_to_dict(f) for f in findings]

    report = {
        "audit_metadata": {
            "document": pdf_filename,
            "standard": "ESRS E1 — Climate Change",
            "framework": "EU CSRD",
            "pipeline": "generic_v1",
            "parser_mode": "generic_candidate_extraction",
            "started_at": started_at,
            "completed_at": completed_at,
            "total_pages": _get_page_count(pdf_path),
            "total_candidates": len(candidates),
            "total_claims_found": len(claims),
            "total_findings": len(findings),
        },
        "document_inventory": document_inventory,
        "findings": findings_dicts,
        "summary": summary,
        "red_flags": summary.get("red_flags", []),
        "review_required": summary.get("review_required", False),
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    _emit(progress_callback, "phase", {"phase": "build_report", "message": "Report complete — evidence package ready"})
    _emit(progress_callback, "complete", {
        "pipeline": report["audit_metadata"]["pipeline"],
        "parser_mode": report["audit_metadata"]["parser_mode"],
        "summary": summary,
        "total_findings": len(findings),
        "review_required": summary.get("review_required", False),
    })
    return report


def _generic_finding_to_dict(finding) -> dict:
    """Convert an AuditFinding model to a JSON-safe dict."""
    return {
        "data_point": finding.data_point,
        "claim_text": finding.claim_text,
        "claimed_value": finding.claimed_value,
        "source_value": finding.source_value,
        "unit": finding.unit,
        "flag": finding.flag,
        "deviation_pct": finding.deviation_pct,
        "extraction_confidence": finding.extraction_confidence,
        "mapping_confidence": finding.mapping_confidence,
        "retrieval_confidence": finding.retrieval_confidence,
        "review_required": finding.review_required,
        "explanation": finding.explanation,
        "source_file": finding.source_file,
        "source_sheet": finding.source_sheet,
        "source_cell": finding.source_cell,
        "page": finding.page,
        "paragraph_idx": finding.paragraph_idx,
        "review_reason": finding.review_reason,
        "provenance": finding.provenance,
    }


def _compute_summary_generic(findings: list) -> dict:
    """Compute summary from AuditFinding model objects."""
    green = sum(1 for f in findings if f.flag == "green")
    yellow = sum(1 for f in findings if f.flag == "yellow")
    red = sum(1 for f in findings if f.flag == "red")
    grey = sum(1 for f in findings if f.flag == "grey")

    red_flags = [
        {
            "data_point": f.data_point,
            "claimed": f.claimed_value,
            "actual": f.source_value,
            "deviation_pct": f.deviation_pct,
            "explanation": f.explanation,
        }
        for f in findings
        if f.flag == "red"
    ]

    review_required = any(f.review_required for f in findings)

    return {
        "green_count": green,
        "yellow_count": yellow,
        "red_count": red,
        "grey_count": grey,
        "total": len(findings),
        "material_red_count": red,
        "red_flags": red_flags,
        "review_required": review_required,
        "verdict": "PASS" if red == 0 else f"FAIL — {red} material misstatement(s) detected",
        "materiality_note": (
            f"{red} material error(s) found. Auditor must investigate flagged items before signing off."
            if red > 0
            else "No material misstatements. Report is consistent with source data."
        ),
    }


def _emit(callback, stage, detail):
    """Call progress callback if provided. Works sync or async."""
    _log_event(stage, detail)
    if callback is None:
        return
    try:
        result = callback(stage, detail)
        if result is not None and hasattr(result, '__await__'):
            pass
    except Exception:
        pass
