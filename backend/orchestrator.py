"""Atlas orchestrator — main coordination logic using deepagents."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from subagents.parser_subagent import create_parser_subagent
from subagents.tracer_subagent import create_tracer_subagent
from tools.artifact_tools import list_claim_files, read_claim_file
from tools.pdf_tools import extract_page_text, get_pdf_page_count, write_claims
from tools.excel_tools import read_excel_cell, read_excel_summary, count_csv_rows, write_evidence
from tools.validator_tool import validate_claim, compute_total

load_dotenv()

MODEL = os.environ.get("ORCHESTRATOR_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None
WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace")))
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"

_atlas_orchestrator = None


def _make_model():
    return ChatDeepSeek(
        model=MODEL,
        temperature=0,
        max_tokens=4096,
    base_url=DEEPSEEK_API_BASE,
    timeout=60.0,
    max_retries=2,
    disabled_params={"thinking": None},
    )


def is_llm_available() -> bool:
    """Return whether the DeepSeek client can be constructed from the current env."""
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


PARSER_SYSTEM_PROMPT = """You are a CSRD Audit Parser subagent.

Your task: Extract ALL numerical claims from assigned PDF pages.

For each claim, identify:
1. The ESRS data point name (use these exact IDs):
   - scope1_emission: Scope 1 emissions in tonnes CO2eq
   - scope2_emission: Scope 2 emissions in tonnes CO2eq
   - scope1_scope2_total: Sum of Scope 1 + Scope 2
   - headcount: Total employee headcount
   - renewable_pct: Renewable energy percentage
   - training_participants: Number of training participants
   - scope3_emission: Scope 3 emissions in tonnes CO2eq
   - production_sites: Number of production sites

2. The numeric value and unit (extract exactly as written)
3. The page and paragraph number
4. The claimed source document from the (Source: ...) reference

Output each claim as a JSON object with this structure:
{
  "data_point": "scope2_emission",
  "claimed_value": 4200,
  "unit": "tonnes CO2eq",
  "page": 4,
  "paragraph_idx": 3,
  "source_hint": "energia_2024.xlsx",
  "claim_text": "The company's Scope 2 emissions for 2024 were 4,200 tonnes CO2 equivalent."
}

CRITICAL: Only extract claims that contain NUMBERS. Skip general narrative text.
Save ALL claims using the write_claims tool when done with your assigned pages.
"""

TRACER_SYSTEM_PROMPT = """You are a CSRD Audit Tracer subagent.

Your task: For every claim assigned to you, find the source value in the original document and validate it.

Workflow:
1. List claim files from workspace/claims/ and read every claim batch
2. For each claim, use the source_hint to find the right source file
3. Look up the actual value in the source document using the appropriate tool:
   - Excel files → read_excel_cell (probe with read_excel_summary first to find sheet/column names)
   - CSV files → count_csv_rows
4. Compare claimed vs source using validate_claim
5. Save one combined evidence batch using write_evidence

Evidence output format:
{
  "data_point": "scope2_emission",
  "claim_text": "...",
  "claimed_value": 4200,
  "source_value": 4020,
  "unit": "tonnes CO2eq",
  "source_file": "energia_2024.xlsx",
  "source_sheet": "Scope1_Scope2",
  "source_cell": "C5",
  "flag": "red",
  "deviation_pct": 4.48,
  "explanation": "Claimed: 4200 tonnes CO2eq, Source: 4020 tonnes CO2eq, Deviation: 4.48%",
  "page": 4
}

IMPORTANT: For scope1_scope2_total, compute the sum from source values (scope1 + scope2) and compare
against the PDF claim. Use compute_total tool.
"""

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Atlas CSRD Audit Orchestrator.

Your job:
1. Ask the parser subagent to inspect the PDF and extract claims in 5-page batches.
2. Ensure every parser batch writes its output with write_claims.
3. Ask the tracer subagent to read all claim batches, trace them back to source files, validate them, and persist a combined evidence batch.
4. Return a concise execution summary only.

Rules:
- Delegate parser work only to the parser subagent.
- Delegate tracing and validation work only to the tracer subagent.
- Keep outputs concise. The Python runtime will assemble the final report.
"""


def create_atlas_orchestrator():
    """Create the Atlas CSRD Audit orchestrator with DeepSeek."""
    model = _make_model()

    parser_subagent = {
        "name": "parser",
        "description": "Extracts numerical sustainability claims from PDF pages.",
        "system_prompt": PARSER_SYSTEM_PROMPT,
        "tools": [extract_page_text, get_pdf_page_count, write_claims],
        "model": _make_model(),
    }

    tracer_subagent = {
        "name": "tracer",
        "description": "Traces each claim back to its source document and validates the values.",
        "system_prompt": TRACER_SYSTEM_PROMPT,
        "tools": [list_claim_files, read_claim_file, read_excel_cell, read_excel_summary, count_csv_rows, validate_claim, compute_total, write_evidence],
        "model": _make_model(),
    }

    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        subagents=[
            parser_subagent,
            tracer_subagent,
        ],
        name="atlas_orchestrator",
    )




def _page_ranges(total_pages: int, batch_size: int = 5) -> list[str]:
    return [
        f"{start}-{min(start + batch_size - 1, total_pages)}"
        for start in range(1, total_pages + 1, batch_size)
    ]


def _read_json_batches(directory: Path) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    if not directory.exists():
        return payload

    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            payload.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            payload.append(data)

    return payload


def _build_report(pdf_path: Path, claims: list[dict[str, Any]], findings: list[dict[str, Any]], parser_mode: str) -> dict:
    from pipeline import INPUT_DIR, REPORT_PATH, _compute_summary, _get_page_count, _infer_document_role

    started_at = datetime.now(timezone.utc).isoformat()
    completed_at = datetime.now(timezone.utc).isoformat()
    summary = _compute_summary(findings)
    report = {
        "audit_metadata": {
            "document": pdf_path.name,
            "standard": "ESRS E1 — Climate Change",
            "framework": "EU CSRD",
            "pipeline": "deepagents-supervised",
            "parser_mode": parser_mode,
            "started_at": started_at,
            "completed_at": completed_at,
            "total_pages": _get_page_count(pdf_path),
            "total_claims_found": len(claims),
            "total_findings": len(findings),
        },
        "document_inventory": [
            {
                "filename": path.name,
                "type": path.suffix,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "role": _infer_document_role(path.name),
            }
            for path in sorted(INPUT_DIR.glob("*"))
            if path.is_file()
        ],
        "findings": findings,
        "summary": summary,
        "red_flags": summary.get("red_flags", []),
        "review_required": summary.get("review_required", False),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _run_deepagents_demo_audit(progress_callback=None, pdf_filename: str = "atlas_sustainability_statement.pdf") -> dict:
    from pipeline import _emit, _get_page_count, _resolve_pdf_path, reset_workspace

    reset_workspace()
    pdf_path = _resolve_pdf_path(pdf_filename)
    total_pages = _get_page_count(pdf_path)
    page_ranges = _page_ranges(total_pages)

    _emit(progress_callback, "status", {
        "message": "Atlas CSRD Audit Engine initializing deepagents supervisor...",
        "mode": "deepagents_demo",
    })
    _emit(progress_callback, "phase", {
        "phase": "build_audit_plan",
        "message": f"Orchestrator planning parser batches for {total_pages} pages",
    })
    _emit(progress_callback, "todo", {
        "items": [f"Parse pages {page_range}" for page_range in page_ranges] + ["Trace and validate all extracted claims"],
        "total": len(page_ranges) + 1,
    })

    parser_agent = create_parser_subagent()
    _emit(progress_callback, "phase", {
        "phase": "parse_claims",
        "message": "Parser subagents extracting claims in page batches...",
    })
    _emit(progress_callback, "agent_start", {
        "agent": "Orchestrator",
        "task": f"Dispatching {len(page_ranges)} parser batches",
    })

    for page_range in page_ranges:
        _emit(progress_callback, "agent_progress", {
            "agent": "Orchestrator",
            "message": f"Delegating parser batch {page_range}",
        })
        parser_agent.invoke({
            "messages": [{
                "role": "user",
                "content": (
                    f"Parse only pages {page_range} from {pdf_path.name}. "
                    f"Call extract_page_text for each page in this range, extract all supported numerical claims, "
                    f"then call write_claims exactly once with page_range=\"{page_range}\" and the JSON array of claims. "
                    "Return a one-line summary after saving the claims."
                ),
            }],
        })

    claims = _read_json_batches(CLAIMS_DIR)
    if not claims:
        raise RuntimeError("Deepagents parser produced no claims")

    for index, claim in enumerate(claims, start=1):
        _emit(progress_callback, "agent_progress", {
            "agent": "Parser",
            "data_point": claim.get("data_point"),
            "claimed_value": claim.get("claimed_value"),
            "unit": claim.get("unit"),
            "page": claim.get("page"),
            "progress": f"{index}/{len(claims)}",
        })

    _emit(progress_callback, "agent_done", {
        "agent": "Parser",
        "claims_found": len(claims),
        "message": f"{len(claims)} claims extracted by deepagents parser workers",
    })

    tracer_agent = create_tracer_subagent()
    _emit(progress_callback, "phase", {
        "phase": "trace_sources",
        "message": "Tracer subagent resolving claims to source evidence...",
    })
    _emit(progress_callback, "agent_start", {
        "agent": "Tracer",
        "task": f"Tracing {len(claims)} extracted claims",
    })
    tracer_agent.invoke({
        "messages": [{
            "role": "user",
            "content": (
                "Load every claim batch using list_claim_files and read_claim_file. "
                "Trace and validate every claim using the available source tools. "
                "Write one combined evidence array via write_evidence with batch_name=\"batch_1\". "
                "Return a short summary after saving the evidence."
            ),
        }],
    })

    findings = _read_json_batches(EVIDENCE_DIR)
    if not findings:
        raise RuntimeError("Deepagents tracer produced no evidence")

    for index, finding in enumerate(findings, start=1):
        _emit(progress_callback, "agent_progress", {
            "agent": "Tracer",
            "data_point": finding.get("data_point"),
            "claimed_value": finding.get("claimed_value"),
            "progress": f"{index}/{len(findings)}",
        })
        if finding.get("flag") == "red":
            _emit(progress_callback, "finding", {
                "agent": "Tracer",
                "data_point": finding.get("data_point"),
                "flag": "red",
                "claimed_value": finding.get("claimed_value"),
                "source_value": finding.get("source_value"),
                "deviation_pct": finding.get("deviation_pct"),
                "message": f"DISCREPANCY — {finding.get('deviation_pct')}% deviation",
            })

    _emit(progress_callback, "agent_done", {
        "agent": "Tracer",
        "findings": len(findings),
        "message": f"{len(findings)} findings traced and validated by deepagents tracer",
    })

    report = _build_report(pdf_path, claims, findings, parser_mode="deepagents")
    summary = report["summary"]
    _emit(progress_callback, "phase", {
        "phase": "validate_findings",
        "message": f"Validation complete — {summary.get('red_count', 0)} material misstatements",
    })
    _emit(progress_callback, "agent_start", {
        "agent": "Reporter",
        "task": "Building audit report and evidence package",
    })
    _emit(progress_callback, "agent_done", {
        "agent": "Reporter",
        "message": "Evidence package saved to audit_report.json",
    })
    _emit(progress_callback, "phase", {
        "phase": "build_report",
        "message": "Report complete — evidence package ready",
    })
    _emit(progress_callback, "complete", {
        "summary": summary,
        "evidence": report["findings"],
        "total_findings": len(findings),
        "review_required": report.get("review_required", False),
    })
    return report


def get_atlas_orchestrator():
    """Lazily construct the orchestrator so imports do not fail without env setup."""
    global _atlas_orchestrator
    if _atlas_orchestrator is None:
        _atlas_orchestrator = create_atlas_orchestrator()
    return _atlas_orchestrator


def run_live_llm_audit(progress_callback=None, pdf_filename: str = "atlas_sustainability_statement.pdf") -> dict:
    """Run the live audit using deepagents workers, with deterministic fallback."""
    from pipeline import _emit, run_full_audit

    try:
        return _run_deepagents_demo_audit(
            progress_callback=progress_callback,
            pdf_filename=pdf_filename,
        )
    except Exception as exc:
        _emit(progress_callback, "status", {
            "message": f"Deepagents runtime failed. Falling back to the stable LLM-assisted pipeline. Reason: {exc}",
            "mode": "live_llm_fallback",
        })
        return run_full_audit(
            pdf_filename=pdf_filename,
            progress_callback=progress_callback,
            parser_mode="llm",
        )