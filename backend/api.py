"""FastAPI server — Atlas CSRD Audit Intelligence.

Two modes:
  MOCK_MODE=true  → instant simulated audit with dramatic SSE stream (for demos)
  MOCK_MODE=false → live deterministic pipeline (for real audits)
"""

import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import AsyncGenerator

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────

_ws = os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace"))
os.environ["WORKSPACE_DIR"] = _ws
WORKSPACE = Path(_ws)
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"
REPORT_PATH = WORKSPACE / "audit_report.json"
INPUT_DIR = WORKSPACE / "input"

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() in ("1", "true", "yes")

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


def _run_live_audit(progress_callback=None) -> tuple[str, dict]:
    """Run the live audit with LLM assistance when available."""
    from orchestrator import is_llm_available, run_live_llm_audit
    from pipeline import run_full_audit

    if is_llm_available():
        logger.info("Live audit requested: selecting LLM-assisted pipeline")
        if progress_callback is not None:
            progress_callback(
                "status",
                {
                    "message": "Atlas CSRD Audit Engine initializing live LLM pipeline...",
                    "mode": "live_llm",
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
        findings = MOCK_EVIDENCE
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
            "evidence": sorted(findings, key=lambda x: x.get("page", 0)),
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
        summary = _compute_summary(MOCK_EVIDENCE)
        return JSONResponse(
            {
                "mode": "mock",
                "evidence": sorted(MOCK_EVIDENCE, key=lambda x: x.get("page", 0)),
                "summary": summary,
                "review_required": summary.get("review_required", False),
                "red_flags": summary.get("red_flags", []),
            }
        )

    try:
        logger.info("POST /audit in live mode")
        mode, report = _run_live_audit()
        return JSONResponse(
            {
                "mode": mode,
                "evidence": sorted(
                    report.get("findings", []), key=lambda x: x.get("page", 0)
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
    """Cinematic SSE stream for live demos — uses the fixed event taxonomy."""
    yield _sse_event(
        "status", {"message": "Atlas CSRD Audit Engine initializing...", "mode": "mock"}
    )
    await asyncio.sleep(0.3)

    # Phase: catalog_inputs
    yield _sse_event(
        "phase", {"phase": "catalog_inputs", "message": "Cataloging input documents..."}
    )
    await asyncio.sleep(0.3)
    input_files = [
        {"name": "atlas_sustainability_statement.pdf", "size_kb": 35.7, "type": ".pdf"},
        {"name": "energia_2024.xlsx", "size_kb": 5.7, "type": ".xlsx"},
        {"name": "energia_szamla_Q4.pdf", "size_kb": 3.5, "type": ".pdf"},
        {"name": "hr_export_2024.csv", "size_kb": 47.7, "type": ".csv"},
        {"name": "scope3_szallito.xlsx", "size_kb": 5.1, "type": ".xlsx"},
    ]
    yield _sse_event(
        "phase",
        {
            "phase": "catalog_inputs",
            "message": f"Found {len(input_files)} input files",
            "files": input_files,
        },
    )
    await asyncio.sleep(0.3)

    # Phase: build_audit_plan
    yield _sse_event(
        "phase",
        {
            "phase": "build_audit_plan",
            "message": "Building audit plan for ESRS E1 — Climate Change",
        },
    )
    todos = [
        "Analyze PDF structure (ESRS E1 claims)",
        "Extract all numerical claims from sustainability statement",
        "Trace scope1_emission → energia_2024.xlsx (Scope1_Scope2 / Scope1_tonna)",
        "Trace scope2_emission → energia_2024.xlsx (Scope1_Scope2 / Scope2_tonna)",
        "Trace scope1_scope2_total → energia_2024.xlsx (Scope1_Scope2) — computed field",
        "Trace renewable_pct → energia_2024.xlsx (Megujulo / Arany)",
        "Trace headcount → hr_export_2024.csv (CSV row count)",
        "Trace scope3_emission → scope3_szallito.xlsx (Scope3 / Kibocsatas (tonna))",
        "Trace training_participants — NO SOURCE (manual verification needed)",
        "Trace production_sites — NO SOURCE (manual verification needed)",
        "Run deterministic validation on all claims",
        "Generate audit evidence package (audit_report.json)",
    ]
    yield _sse_event("todo", {"items": todos, "total": len(todos)})
    await asyncio.sleep(0.3)
    yield _sse_event(
        "phase",
        {
            "phase": "build_audit_plan",
            "message": "Audit plan ready — 8 claim patterns, 8 data points with source mappings",
        },
    )
    await asyncio.sleep(0.3)

    # Phase: parse_claims (Parser agent)
    yield _sse_event(
        "phase",
        {
            "phase": "parse_claims",
            "message": "Parser analyzing sustainability statement...",
        },
    )
    yield _sse_event(
        "agent_start",
        {
            "agent": "Parser",
            "task": "Extracting ESRS E1 claims from atlas_sustainability_statement.pdf",
        },
    )
    await asyncio.sleep(0.3)
    claim_progress = [
        ("production_sites", 3, "db", 4),
        ("scope1_emission", 1850, "tCO2e", 6),
        ("scope2_emission", 4200, "tCO2e", 7),
        ("scope1_scope2_total", 6050, "tCO2e", 7),
        ("scope3_emission", 18400, "tCO2e", 8),
        ("renewable_pct", 67, "%", 9),
        ("headcount", 2340, "fő", 10),
        ("training_participants", 1240, "fő", 11),
    ]
    for i, (dp, val, unit, page) in enumerate(claim_progress):
        yield _sse_event(
            "agent_progress",
            {
                "agent": "Parser",
                "data_point": dp,
                "claimed_value": val,
                "unit": unit,
                "page": page,
                "progress": f"{i + 1}/{len(claim_progress)}",
            },
        )
        await asyncio.sleep(0.15)
    yield _sse_event("agent_done", {"agent": "Parser", "claims_found": 8})
    yield _sse_event(
        "phase",
        {"phase": "parse_claims", "message": "Parsing complete — 8 claims extracted"},
    )
    await asyncio.sleep(0.3)

    # Phase: trace_sources (Tracer agent)
    yield _sse_event(
        "phase",
        {"phase": "trace_sources", "message": "Tracer resolving source documents..."},
    )
    yield _sse_event(
        "agent_start",
        {"agent": "Tracer", "task": "Tracing 8 claims to source documents"},
    )
    await asyncio.sleep(0.3)
    tracer_items = [
        ("production_sites", None, "grey"),
        ("scope1_emission", "energia_2024.xlsx / Scope1_Scope2 / B5", "green"),
        ("scope2_emission", "energia_2024.xlsx / Scope1_Scope2 / C5", "red"),
        ("scope1_scope2_total", "energia_2024.xlsx / Scope1_Scope2 / computed", "red"),
        ("scope3_emission", "scope3_szallito.xlsx / Scope3 / C6", "green"),
        ("renewable_pct", "energia_2024.xlsx / Megujulo / D2", "green"),
        ("headcount", "hr_export_2024.csv", "yellow"),
        ("training_participants", None, "grey"),
    ]
    for i, (dp, source, flag) in enumerate(tracer_items):
        yield _sse_event(
            "agent_progress",
            {
                "agent": "Tracer",
                "data_point": dp,
                "claimed_value": next(c[1] for c in claim_progress if c[0] == dp),
                "progress": f"{i + 1}/{len(tracer_items)}",
            },
        )
        await asyncio.sleep(0.15)
        if flag == "red":
            dev = 10.53 if dp == "scope2_emission" else 7.08
            yield _sse_event(
                "finding",
                {
                    "agent": "Tracer",
                    "data_point": dp,
                    "flag": "red",
                    "claimed_value": 4200 if dp == "scope2_emission" else 6050,
                    "source_value": 3800 if dp == "scope2_emission" else 5650,
                    "deviation_pct": dev,
                    "message": f"DISCREPANCY — {dev}% deviation",
                },
            )
            await asyncio.sleep(0.3)
    yield _sse_event(
        "agent_done",
        {"agent": "Tracer", "findings": 8, "sources_resolved": 6},
    )
    yield _sse_event(
        "phase", {"phase": "trace_sources", "message": "Trace complete — 8 findings"}
    )
    await asyncio.sleep(0.3)

    # Phase: validate_findings (Validator agent)
    yield _sse_event(
        "phase",
        {
            "phase": "validate_findings",
            "message": "Validator running deterministic checks...",
        },
    )
    yield _sse_event(
        "agent_start",
        {
            "agent": "Validator",
            "task": "Running deterministic validation on all findings",
        },
    )
    await asyncio.sleep(0.2)
    yield _sse_event(
        "agent_progress",
        {"agent": "Validator", "green": 3, "yellow": 1, "red": 2, "grey": 2},
    )
    await asyncio.sleep(0.2)
    yield _sse_event(
        "agent_done",
        {
            "agent": "Validator",
            "message": "Validation complete — 3 green, 1 yellow, 2 red, 2 grey",
        },
    )
    yield _sse_event(
        "phase",
        {
            "phase": "validate_findings",
            "message": "Validation complete — 2 material misstatements",
        },
    )
    await asyncio.sleep(0.3)

    # Phase: build_report (Reporter agent)
    yield _sse_event(
        "phase",
        {"phase": "build_report", "message": "Reporter assembling evidence package..."},
    )
    yield _sse_event(
        "agent_start",
        {"agent": "Reporter", "task": "Building audit report and evidence package"},
    )
    await asyncio.sleep(0.2)
    yield _sse_event(
        "agent_done",
        {"agent": "Reporter", "message": "Evidence package saved to audit_report.json"},
    )
    yield _sse_event(
        "phase",
        {
            "phase": "build_report",
            "message": "Report complete — evidence package ready",
        },
    )
    await asyncio.sleep(0.3)

    # Complete — same structure as live stream
    summary = _compute_summary(MOCK_EVIDENCE)
    yield _sse_event(
        "complete",
        {
            "summary": summary,
            "total_findings": 8,
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
