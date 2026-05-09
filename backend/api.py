"""FastAPI server — Atlas CSRD Audit Intelligence.

Two modes:
  MOCK_MODE=true  → instant simulated audit with dramatic SSE stream (for demos)
  MOCK_MODE=false → live deterministic pipeline (for real audits)
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, AsyncGenerator

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

from input_bundle import get_input_dir, get_statement_filename, load_audit_manifest

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────

_ws = os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace"))
os.environ["WORKSPACE_DIR"] = _ws
WORKSPACE = Path(_ws)
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"
REPORT_PATH = WORKSPACE / "audit_report.json"
INPUT_DIR = get_input_dir(WORKSPACE)

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() in ("1", "true", "yes")
MOCK_SSE_DELAY_SECONDS = max(0.05, float(os.environ.get("MOCK_SSE_DELAY_SECONDS", "0.75")))

logging.basicConfig(
    level=os.environ.get("ATLAS_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("atlas.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown logging."""
    mode = "🎭 MOCK (demo)" if MOCK_MODE else "⚡ LIVE (deterministic pipeline)"
    files = list(INPUT_DIR.glob("*")) if INPUT_DIR.exists() else []
    print(f"\n{'=' * 60}")
    print(f"  Atlas CSRD Audit Intelligence — API Server")
    print(f"  Mode: {mode}")
    print(f"  Input files: {len(files)}")
    for f in sorted(files):
        print(f"    📄 {f.name} ({f.stat().st_size / 1024:.1f} KB)")
    print(f"  Endpoints:")
    print(f"    GET  /         — Dashboard UI")
    print(f"    GET  /health   — System status")
    print(f"    POST /audit    — Run audit")
    print(f"    GET  /stream   — Real-time SSE stream")
    print(f"    GET  /evidence — Audit findings")
    print(f"    GET  /report   — Full report JSON")
    print(f"    POST /reset    — Clear workspace")
    print(f"{'=' * 60}\n")
    yield


app = FastAPI(
    title="Atlas CSRD Audit Intelligence",
    description="AI-powered CSRD sustainability statement audit — ESRS E1",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mock evidence (demo data with dramatic red flags) ──────────────────

MOCK_EVIDENCE = [
    {
        "page": 4,
        "flag": "grey",
        "claim_text": "The company conducts production activities at 3 sites.",
        "data_point": "production_sites",
        "claimed_value": 3,
        "source_value": None,
        "unit": "sites",
        "source_file": None,
        "source_sheet": None,
        "source_cell": None,
        "deviation_pct": None,
        "explanation": "Missing evidence: No source document configured for production_sites. Manual verification required — auditor must locate supporting documentation.",
        "review_required": True,
    },
    {
        "page": 6,
        "flag": "green",
        "claim_text": "The company's Scope 1 emissions for 2024 were 1,850 tonnes CO2 equivalent.",
        "data_point": "scope1_emission",
        "claimed_value": 1850,
        "source_value": 1850,
        "unit": "tCO2e",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2",
        "source_cell": "B5",
        "deviation_pct": 0.0,
        "explanation": "Claimed: 1850 tCO2e, Source: 1850 tCO2e, Deviation: 0.0%",
        "review_required": False,
    },
    {
        "page": 7,
        "flag": "red",
        "claim_text": "The company's Scope 2 emissions for 2024 were 4,200 tonnes CO2 equivalent.",
        "data_point": "scope2_emission",
        "claimed_value": 4200,
        "source_value": 3800,
        "unit": "tCO2e",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2",
        "source_cell": "C5",
        "deviation_pct": 10.53,
        "explanation": "Claimed: 4200 tCO2e, Source: 3800 tCO2e, Deviation: 10.53% — MATERIAL MISSTATEMENT",
        "review_required": True,
    },
    {
        "page": 7,
        "flag": "red",
        "claim_text": "The total Scope 1 and Scope 2 emissions amount to 6,050 tonnes CO2 equivalent.",
        "data_point": "scope1_scope2_total",
        "claimed_value": 6050,
        "source_value": 5650.0,
        "unit": "tCO2e",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2",
        "source_cell": "B5+C5",
        "deviation_pct": 7.08,
        "explanation": "Claimed: 6050 tCO2e, Source: 5650.0 tCO2e, Deviation: 7.08% — ARITHMETIC INCONSISTENCY",
        "review_required": True,
    },
    {
        "page": 8,
        "flag": "green",
        "claim_text": "The estimated Scope 3 emissions were 18,400 tonnes CO2 equivalent.",
        "data_point": "scope3_emission",
        "claimed_value": 18400,
        "source_value": 18400,
        "unit": "tCO2e",
        "source_file": "scope3_szallito.xlsx",
        "source_sheet": "Scope3",
        "source_cell": "C6",
        "deviation_pct": 0.0,
        "explanation": "Claimed: 18400 tCO2e, Source: 18400 tCO2e, Deviation: 0.0%",
        "review_required": False,
    },
    {
        "page": 9,
        "flag": "green",
        "claim_text": "The share of renewable energy in total energy consumption was 67%.",
        "data_point": "renewable_pct",
        "claimed_value": 67,
        "source_value": 67,
        "unit": "%",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Megujulo",
        "source_cell": "D2",
        "deviation_pct": 0.0,
        "explanation": "Claimed: 67 %, Source: 67 %, Deviation: 0.0%",
        "review_required": False,
    },
    {
        "page": 10,
        "flag": "yellow",
        "claim_text": "The total headcount as of December 31, 2024 was 2,340 employees.",
        "data_point": "headcount",
        "claimed_value": 2340,
        "source_value": 2290,
        "unit": "employees",
        "source_file": "hr_export_2024.csv",
        "source_sheet": "Sheet1",
        "source_cell": "aktív rows",
        "deviation_pct": 2.18,
        "explanation": "Claimed: 2340 fő, Source: 2290 fő, Deviation: 2.18% — Minor headcount discrepancy, likely data entry timing issue.",
        "review_required": False,
    },
    {
        "page": 11,
        "flag": "grey",
        "claim_text": "The number of participants in training programs was 1,240 employees.",
        "data_point": "training_participants",
        "claimed_value": 1240,
        "source_value": None,
        "unit": "employees",
        "source_file": None,
        "source_sheet": None,
        "source_cell": None,
        "deviation_pct": None,
        "explanation": "Missing evidence: No source document configured for training_participants. Manual verification required — auditor must locate supporting documentation.",
        "review_required": True,
    },
]


# ── Helpers ────────────────────────────────────────────────────────────


def _compute_summary(findings: list) -> dict:
    """Compute summary counts and flags — matches pipeline.py _compute_summary."""
    green = sum(1 for f in findings if f.get("flag") == "green")
    yellow = sum(1 for f in findings if f.get("flag") == "yellow")
    red = sum(1 for f in findings if f.get("flag") == "red")
    grey = sum(1 for f in findings if f.get("flag") not in ("green", "yellow", "red"))

    red_flags = [
        {
            "data_point": f["data_point"],
            "claimed": f.get("claimed_value"),
            "actual": f.get("source_value"),
            "deviation_pct": f.get("deviation_pct"),
            "explanation": f.get("explanation", ""),
        }
        for f in findings
        if f.get("flag") == "red"
    ]

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
        "verdict": (
            "PASS" if not has_red else f"FAIL — {red} material misstatement(s) detected"
        ),
        "materiality_note": (
            f"{red} material error(s) found. Auditor must investigate flagged items before signing off."
            if has_red
            else "No material misstatements. Report is consistent with source data."
        ),
    }


def _load_report_file() -> dict[str, Any] | None:
    if not REPORT_PATH.exists():
        return None

    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None

    return payload if isinstance(payload, dict) else None


def _parse_mock_page(description: str, default_page: int) -> int:
    match = re.search(r"p\.(\d+)", description, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return default_page


def _severity_to_flag(severity: str) -> str:
    normalized = (severity or "").strip().upper()
    return {
        "RED": "red",
        "YELLOW": "yellow",
        "MISSING": "grey",
        "GREEN": "green",
    }.get(normalized, "grey")


def _compute_deviation_pct(claimed_value: float | int | None, source_value: float | int | None) -> float | None:
    if not isinstance(claimed_value, (int, float)) or not isinstance(source_value, (int, float)):
        return None
    if claimed_value == 0:
        return None
    return round(abs(claimed_value - source_value) / abs(claimed_value) * 100, 1)


def _legacy_mock_findings() -> list[dict[str, Any]]:
    return sorted(MOCK_EVIDENCE, key=_finding_page_sort_key)


def _manifest_mock_findings(manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not manifest:
        return []

    expected = manifest.get("expected_findings")
    flags = expected.get("flags") if isinstance(expected, dict) else None
    if not isinstance(flags, list):
        return []

    overrides: dict[int, dict[str, Any]] = {
        1: {
            "data_point": "scope2_market_based_total",
            "claim_text": "Scope 2 market-based total reported in the sustainability statement",
            "claimed_value": 47.0,
            "source_value": 44.8,
            "unit": "ktCO2e",
            "source_file": "GHG_calculation_workbook.xlsx",
            "source_sheet": "Scope2_electricity",
            "source_cell": "market-based total",
            "page": 34,
        },
        2: {
            "data_point": "scope12_market_based_total",
            "claim_text": "Total Scope 1+2 market-based emissions reported in the sustainability statement",
            "claimed_value": 359.0,
            "source_value": 335.0,
            "unit": "ktCO2e",
            "source_file": "GHG_calculation_workbook.xlsx",
            "source_sheet": "Reconciliation_summary",
            "source_cell": "market-based total",
            "page": 33,
        },
        3: {
            "data_point": "eu_taxonomy_revenue_alignment_scope_mismatch",
            "claim_text": "EU Taxonomy revenue alignment is disclosed with two different scope bases",
            "claimed_value": 52.0,
            "source_value": 29.3,
            "unit": "%",
            "source_file": "siemens_E1_excerpt.pdf",
            "source_sheet": None,
            "source_cell": "p.19",
            "deviation_pct": None,
            "page": 19,
        },
        4: {
            "data_point": "scope3_category7_employee_commuting",
            "claim_text": "Employee commuting emissions reported in the PDF require support from the workbook",
            "claimed_value": 177.0,
            "source_value": None,
            "unit": "ktCO2e",
            "source_file": "GHG_calculation_workbook.xlsx",
            "source_sheet": "Scope3_categories",
            "source_cell": "row 3.7",
            "page": 33,
        },
        5: {
            "data_point": "carbon_credits_certificate_url",
            "claim_text": "Cancelled carbon credits require independently verifiable certificate URLs",
            "claimed_value": None,
            "source_value": None,
            "unit": "supporting document",
            "source_file": "carbon_credits_register.xlsx",
            "source_sheet": "Plan Vivo rows",
            "source_cell": "certificate_url",
            "page": 34,
        },
    }

    findings: list[dict[str, Any]] = []
    for raw_flag in flags:
        if not isinstance(raw_flag, dict):
            continue

        finding_id = int(raw_flag.get("id", len(findings) + 1))
        description = str(raw_flag.get("description", "")).strip()
        override = overrides.get(finding_id, {})
        claimed_value = override.get("claimed_value")
        source_value = override.get("source_value")
        flag = _severity_to_flag(str(raw_flag.get("severity", "MISSING")))

        findings.append(
            {
                "claim_id": f"mock_flag_{finding_id}",
                "page": override.get("page", _parse_mock_page(description, finding_id)),
                "flag": flag,
                "claim_text": override.get("claim_text", description),
                "data_point": override.get("data_point", f"mock_finding_{finding_id}"),
                "claimed_value": claimed_value,
                "source_value": source_value,
                "unit": override.get("unit", ""),
                "source_file": override.get("source_file"),
                "source_sheet": override.get("source_sheet"),
                "source_cell": override.get("source_cell"),
                "deviation_pct": override.get(
                    "deviation_pct",
                    _compute_deviation_pct(claimed_value, source_value),
                ),
                "explanation": description,
                "review_required": flag != "green",
            }
        )

    return sorted(findings, key=_finding_page_sort_key)


def _mock_document_inventory(manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    manifest_roles: dict[str, str] = {}
    if manifest:
        statement = manifest.get("statement_document")
        if isinstance(statement, dict):
            statement_path = str(statement.get("path", "")).strip()
            if statement_path:
                manifest_roles[Path(statement_path).name] = str(statement.get("type", "sustainability_statement"))

        evidence_files = manifest.get("evidence_files")
        if isinstance(evidence_files, list):
            for item in evidence_files:
                if not isinstance(item, dict):
                    continue
                evidence_path = str(item.get("path", "")).strip()
                if evidence_path:
                    manifest_roles[Path(evidence_path).name] = str(item.get("type", "supporting_document"))

    return [
        {
            "filename": path.name,
            "type": path.suffix,
            "size_kb": round(path.stat().st_size / 1024, 1),
            "role": manifest_roles.get(path.name, "input_document"),
        }
        for path in sorted(INPUT_DIR.glob("*"))
        if path.is_file()
    ]


def _build_mock_report() -> dict[str, Any]:
    manifest = load_audit_manifest(WORKSPACE)
    findings = _manifest_mock_findings(manifest) or _legacy_mock_findings()
    summary = _compute_summary(findings)
    now = datetime.now(timezone.utc).isoformat()
    statement_filename = get_statement_filename(
        default_filename="atlas_sustainability_statement.pdf",
        workspace_dir=WORKSPACE,
    ) or "atlas_sustainability_statement.pdf"

    return {
        "audit_metadata": {
            "document": statement_filename,
            "standard": "ESRS E1 — Climate Change",
            "framework": "EU CSRD",
            "pipeline": "mock",
            "parser_mode": "scripted-manifest",
            "started_at": now,
            "completed_at": now,
            "total_pages": max((_finding_page_sort_key(item) for item in findings), default=0),
            "total_claims_found": len(findings),
            "total_findings": len(findings),
            "audit_id": manifest.get("audit_id") if isinstance(manifest, dict) else None,
            "client_name": manifest.get("client_name") if isinstance(manifest, dict) else None,
            "fiscal_year": manifest.get("fiscal_year") if isinstance(manifest, dict) else None,
        },
        "document_inventory": _mock_document_inventory(manifest),
        "findings": findings,
        "summary": summary,
        "red_flags": summary.get("red_flags", []),
        "review_required": summary.get("review_required", False),
    }


def _write_mock_outputs(report: dict[str, Any]) -> dict[str, Any]:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (EVIDENCE_DIR / "all_evidence.json").write_text(
        json.dumps(report.get("findings", []), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


async def _mock_pause(request: Request, multiplier: float = 1.0) -> bool:
    if await request.is_disconnected():
        return False
    await asyncio.sleep(MOCK_SSE_DELAY_SECONDS * multiplier)
    return not await request.is_disconnected()


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _collect_evidence_files() -> list:
    findings = []
    for ef in sorted(EVIDENCE_DIR.glob("*.json")):
        try:
            data = json.loads(ef.read_text(encoding="utf-8"))
            if isinstance(data, list):
                findings.extend(data)
            elif isinstance(data, dict):
                findings.append(data)
        except (json.JSONDecodeError, IOError):
            continue
    return findings


def _finding_page_sort_key(finding: dict) -> int:
    page = finding.get("page")
    return page if isinstance(page, int) else 0


def _run_live_audit(progress_callback=None) -> tuple[str, dict]:
    """Run the live audit with LLM assistance when available."""
    from orchestrator import get_pipeline_mode, is_llm_available, run_live_llm_audit
    from pipeline import run_full_audit, run_generic_audit

    pipeline_mode = get_pipeline_mode()

    if pipeline_mode == "generic":
        logger.info("Live audit requested: forcing generic_v1 pipeline")
        if progress_callback is not None:
            progress_callback(
                "status",
                {
                    "message": "Atlas CSRD Audit Engine initializing generic_v1 pipeline...",
                    "mode": "live_generic",
                    "pipeline": "generic_v1",
                },
            )
        return "live_generic", run_generic_audit(progress_callback=progress_callback)

    if pipeline_mode == "legacy":
        logger.info("Live audit requested: forcing deterministic legacy pipeline")
        if progress_callback is not None:
            progress_callback(
                "status",
                {
                    "message": "Atlas CSRD Audit Engine initializing deterministic pipeline...",
                    "mode": "live_deterministic",
                    "pipeline": "deterministic",
                },
            )
        return "live_deterministic", run_full_audit(progress_callback=progress_callback)

    if pipeline_mode == "deepagents":
        if is_llm_available():
            logger.info("Live audit requested: forcing deepagents pipeline")
            if progress_callback is not None:
                progress_callback(
                    "status",
                    {
                        "message": "Atlas CSRD Audit Engine initializing deepagents pipeline...",
                        "mode": "live_llm",
                        "pipeline": "deepagents-supervised",
                    },
                )
            return "live_llm", run_live_llm_audit(progress_callback=progress_callback)

        logger.warning(
            "Deepagents mode requested without LLM availability: falling back to deterministic pipeline"
        )
        if progress_callback is not None:
            progress_callback(
                "status",
                {
                    "message": "Deepagents mode requested but DeepSeek is unavailable. Running deterministic pipeline.",
                    "mode": "live_deterministic",
                    "pipeline": "deterministic",
                },
            )
        return "live_deterministic", run_full_audit(progress_callback=progress_callback)

    if is_llm_available():
        logger.info("Live audit requested: selecting LLM-assisted pipeline")
        if progress_callback is not None:
            progress_callback(
                "status",
                {
                    "message": "Atlas CSRD Audit Engine initializing live LLM pipeline...",
                    "mode": "live_llm",
                    "pipeline": "deepagents-supervised",
                },
            )
        return "live_llm", run_live_llm_audit(progress_callback=progress_callback)

    logger.warning(
        "Live audit requested without LLM availability: falling back to deterministic pipeline"
    )
    if progress_callback is not None:
        progress_callback(
            "status",
            {
                "message": "DeepSeek is unavailable. Running deterministic live pipeline.",
                "mode": "live_deterministic",
                "pipeline": "deterministic",
            },
        )
    return "live_deterministic", run_full_audit(progress_callback=progress_callback)


def _sanitize_filename(filename: str) -> str:
    cleaned = Path(filename or "").name
    if not cleaned:
        raise HTTPException(status_code=400, detail="Filename is required.")
    return cleaned


def _clear_input_dir() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing in INPUT_DIR.iterdir():
        if existing.is_file():
            try:
                existing.unlink()
            except PermissionError:
                logger.warning(
                    f"Could not delete {existing.name} (in use by another process), skipping."
                )


async def _save_upload(upload: UploadFile) -> dict:
    filename = _sanitize_filename(upload.filename or "")
    destination = INPUT_DIR / filename

    try:
        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
    finally:
        await upload.close()
    return {
        "filename": filename,
        "size_kb": round(destination.stat().st_size / 1024, 1),
    }


# ── Endpoints ──────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path(__file__).parent / "ui.html"
    if ui_path.exists():
        return HTMLResponse(ui_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>Atlas — CSRD Audit Intelligence</h1><p>API is running. UI not found at ui.html</p>"
    )


@app.get("/health")
async def health_check():
    """System health + input file inventory."""
    if not INPUT_DIR.exists():
        return JSONResponse(
            {
                "status": "ok",
                "mode": "mock" if MOCK_MODE else "live",
                "input_files": [],
                "input_file_count": 0,
                "ready": False,
            }
        )

    files = sorted(
        [
            {"filename": f.name, "size_kb": round(f.stat().st_size / 1024, 1)}
            for f in INPUT_DIR.iterdir()
            if f.is_file()
        ],
        key=lambda x: x["filename"],
    )
    return JSONResponse(
        {
            "status": "ok",
            "mode": "mock" if MOCK_MODE else "live",
            "input_files": files,
            "input_file_count": len(files),
            "ready": len(files) >= 5,
            "endpoints": {
                "audit": "POST /audit",
                "stream": "GET /stream (SSE)",
                "evidence": "GET /evidence",
                "report": "GET /report",
                "reset": "POST /reset",
            },
        }
    )


@app.get("/evidence")
async def get_evidence():
    """Return all evidence with summary."""
    if MOCK_MODE:
        report = _load_report_file()
        findings = report.get("findings", []) if report else []
        summary = report.get("summary", _compute_summary([])) if report else _compute_summary([])
        return JSONResponse(
            {
                "evidence": sorted(findings, key=_finding_page_sort_key),
                "summary": summary,
            }
        )
    else:
        findings = _collect_evidence_files()
        if not findings and REPORT_PATH.exists():
            try:
                data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
                findings = data.get("findings", [])
            except (json.JSONDecodeError, IOError):
                pass

    return JSONResponse(
        {
            "evidence": sorted(findings, key=_finding_page_sort_key),
            "summary": _compute_summary(findings),
        }
    )


@app.post("/upload")
async def upload_inputs(files: list[UploadFile] = File(...)):
    """Replace workspace input files with the uploaded selection."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    _clear_input_dir()

    saved_files = []
    for upload in files:
        saved_files.append(await _save_upload(upload))

    return JSONResponse(
        {
            "status": "uploaded",
            "files": saved_files,
            "input_file_count": len(saved_files),
            "ready": any(
                item["filename"].lower().endswith(".pdf") for item in saved_files
            ),
        }
    )


@app.get("/report")
async def get_report():
    """Return the full audit report (evidence package)."""
    if MOCK_MODE:
        report = _load_report_file()
        if report is not None:
            return JSONResponse(report)
        return JSONResponse(
            {
                "error": "No mock audit report generated yet. Run POST /audit or start the SSE stream first."
            },
            status_code=404,
        )

    # A6 — Proper error handling and full report structure
    if REPORT_PATH.exists():
        try:
            report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            return JSONResponse(report)
        except (json.JSONDecodeError, IOError):
            return JSONResponse(
                {
                    "error": "Report file is corrupted. Run POST /reset and POST /audit to regenerate."
                },
                status_code=500,
            )
    return JSONResponse(
        {
            "error": "No audit report generated yet. Run POST /audit first to create an evidence package."
        },
        status_code=404,
    )


@app.post("/audit")
async def run_audit():
    """Trigger audit — mock (instant) or live (deterministic pipeline)."""
    if MOCK_MODE:
        logger.info("POST /audit in mock mode")
        report = _write_mock_outputs(_build_mock_report())
        return JSONResponse(
            {
                "mode": "mock",
                "pipeline": report.get("audit_metadata", {}).get("pipeline"),
                "audit_metadata": report.get("audit_metadata", {}),
                "evidence": sorted(report.get("findings", []), key=_finding_page_sort_key),
                "summary": report.get("summary", {}),
                "review_required": report.get("review_required", False),
                "red_flags": report.get("red_flags", []),
            }
        )

    try:
        logger.info("POST /audit in live mode")
        mode, report = await asyncio.to_thread(_run_live_audit)
        return JSONResponse(
            {
                "mode": mode,
                "pipeline": report.get("audit_metadata", {}).get("pipeline"),
                "audit_metadata": report.get("audit_metadata", {}),
                "evidence": sorted(
                    report.get("findings", []), key=_finding_page_sort_key
                ),
                "summary": report.get("summary", {}),
                "review_required": report.get("review_required", False),
                "red_flags": report.get("red_flags", []),
            }
        )
    except Exception as e:
        return JSONResponse(
            {
                "mode": "live",
                "pipeline": None,
                "error": str(e),
                "evidence": [],
                "summary": _compute_summary([]),
                "review_required": False,
                "red_flags": [],
            },
            status_code=500,
        )


@app.post("/reset")
async def reset_workspace():
    """Clear all audit outputs. Ready for a fresh run."""
    from pipeline import reset_workspace as do_reset

    result = do_reset()
    return JSONResponse({"status": "reset", **result})


@app.get("/stream")
async def stream_audit(request: Request):
    """SSE real-time audit event stream."""
    logger.info("GET /stream opened in %s mode", "mock" if MOCK_MODE else "live")
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if MOCK_MODE:
        return StreamingResponse(
            _mock_stream(request), media_type="text/event-stream", headers=headers
        )
    return StreamingResponse(
        _live_stream(request), media_type="text/event-stream", headers=headers
    )


# ── SSE: Mock stream (dramatic demo mode) ──────────────────────────────


async def _mock_stream(request: Request) -> AsyncGenerator[str, None]:
    """Manifest-driven SSE stream for mock mode with slow, readable demo pacing."""
    report = _build_mock_report()
    findings = report.get("findings", [])
    summary = report.get("summary", {})
    manifest = load_audit_manifest(WORKSPACE) or {}
    inventory = report.get("document_inventory", [])
    todo_items = [
        f"Reproduce expected finding {item.get('id')}: {item.get('description')}"
        for item in (manifest.get("expected_findings", {}).get("flags", []) if isinstance(manifest, dict) else [])
        if isinstance(item, dict)
    ]

    yield _sse_event(
        "status",
        {
            "message": "Atlas CSRD Audit Engine initializing mock pipeline from audit_index.json...",
            "mode": "mock",
            "pipeline": "mock",
        },
    )
    if not await _mock_pause(request, 1.1):
        return

    yield _sse_event(
        "phase",
        {"phase": "catalog_inputs", "message": "Cataloging mock input documents..."},
    )
    if not await _mock_pause(request, 0.8):
        return

    for item in inventory:
        yield _sse_event(
            "file_found",
            {"filename": item.get("filename"), "role": item.get("role")},
        )
        if not await _mock_pause(request, 0.55):
            return

    yield _sse_event(
        "phase",
        {
            "phase": "catalog_inputs",
            "message": f"Found {len(inventory)} mock input files",
            "files": inventory,
        },
    )
    if not await _mock_pause(request, 0.9):
        return

    yield _sse_event(
        "phase",
        {
            "phase": "build_audit_plan",
            "message": "Loading scripted audit plan from audit_index.json...",
        },
    )
    if todo_items:
        yield _sse_event("todo", {"items": todo_items, "total": len(todo_items)})
        if not await _mock_pause(request, 1.0):
            return

    yield _sse_event(
        "phase",
        {
            "phase": "build_audit_plan",
            "message": f"Mock plan ready — {len(findings)} expected findings scripted from the manifest",
        },
    )
    if not await _mock_pause(request, 0.9):
        return

    yield _sse_event(
        "phase",
        {
            "phase": "parse_claims",
            "message": "Parser loading scripted checks from audit_index.json...",
        },
    )
    yield _sse_event(
        "agent_start",
        {
            "agent": "Parser",
            "task": "Loading scripted expected findings from audit_index.json",
        },
    )
    if not await _mock_pause(request, 0.8):
        return

    for index, finding in enumerate(findings, start=1):
        yield _sse_event(
            "agent_progress",
            {
                "agent": "Parser",
                "message": f"Anchored mock check {index}/{len(findings)}: {finding.get('data_point')}",
            },
        )
        if not await _mock_pause(request, 0.6):
            return

    yield _sse_event(
        "agent_done",
        {
            "agent": "Parser",
            "claims_found": len(findings),
            "message": f"Loaded {len(findings)} scripted findings from audit_index.json",
        },
    )
    if not await _mock_pause(request, 0.9):
        return

    yield _sse_event(
        "phase",
        {
            "phase": "trace_sources",
            "message": "Tracer replaying expected evidence outcomes...",
        },
    )
    yield _sse_event(
        "agent_start",
        {
            "agent": "Tracer",
            "task": f"Replaying {len(findings)} expected findings from the manifest",
        },
    )
    if not await _mock_pause(request, 0.8):
        return

    for index, finding in enumerate(findings, start=1):
        source_label = finding.get("source_file") or "supporting evidence gap"
        yield _sse_event(
            "agent_progress",
            {
                "agent": "Tracer",
                "message": f"Checking {finding.get('data_point')} against {source_label} ({index}/{len(findings)})",
            },
        )
        if not await _mock_pause(request, 0.6):
            return
        yield _sse_event(
            "finding",
            {
                "agent": "Tracer",
                "data_point": finding.get("data_point"),
                "flag": finding.get("flag"),
                "claimed_value": finding.get("claimed_value"),
                "source_value": finding.get("source_value"),
                "deviation_pct": finding.get("deviation_pct"),
                "message": finding.get("explanation"),
            },
        )
        if not await _mock_pause(request, 0.95):
            return

    yield _sse_event(
        "agent_done",
        {
            "agent": "Tracer",
            "findings": len(findings),
            "sources_resolved": sum(1 for item in findings if item.get("source_file")),
            "message": f"Replayed {len(findings)} expected findings from audit_index.json",
        },
    )
    if not await _mock_pause(request, 0.8):
        return

    yield _sse_event(
        "phase",
        {
            "phase": "validate_findings",
            "message": "Validator confirming the scripted perfect mock result...",
        },
    )
    yield _sse_event(
        "agent_start",
        {
            "agent": "Validator",
            "task": "Summarizing scripted findings for the mock report",
        },
    )
    if not await _mock_pause(request, 0.55):
        return
    yield _sse_event(
        "agent_progress",
        {
            "agent": "Validator",
            "green": summary.get("green_count", 0),
            "yellow": summary.get("yellow_count", 0),
            "red": summary.get("red_count", 0),
            "grey": summary.get("grey_count", 0),
        },
    )
    if not await _mock_pause(request, 0.75):
        return
    yield _sse_event(
        "agent_done",
        {
            "agent": "Validator",
            "message": (
                f"Validation complete — {summary.get('green_count', 0)} green, "
                f"{summary.get('yellow_count', 0)} yellow, {summary.get('red_count', 0)} red, "
                f"{summary.get('grey_count', 0)} grey"
            ),
        },
    )
    if not await _mock_pause(request, 0.85):
        return

    yield _sse_event(
        "phase",
        {"phase": "build_report", "message": "Reporter assembling the perfect mock evidence package..."},
    )
    yield _sse_event(
        "agent_start",
        {"agent": "Reporter", "task": "Writing mock audit report and evidence package"},
    )
    if not await _mock_pause(request, 0.65):
        return

    _write_mock_outputs(report)

    yield _sse_event(
        "agent_done",
        {"agent": "Reporter", "message": "Mock evidence package saved to audit_report.json"},
    )
    if not await _mock_pause(request, 0.65):
        return

    yield _sse_event(
        "phase",
        {
            "phase": "build_report",
            "message": "Mock report complete — 5 expected findings reproduced from audit_index.json",
        },
    )
    if not await _mock_pause(request, 0.8):
        return

    yield _sse_event(
        "complete",
        {
            "pipeline": report["audit_metadata"]["pipeline"],
            "parser_mode": report["audit_metadata"]["parser_mode"],
            "summary": summary,
            "evidence": report.get("findings", []),
            "total_findings": len(findings),
            "review_required": summary.get("review_required", False),
        },
    )


# ── SSE: Live stream (deterministic pipeline) ──────────────────────────


async def _live_stream(request: Request) -> AsyncGenerator[str, None]:
    """Live SSE stream using the deterministic pipeline."""
    import threading
    import queue

    event_queue: queue.Queue = queue.Queue()

    def progress_callback(stage, detail):
        event_queue.put((stage, detail))

    # Run audit in background thread
    def _run():
        try:
            _run_live_audit(progress_callback=progress_callback)
        except Exception as e:
            event_queue.put(("error", {"message": str(e)}))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    # Stream events
    complete_sent = False
    while not complete_sent:
        if await request.is_disconnected():
            break

        try:
            stage, detail = event_queue.get(timeout=0.3)
        except queue.Empty:
            # Send heartbeat
            yield _sse_event("heartbeat", {"ts": time.time()})
            continue

        if stage == "complete":
            yield _sse_event("complete", detail)
            complete_sent = True
        elif stage == "error":
            yield _sse_event("error", detail)
            complete_sent = True
        else:
            yield _sse_event(stage, detail)


# ── Startup info ───────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
