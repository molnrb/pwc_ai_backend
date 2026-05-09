"""Atlas orchestrator — main coordination logic using deepagents."""

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from input_bundle import get_input_dir

from subagents.parser_subagent import create_parser_subagent
from subagents.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    PARSER_SYSTEM_PROMPT,
    TRACER_SYSTEM_PROMPT,
)
from subagents.tracer_subagent import create_tracer_subagent, make_tracer_model
from tools.artifact_tools import list_claim_files, read_claim_file
from tools.csv_tools import profile_csv, search_csv_columns, find_csv_numeric_candidates
from tools.pdf_tools import (
    extract_document_page_text,
    extract_page_text,
    get_document_page_count,
    get_pdf_page_count,
    write_claims,
)
from tools.excel_tools import read_excel_cell, read_excel_summary, count_csv_rows, write_evidence
from tools.validator_tool import validate_claim, compute_total

load_dotenv()

MODEL = os.environ.get("ORCHESTRATOR_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None
WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace")))
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"
INPUT_DIR = get_input_dir(WORKSPACE)

_atlas_orchestrator = None
VALID_PIPELINE_MODES = {"auto", "deepagents", "generic", "legacy"}
TRACER_CONCURRENCY = max(1, int(os.environ.get("ATLAS_TRACER_CONCURRENCY", "2")))
PARSER_TIMEOUT_SECONDS = float(os.environ.get("ATLAS_PARSER_TIMEOUT_SECONDS", "300"))
PARSER_RETRY_TIMEOUT_SECONDS = float(os.environ.get("ATLAS_PARSER_RETRY_TIMEOUT_SECONDS", "420"))


def _make_model():
    return ChatDeepSeek(
        model=MODEL,
        temperature=0,
        max_tokens=4096,
        base_url=DEEPSEEK_API_BASE,
        timeout=180.0,
        max_retries=2,
        disabled_params={"thinking": None},
    )


def is_llm_available() -> bool:
    """Return whether the DeepSeek client can be constructed from the current env."""
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def get_pipeline_mode() -> str:
    """Return the configured pipeline mode from the environment."""
    raw_mode = os.environ.get("ATLAS_PIPELINE_MODE", "auto").strip().lower()
    if raw_mode in VALID_PIPELINE_MODES:
        return raw_mode

    return "auto"


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
        "tools": [
            list_claim_files,
            read_claim_file,
            read_excel_cell,
            read_excel_summary,
            count_csv_rows,
            profile_csv,
            search_csv_columns,
            find_csv_numeric_candidates,
            extract_document_page_text,
            get_document_page_count,
            validate_claim,
            compute_total,
            write_evidence,
        ],
        "model": make_tracer_model(),
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


# ── Helpers ────────────────────────────────────────────────────────────────


def _page_ranges(total_pages: int, batch_size: int = 3) -> list[str]:
    return [
        f"{start}-{min(start + batch_size - 1, total_pages)}"
        for start in range(1, total_pages + 1, batch_size)
    ]


def _normalize_finding(f: dict[str, Any]) -> dict[str, Any]:
    """Normalize evidence findings from tracer agents that may use non-standard schema fields."""
    if "flag" not in f and "validation" in f:
        f = dict(f)
        f["flag"] = f.pop("validation")
    if "explanation" not in f and "note" in f:
        f = dict(f)
        f["explanation"] = f.pop("note")
    return f


def _read_json_batches(directory: Path, pattern: str = "*.json") -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    if not directory.exists():
        return payload

    for path in sorted(directory.glob(pattern)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            payload.extend(_normalize_finding(item) for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            payload.append(_normalize_finding(data))

    return payload


def _claim_batch_files() -> list[Path]:
    if not CLAIMS_DIR.exists():
        return []

    return sorted(
        path for path in CLAIMS_DIR.glob("page_*.json")
        if path.is_file()
    )


def _claim_batch_path(page_range: str) -> Path:
    return CLAIMS_DIR / f"page_{page_range}.json"


def _evidence_batch_path(claim_batch_file: Path) -> Path:
    return EVIDENCE_DIR / claim_batch_file.name.replace("page_", "evidence_")


def _parser_batch_message(pdf_name: str, page_range: str, retry: bool = False) -> dict[str, Any]:
    retry_prefix = "Previous attempt did not save the required claim batch file. " if retry else ""
    return {
        "messages": [{
            "role": "user",
            "content": (
                f"{retry_prefix}"
                f"Parse only pages {page_range} from {pdf_name}. "
                f"Call extract_page_text for each page in this range, extract all supported numerical claims, "
                f"then call write_claims exactly once with page_range=\"{page_range}\" and the JSON array of claims. "
                f"The only allowed output file for this task is page_{page_range}.json. "
                "Do not write any scratch, helper, or differently named claim files. "
                "Return a one-line summary after saving the claims."
            ),
        }],
    }


async def _invoke_agent_async(agent: Any, payload: dict[str, Any]) -> Any:
    if hasattr(agent, "ainvoke"):
        return await agent.ainvoke(payload)
    return await asyncio.to_thread(agent.invoke, payload)


async def _parse_all_batches(parser_agent: Any, pdf_path: Path, page_ranges: list[str], progress_callback=None) -> list[Any]:
    from pipeline import _emit

    async def run_one(page_range: str) -> Any:
        _emit(progress_callback, "agent_progress", {
            "agent": "Orchestrator",
            "message": f"Delegating parser batch {page_range}",
        })
        return await _invoke_agent_async(parser_agent, _parser_batch_message(pdf_path.name, page_range))

    return await asyncio.gather(*(run_one(page_range) for page_range in page_ranges), return_exceptions=True)


async def _retry_missing_parser_batches(parser_agent: Any, pdf_path: Path, page_ranges: list[str], progress_callback=None) -> list[Any]:
    from pipeline import _emit

    results: list[Any] = []
    for page_range in page_ranges:
        _emit(progress_callback, "agent_progress", {
            "agent": "Orchestrator",
            "message": f"Retrying parser batch {page_range}",
        })
        results.append(
            await _invoke_agent_async(
                parser_agent,
                _parser_batch_message(pdf_path.name, page_range, retry=True),
            )
        )

    return results


def _emit_missing_batch_status(progress_callback, missing_page_ranges: list[str], claims_found: int) -> None:
    from pipeline import _emit

    joined_ranges = ", ".join(missing_page_ranges)
    _emit(progress_callback, "status", {
        "message": (
            "Parser batches still missing after extended retry: "
            f"{joined_ranges}. Continuing without those pages and using the {claims_found} extracted claims already available."
        ),
        "mode": "deepagents_partial_parse",
        "missing_batches": missing_page_ranges,
        "claims_found": claims_found,
    })


def _tracer_batch_message(claim_batch_file: Path, available_files: str) -> dict[str, Any]:
    batch_name = claim_batch_file.stem.replace("page_", "evidence_")
    return {
        "messages": [{
            "role": "user",
            "content": (
                f"Process only the claim batch file '{claim_batch_file.name}'. "
                f"Read it with read_claim_file('{claim_batch_file.name}'). "
                f"Only use source files that exist in the active input bundle: {available_files}. "
                "Trace every claim in that file using the available Excel, CSV, and PDF tools. "
                "If a guessed filename does not exist, discard it and continue with the listed files only. "
                "The output objects must use the exact schema keys 'flag' and 'explanation'; never use 'validation' or 'note'. "
                f"When finished, call write_evidence exactly once with batch_name='{batch_name}' and the combined JSON array for this batch only. "
                f"Do not write any intermediate or scratch JSON files. The only allowed batch_name for this task is '{batch_name}'. "
                "Return a short summary after saving the evidence."
            ),
        }],
    }


def _filter_tracer_batch_output(claim_batch_file: Path) -> tuple[int, int]:
    evidence_path = _evidence_batch_path(claim_batch_file)
    if not claim_batch_file.exists() or not evidence_path.exists():
        return 0, 0

    try:
        claims = json.loads(claim_batch_file.read_text(encoding="utf-8"))
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0, 0

    if not isinstance(claims, list) or not isinstance(evidence, list):
        return 0, 0

    allowed_claim_ids = {
        claim.get("claim_id")
        for claim in claims
        if isinstance(claim, dict) and claim.get("claim_id")
    }
    if not allowed_claim_ids:
        return 0, 0

    filtered = [
        item for item in evidence
        if not isinstance(item, dict)
        or not item.get("claim_id")
        or item.get("claim_id") in allowed_claim_ids
    ]
    dropped = len(evidence) - len(filtered)
    if dropped:
        evidence_path.write_text(json.dumps(filtered, indent=2, ensure_ascii=False), encoding="utf-8")
    return dropped, len(filtered)


async def _trace_all(tracer_agent: Any, claim_batch_files: list[Path], sem: asyncio.Semaphore, progress_callback=None) -> list[Any]:
    from pipeline import _emit

    available_files = ", ".join(path.name for path in sorted(INPUT_DIR.glob("*")) if path.is_file())

    async def run_one(claim_batch_file: Path) -> Any:
        async with sem:
            _emit(progress_callback, "agent_progress", {
                "agent": "Tracer",
                "message": f"Tracing claim batch {claim_batch_file.name}",
            })
            result = await _invoke_agent_async(
                tracer_agent,
                _tracer_batch_message(claim_batch_file, available_files),
            )
            dropped, kept = _filter_tracer_batch_output(claim_batch_file)
            if dropped:
                _emit(progress_callback, "agent_progress", {
                    "agent": "Tracer",
                    "message": (
                        f"Filtered {dropped} extra finding(s) from {claim_batch_file.name}; kept {kept} matched evidence rows"
                    ),
                })
            return result

    return await asyncio.gather(*(run_one(claim_batch_file) for claim_batch_file in claim_batch_files), return_exceptions=True)


def _detect_cross_batch_ambiguity(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        data_point = finding.get("data_point")
        if isinstance(data_point, str) and data_point:
            groups[data_point].append(finding)

    for data_point, group in groups.items():
        if len(group) < 2:
            continue

        values = {
            round(float(finding["claimed_value"]), 4)
            for finding in group
            if isinstance(finding.get("claimed_value"), (int, float))
        }
        if len(values) <= 1:
            continue

        page_value_pairs = sorted({
            (finding.get("page"), finding.get("claimed_value"))
            for finding in group
            if finding.get("claimed_value") is not None
        })
        explanation = (
            f"ambiguous_disclosure: PDF reports multiple values for {data_point} "
            f"({', '.join(f'{value} on p.{page}' for page, value in page_value_pairs)}) - "
            "different scopes, requires human review"
        )
        for finding in group:
            finding["flag"] = "yellow"
            finding["explanation"] = explanation

    return findings


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


def _run_or_await(coro: Any) -> Any:
    """Run a coroutine, adapting to whether we're inside a running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — use asyncio.run()
        return asyncio.run(coro)
    else:
        # Running loop — use run_coroutine_threadsafe in a sync context
        # or just return the coroutine for the caller to await.
        # Since _run_deepagents_demo_audit is called from a sync context
        # inside uvicorn's thread, we use asyncio.run_coroutine_threadsafe
        # when there's already a running loop.
        import concurrent.futures
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=600)


async def _run_deepagents_demo_audit_async(progress_callback=None, pdf_filename: str = "atlas_sustainability_statement.pdf") -> dict:
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

    # ── Parse phase ──────────────────────────────────────────────────────
    parser_agent = create_parser_subagent(timeout_seconds=PARSER_TIMEOUT_SECONDS)
    _emit(progress_callback, "phase", {
        "phase": "parse_claims",
        "message": "Parser subagents extracting claims in page batches...",
    })
    _emit(progress_callback, "agent_start", {
        "agent": "Orchestrator",
        "task": f"Dispatching {len(page_ranges)} parser batches",
    })

    parser_results = await _parse_all_batches(parser_agent, pdf_path, page_ranges, progress_callback)
    parser_errors = [result for result in parser_results if isinstance(result, Exception)]
    if parser_errors:
        _emit(progress_callback, "status", {
            "message": (
                f"Parser initial pass completed with {len(parser_errors)} batch exception(s). "
                "Checking which claim files were saved and proceeding with retry if needed."
            ),
            "mode": "deepagents_parser_partial",
        })

    # ── Check which batches saved successfully ───────────────────────────
    missing_page_ranges = [page_range for page_range in page_ranges if not _claim_batch_path(page_range).is_file()]
    if missing_page_ranges:
        _emit(progress_callback, "status", {
            "message": (
                "Parser batches missing after initial pass: "
                f"{', '.join(missing_page_ranges)}. Retrying with an extended timeout before continuing."
            ),
            "mode": "deepagents_parser_retry",
            "missing_batches": missing_page_ranges,
        })
        retry_parser_agent = create_parser_subagent(timeout_seconds=PARSER_RETRY_TIMEOUT_SECONDS)
        retry_results = await _retry_missing_parser_batches(retry_parser_agent, pdf_path, missing_page_ranges, progress_callback)
        retry_errors = [result for result in retry_results if isinstance(result, Exception)]
        if retry_errors:
            _emit(progress_callback, "status", {
                "message": (
                    f"Parser retry completed with {len(retry_errors)} exception(s) for batches: "
                    f"{', '.join(missing_page_ranges)}. Continuing with available claim data."
                ),
                "mode": "deepagents_parser_retry_partial",
            })

    # ── Final check: what do we have? ────────────────────────────────────
    missing_page_ranges = [page_range for page_range in page_ranges if not _claim_batch_path(page_range).is_file()]
    claims = _read_json_batches(CLAIMS_DIR)
    if not claims:
        raise RuntimeError("Deepagents parser produced no claims — cannot continue")

    if missing_page_ranges:
        _emit_missing_batch_status(progress_callback, missing_page_ranges, len(claims))

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

    # ── Trace phase ──────────────────────────────────────────────────────
    tracer_agent = create_tracer_subagent()
    claim_batch_files = _claim_batch_files()
    _emit(progress_callback, "phase", {
        "phase": "trace_sources",
        "message": "Tracer subagent resolving claims to source evidence...",
    })
    _emit(progress_callback, "agent_start", {
        "agent": "Tracer",
        "task": f"Tracing {len(claims)} extracted claims across {len(claim_batch_files)} claim batches",
    })

    tracer_results = await _trace_all(
        tracer_agent,
        claim_batch_files,
        asyncio.Semaphore(TRACER_CONCURRENCY),
        progress_callback,
    )
    tracer_errors = [result for result in tracer_results if isinstance(result, Exception)]
    if tracer_errors:
        _emit(progress_callback, "status", {
            "message": (
                f"Tracer completed with {len(tracer_errors)} batch exception(s). "
                "Continuing with available evidence."
            ),
            "mode": "deepagents_tracer_partial",
        })

    findings = _read_json_batches(EVIDENCE_DIR, pattern="evidence_*.json")
    if not findings:
        raise RuntimeError("Deepagents tracer produced no evidence — cannot build report")
    findings = _detect_cross_batch_ambiguity(findings)

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
        "pipeline": report["audit_metadata"]["pipeline"],
        "parser_mode": report["audit_metadata"]["parser_mode"],
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
    from pipeline import _emit, run_full_audit, run_generic_audit

    pipeline_mode = get_pipeline_mode()
    if pipeline_mode == "generic":
        _emit(progress_callback, "status", {
            "message": "Generic pipeline mode forced. Running generic_v1 pipeline.",
            "mode": "live_generic",
            "pipeline": "generic_v1",
        })
        return run_generic_audit(
            pdf_filename=pdf_filename,
            progress_callback=progress_callback,
        )

    if pipeline_mode == "legacy":
        _emit(progress_callback, "status", {
            "message": "Legacy pipeline mode forced. Running deterministic pipeline.",
            "mode": "live_deterministic",
            "pipeline": "deterministic",
        })
        return run_full_audit(
            pdf_filename=pdf_filename,
            progress_callback=progress_callback,
        )

    try:
        return _run_or_await(_run_deepagents_demo_audit_async(
            progress_callback=progress_callback,
            pdf_filename=pdf_filename,
        ))
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