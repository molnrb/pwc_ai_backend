"""FastAPI server — Atlas CSRD Audit Intelligence.

Two modes:
  MOCK_MODE=true  → instant simulated audit with dramatic SSE stream (for demos)
  MOCK_MODE=false → live deterministic pipeline (for real audits)
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncGenerator

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown logging."""
    mode = "🎭 MOCK (demo)" if MOCK_MODE else "⚡ LIVE (deterministic pipeline)"
    files = list(INPUT_DIR.glob("*")) if INPUT_DIR.exists() else []
    print(f"\n{'='*60}")
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
    print(f"{'='*60}\n")
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
        "page": 6, "flag": "green",
        "claim_text": "The company's Scope 1 emissions for 2024 were 1,850 tonnes CO2 equivalent.",
        "data_point": "scope1_emission", "claimed_value": 1850, "source_value": 1850,
        "unit": "tCO2e", "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2", "source_cell": "B5",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 1,850 tCO2e, Excel Total Scope1 = 1,850 tCO2e — EXACT MATCH",
    },
    {
        "page": 7, "flag": "red",
        "claim_text": "The company's Scope 2 emissions for 2024 were 4,200 tonnes CO2 equivalent.",
        "data_point": "scope2_emission", "claimed_value": 4200, "source_value": 4020,
        "unit": "tCO2e", "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2", "source_cell": "C5",
        "deviation_pct": 4.48,
        "explanation": "⚠️ MATERIAL MISSTATEMENT: PDF claims 4,200 tCO2e but Excel Total Scope2 = 4,020 tCO2e. Overstatement of 180 tonnes (4.48%). Exceeds ESRS E1 materiality threshold.",
    },
    {
        "page": 7, "flag": "red",
        "claim_text": "The total Scope 1 and Scope 2 emissions amount to 6,050 tonnes CO2 equivalent.",
        "data_point": "scope1_scope2_total", "claimed_value": 6050, "source_value": 5870,
        "unit": "tCO2e", "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2", "source_cell": "B5+C5",
        "deviation_pct": 3.07,
        "explanation": "⚠️ ARITHMETIC ERROR: PDF claims 6,050 but 1,850 + 4,020 = 5,870. A 180-tonne discrepancy. The PDF total is mathematically inconsistent with the source data.",
    },
    {
        "page": 10, "flag": "red",
        "claim_text": "The total headcount as of December 31, 2024 was 2,340 employees.",
        "data_point": "headcount", "claimed_value": 2340, "source_value": 2290,
        "unit": "employees", "source_file": "hr_export_2024.csv",
        "source_sheet": "Sheet1", "source_cell": "aktív rows",
        "deviation_pct": 2.18,
        "explanation": "⚠️ HEADCOUNT DISCREPANCY: PDF states 2,340 but CSV contains only 2,290 active employees. 50 phantom employees. Possible data entry error or outdated HR extract used in report.",
    },
    {
        "page": 8, "flag": "green",
        "claim_text": "The estimated Scope 3 emissions were 18,400 tonnes CO2 equivalent.",
        "data_point": "scope3_emission", "claimed_value": 18400, "source_value": 18400,
        "unit": "tCO2e", "source_file": "scope3_szallito.xlsx",
        "source_sheet": "Scope3", "source_cell": "C6",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 18,400 tCO2e, Scope3 supplier Excel Total = 18,400 tCO2e — CONSISTENT",
    },
    {
        "page": 9, "flag": "green",
        "claim_text": "The share of renewable energy in total energy consumption was 67%.",
        "data_point": "renewable_pct", "claimed_value": 67, "source_value": 67,
        "unit": "%", "source_file": "energia_2024.xlsx",
        "source_sheet": "Megujulo", "source_cell": "D2",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 67%, Excel Megujulo Arány = 67%. Verified by Q4 E.ON invoice (2,077/3,100 = 67%). — CONSISTENT",
    },
    {
        "page": 14, "flag": "green",
        "claim_text": "E.ON Q4 invoice: 3,100 MWh total, 2,077 MWh renewable.",
        "data_point": "q4_invoice", "claimed_value": 67, "source_value": 67,
        "unit": "%", "source_file": "energia_szamla_Q4.pdf",
        "source_sheet": "Q4", "source_cell": "Line items",
        "deviation_pct": 0.0,
        "explanation": "Q4 invoice confirms 67% renewable share (2,077 / 3,100) — cross-validated with annual Excel data",
    },
    {
        "page": 11, "flag": "grey",
        "claim_text": "The number of participants in training programs was 1,240 employees.",
        "data_point": "training_participants", "claimed_value": 1240, "source_value": None,
        "unit": "employees", "source_file": None,
        "source_sheet": None, "source_cell": None,
        "deviation_pct": None,
        "explanation": "No source document configured for training_participants. Claim references internal training records — requires manual verification.",
    },
    {
        "page": 4, "flag": "grey",
        "claim_text": "The company conducts production activities at 3 sites.",
        "data_point": "production_sites", "claimed_value": 3, "source_value": None,
        "unit": "sites", "source_file": None,
        "source_sheet": None, "source_cell": None,
        "deviation_pct": None,
        "explanation": "No source document configured for production_sites. Easily verifiable through site registry but not in this audit scope.",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────


def _compute_summary(findings: list) -> dict:
    green = sum(1 for f in findings if f.get("flag") == "green")
    yellow = sum(1 for f in findings if f.get("flag") == "yellow")
    red = sum(1 for f in findings if f.get("flag") == "red")
    grey = sum(1 for f in findings if f.get("flag") == "grey")
    red_flags = [
        {
            "data_point": f["data_point"],
            "claimed": f.get("claimed_value"),
            "actual": f.get("source_value"),
            "deviation_pct": f.get("deviation_pct"),
            "explanation": f.get("explanation", ""),
        }
        for f in findings if f.get("flag") == "red"
    ]
    return {
        "green_count": green,
        "yellow_count": yellow,
        "red_count": red,
        "grey_count": grey,
        "total": len(findings),
        "red_flags": red_flags,
        "verdict": "PASS" if red == 0 else f"FAIL — {red} material misstatement(s) detected",
        "materiality_note": (
            f"{red} material error(s) found. Auditor must investigate flagged items before signing off."
            if red > 0
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


# ── Endpoints ──────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path(__file__).parent / "ui.html"
    if ui_path.exists():
        return HTMLResponse(ui_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Atlas — CSRD Audit Intelligence</h1><p>API is running. UI not found at ui.html</p>")


@app.get("/health")
async def health_check():
    """System health + input file inventory."""
    if not INPUT_DIR.exists():
        return JSONResponse({
            "status": "ok",
            "mode": "mock" if MOCK_MODE else "live",
            "input_files": [],
            "input_file_count": 0,
            "ready": False,
        })

    files = sorted(
        [{"filename": f.name, "size_kb": round(f.stat().st_size / 1024, 1)} for f in INPUT_DIR.iterdir() if f.is_file()],
        key=lambda x: x["filename"],
    )
    return JSONResponse({
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
    })


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

    return JSONResponse({
        "evidence": sorted(findings, key=lambda x: x.get("page", 0)),
        "summary": _compute_summary(findings),
    })


@app.get("/report")
async def get_report():
    """Return the full audit report."""
    if REPORT_PATH.exists():
        try:
            return JSONResponse(json.loads(REPORT_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, IOError):
            return JSONResponse({"error": "Report file is corrupted."}, status_code=500)
    return JSONResponse({"error": "No report generated yet. Run POST /audit first."}, status_code=404)


@app.post("/audit")
async def run_audit():
    """Trigger audit — mock (instant) or live (deterministic pipeline)."""
    if MOCK_MODE:
        return JSONResponse({
            "mode": "mock",
            "evidence": MOCK_EVIDENCE,
            "summary": _compute_summary(MOCK_EVIDENCE),
        })

    try:
        from pipeline import run_full_audit

        report = run_full_audit()
        findings = report.get("findings", [])
        return JSONResponse({
            "mode": "live",
            "evidence": sorted(findings, key=lambda x: x.get("page", 0)),
            "summary": _compute_summary(findings),
        })
    except Exception as e:
        return JSONResponse({
            "mode": "live",
            "error": str(e),
            "evidence": [],
            "summary": _compute_summary([]),
        }, status_code=500)


@app.post("/reset")
async def reset_workspace():
    """Clear all audit outputs. Ready for a fresh run."""
    from pipeline import reset_workspace as do_reset

    result = do_reset()
    return JSONResponse({"status": "reset", **result})


@app.get("/stream")
async def stream_audit(request: Request):
    """SSE real-time audit event stream."""
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if MOCK_MODE:
        return StreamingResponse(_mock_stream(request), media_type="text/event-stream", headers=headers)
    return StreamingResponse(_live_stream(request), media_type="text/event-stream", headers=headers)


# ── SSE: Mock stream (dramatic demo mode) ──────────────────────────────


async def _mock_stream(request: Request) -> AsyncGenerator[str, None]:
    """Cinematic SSE stream for live demos."""
    yield _sse_event("status", {"message": "🚀 Atlas CSRD Audit Engine initializing...", "mode": "mock"})
    await asyncio.sleep(0.3)

    # Phase 1: Read input
    yield _sse_event("phase", {"phase": "scan", "message": "📋 Scanning input workspace..."})
    await asyncio.sleep(0.3)
    for fname in ["atlas_sustainability_statement.pdf", "energia_2024.xlsx", "hr_export_2024.csv",
                   "scope3_szallito.xlsx", "energia_szamla_Q4.pdf"]:
        yield _sse_event("file_found", {"filename": fname})
        await asyncio.sleep(0.1)
    yield _sse_event("phase", {"phase": "scan_done", "message": "✅ 5 input files detected", "count": 5})
    await asyncio.sleep(0.2)

    # Phase 2: TODO list
    todos = [
        "Analyze PDF structure (15 pages, ESRS E1)",
        "Parse pages 1–5: Executive Summary & Scope 1",
        "Parse pages 6–10: Scope 2, Scope 3, Renewable Energy",
        "Parse pages 11–15: Workforce, Training, Governance",
        "Trace scope1_emission → energia_2024.xlsx",
        "Trace scope2_emission → energia_2024.xlsx",
        "Trace scope1_scope2_total → compute sum",
        "Trace headcount → hr_export_2024.csv",
        "Trace scope3_emission → scope3_szallito.xlsx",
        "Trace renewable_pct → energia_2024.xlsx + Q4 invoice",
        "Validate all claims (deterministic math)",
        "Generate audit report → audit_report.json",
    ]
    yield _sse_event("todo", {"items": todos, "total": len(todos)})
    await asyncio.sleep(0.3)

    # Phase 3: Parser subagents (simulated)
    parser_tasks = [
        ("Parser #1", "Extracting claims from pages 1–5", "scanned"),
        ("Parser #2", "Extracting claims from pages 6–10", "scanned"),
        ("Parser #3", "Extracting claims from pages 11–15", "scanned"),
    ]
    for agent, task, status in parser_tasks:
        yield _sse_event("agent_start", {"agent": agent, "task": task})
        await asyncio.sleep(0.25)
        yield _sse_event("agent_progress", {"agent": agent, "status": status})
        await asyncio.sleep(0.15)
        yield _sse_event("agent_done", {"agent": agent, "output": "claims saved to workspace/claims/"})
        await asyncio.sleep(0.1)

    yield _sse_event("phase", {"phase": "parse_done", "message": "✅ 8 claims extracted from 15 pages"})
    await asyncio.sleep(0.3)

    # Phase 4: Tracer subagents — one per claim, with drama for red flags
    tracer_findings = [
        ("scope1_emission", "Tracer — Scope 1", "energia_2024.xlsx / Scope1_Scope2 / B5", "green", 0.0),
        ("scope2_emission", "Tracer — Scope 2", "energia_2024.xlsx / Scope1_Scope2 / C5", "red", 4.48),
        ("scope1_scope2_total", "Tracer — Scope 1+2 Total", "energia_2024.xlsx / Scope1_Scope2 / computed", "red", 3.07),
        ("headcount", "Tracer — Headcount", "hr_export_2024.csv", "red", 2.18),
        ("scope3_emission", "Tracer — Scope 3", "scope3_szallito.xlsx / Scope3 / C6", "green", 0.0),
        ("renewable_pct", "Tracer — Renewable %", "energia_2024.xlsx / Megujulo / D2", "green", 0.0),
    ]
    for dp_id, agent, source, flag, dev in tracer_findings:
        yield _sse_event("agent_start", {"agent": agent, "data_point": dp_id, "source": source})
        await asyncio.sleep(0.2)
        if flag == "red":
            yield _sse_event("finding", {
                "agent": agent, "flag": flag, "data_point": dp_id,
                "message": f"⚠️  DISCREPANCY FOUND — {dev}% deviation",
            })
            await asyncio.sleep(0.3)
        yield _sse_event("agent_done", {
            "agent": agent, "flag": flag, "deviation_pct": dev,
            "output_file": f"evidence/{dp_id}.json",
        })
        await asyncio.sleep(0.15)

    yield _sse_event("phase", {"phase": "trace_done", "message": "✅ All claims traced and validated"})
    await asyncio.sleep(0.3)

    # Phase 5: Complete with summary
    summary = _compute_summary(MOCK_EVIDENCE)
    yield _sse_event("complete", {
        "evidence": sorted(MOCK_EVIDENCE, key=lambda x: x.get("page", 0)),
        "summary": summary,
        "message": f"Audit complete. {summary['red_count']} material misstatements found." if summary['red_count'] > 0 else "Audit complete. No material misstatements.",
    })


# ── SSE: Live stream (deterministic pipeline) ──────────────────────────


async def _live_stream(request: Request) -> AsyncGenerator[str, None]:
    """Live SSE stream using the deterministic pipeline."""
    from pipeline import run_full_audit
    import threading
    import queue

    event_queue: queue.Queue = queue.Queue()

    def progress_callback(stage, detail):
        event_queue.put((stage, detail))

    # Run audit in background thread
    def _run():
        try:
            run_full_audit(progress_callback=progress_callback)
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
            yield _sse_event("complete", {
                "message": "Audit complete",
                "summary": detail,
            })
            complete_sent = True
        elif stage == "error":
            yield _sse_event("error", detail)
            complete_sent = True
        else:
            yield _sse_event(stage, detail)


# ── Startup info ───────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
