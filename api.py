"""FastAPI server + SSE stream + static UI — Atlas CSRD Audit Intelligence."""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

load_dotenv()

# Ensure WORKSPACE_DIR is an absolute path so deepagents tools write to the correct location
_ws = os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace"))
os.environ["WORKSPACE_DIR"] = _ws
WORKSPACE = Path(_ws)
CLAIMS_DIR = WORKSPACE / "claims"
EVIDENCE_DIR = WORKSPACE / "evidence"
REPORT_PATH = WORKSPACE / "audit_report.json"
INPUT_DIR = WORKSPACE / "input"

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() in ("1", "true", "yes")

app = FastAPI(title="Atlas CSRD Audit Intelligence")

# CORS — frontend may run on a different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mock evidence data — used when MOCK_MODE=True
# ---------------------------------------------------------------------------
MOCK_EVIDENCE = [
    {
        "page": 6,
        "flag": "green",
        "claim_text": "Scope 1 kibocsátás 2024-ben 1 850 tonna CO₂-egyenérték volt.",
        "data_point": "scope1_emission",
        "claimed_value": 1850,
        "source_value": 1850,
        "unit": "tCO2e",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2",
        "source_cell": "B5",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 1850 tCO2e, Excel Total Scope1 cell shows 1850 tCO2e, deviation 0.0%",
    },
    {
        "page": 7,
        "flag": "red",
        "claim_text": "A vállalat Scope 2 kibocsátása 2024-ben 4 200 tonna CO₂-egyenérték.",
        "data_point": "scope2_emission",
        "claimed_value": 4200,
        "source_value": 4020,
        "unit": "tCO2e",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2",
        "source_cell": "C5",
        "deviation_pct": 4.48,
        "explanation": "PDF claims 4200 tCO2e, Excel Total Scope2 cell shows 4020 tCO2e, deviation 4.48%",
    },
    {
        "page": 7,
        "flag": "red",
        "claim_text": "A teljes Scope 1+2 kibocsátás 6 050 tonna CO₂-egyenérték.",
        "data_point": "scope1_scope2_total",
        "claimed_value": 6050,
        "source_value": 5870,
        "unit": "tCO2e",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Scope1_Scope2",
        "source_cell": "B5+C5",
        "deviation_pct": 3.07,
        "explanation": "PDF claims 6050 tCO2e, Excel Total Scope1 (1850) + Scope2 (4020) = 5870 tCO2e, deviation 3.07%",
    },
    {
        "page": 9,
        "flag": "red",
        "claim_text": "A vállalat teljes munkavállalói létszáma 2024-ben 2 340 fő volt.",
        "data_point": "headcount",
        "claimed_value": 2340,
        "source_value": 2290,
        "unit": "fő",
        "source_file": "hr_export_2024.csv",
        "source_sheet": "Sheet1",
        "source_cell": "aktív sorok",
        "deviation_pct": 2.18,
        "explanation": "PDF claims 2340 fő, CSV aktív sorok száma 2290, deviation 2.18%",
    },
    {
        "page": 10,
        "flag": "green",
        "claim_text": "Scope 3 kibocsátás 2024-ben 18 400 tonna CO₂-egyenérték.",
        "data_point": "scope3_emission",
        "claimed_value": 18400,
        "source_value": 18400,
        "unit": "tCO2e",
        "source_file": "scope3_szallito.xlsx",
        "source_sheet": "Scope3",
        "source_cell": "B2",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 18400 tCO2e, Scope3 szállítói Excel Total = 18400 tCO2e, deviation 0.0%",
    },
    {
        "page": 11,
        "flag": "green",
        "claim_text": "A megújuló energia aránya 2024-ben 67% volt.",
        "data_point": "renewable_pct",
        "claimed_value": 67,
        "source_value": 67,
        "unit": "%",
        "source_file": "energia_2024.xlsx",
        "source_sheet": "Megujulo",
        "source_cell": "D4",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 67%, Excel Megujulo Arány = 67%, deviation 0.0%",
    },
    {
        "page": 14,
        "flag": "green",
        "claim_text": "Q4 energia számla összesen 1 240 MWh.",
        "data_point": "q4_invoice",
        "claimed_value": 1240,
        "source_value": 1240,
        "unit": "MWh",
        "source_file": "energia_szamla_Q4.pdf",
        "source_sheet": "Q4",
        "source_cell": "Total",
        "deviation_pct": 0.0,
        "explanation": "PDF claims 1240 MWh, Q4 számla Total = 1240 MWh, deviation 0.0%",
    },
]

# ---------------------------------------------------------------------------
# Lazy orchestrator import
# ---------------------------------------------------------------------------
_atlas = None


def get_atlas():
    global _atlas
    if _atlas is None:
        from orchestrator import atlas
        _atlas = atlas
    return _atlas


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path(__file__).parent / "ui.html"
    if ui_path.exists():
        return HTMLResponse(ui_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Atlas CSRD Audit Intelligence</h1><p>UI not found.</p>")


@app.get("/health")
async def health_check():
    if not INPUT_DIR.exists():
        return JSONResponse({
            "status": "ok",
            "input_files": [],
            "input_file_count": 0,
            "mock_mode": MOCK_MODE,
        })
    files = sorted(
        [{"filename": f.name, "size_bytes": f.stat().st_size} for f in INPUT_DIR.iterdir() if f.is_file()],
        key=lambda x: x["filename"],
    )
    return JSONResponse({
        "status": "ok",
        "input_files": files,
        "input_file_count": len(files),
        "mock_mode": MOCK_MODE,
    })


@app.get("/evidence")
async def get_evidence():
    """Return all evidence results and summary — reads from disk or returns mock data."""
    if MOCK_MODE:
        return JSONResponse({
            "evidence": MOCK_EVIDENCE,
            "summary": _compute_summary(MOCK_EVIDENCE),
        })

    findings = _collect_evidence_files()
    return JSONResponse({
        "evidence": findings,
        "summary": _compute_summary(findings),
    })


@app.get("/report")
async def get_report():
    if REPORT_PATH.exists():
        try:
            data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            return JSONResponse(data)
        except (json.JSONDecodeError, IOError):
            return JSONResponse({"error": "Report file is corrupted."}, status_code=500)
    return JSONResponse({"error": "No report generated yet. Run POST /audit first."}, status_code=404)


@app.post("/audit")
async def run_audit():
    """Trigger a full audit run via the orchestrator (live) or return mock results."""
    if MOCK_MODE:
        return JSONResponse({
            "evidence": MOCK_EVIDENCE,
            "summary": _compute_summary(MOCK_EVIDENCE),
        })

    findings = []
    summary = {"green_count": 0, "yellow_count": 0, "red_count": 0, "grey_count": 0, "red_flags": []}
    try:
        atlas = get_atlas()
        atlas.invoke({
            "messages": [{
                "role": "user",
                "content": (
                    "Run the full CSRD audit on atlas_sustainability_statement.pdf. "
                    "Parse all pages, trace all claims, validate everything, "
                    "and generate the audit_report.json."
                ),
            }]
        })
        findings = _collect_evidence_files()
        summary = _compute_summary(findings)
    except Exception as e:
        summary["error"] = str(e)

    return JSONResponse({"evidence": findings, "summary": summary})


@app.get("/stream")
async def stream_audit(request: Request):
    """SSE stream — pushes audit events in real time (MOCK or live)."""
    if MOCK_MODE:
        return StreamingResponse(
            _mock_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    return StreamingResponse(
        _live_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# SSE stream generators
# ---------------------------------------------------------------------------


async def _mock_stream(request: Request) -> AsyncGenerator[str, None]:
    """MOCK_MODE SSE stream — simulates the full audit pipeline."""
    todos = [
        "Read PDF page count",
        "Parse pages 1-5",
        "Parse pages 6-10",
        "Parse pages 11-15",
        "Trace scope1_emission",
        "Trace scope2_emission",
        "Trace scope1_scope2_total",
        "Trace headcount",
        "Trace scope3_emission",
        "Trace renewable_pct",
        "Trace Q4 invoice",
        "Validate all claims",
        "Generate final report",
    ]

    # 1) Send todo list
    yield _sse_event("todo", {"items": todos})
    await asyncio.sleep(0.3)

    # 2) Simulate agent activity
    agents = [
        ("Parser #1", "Parse pages 1-5"),
        ("Parser #2", "Parse pages 6-10"),
        ("Parser #3", "Parse pages 11-15"),
    ]
    for agent, task in agents:
        yield _sse_event("agent_start", {"agent": agent, "task": task})
        await asyncio.sleep(0.2)
        yield _sse_event("agent_done", {"agent": agent})
        await asyncio.sleep(0.1)

    for evidence_item in MOCK_EVIDENCE:
        agent = f"Tracer — {evidence_item['data_point']}"
        task = f"Trace and validate {evidence_item['data_point']}"
        yield _sse_event("agent_start", {"agent": agent, "task": task})
        await asyncio.sleep(0.15)
        yield _sse_event("agent_done", {
            "agent": agent,
            "output_file": f"evidence/batch_{evidence_item['data_point']}.json",
        })
        await asyncio.sleep(0.05)

    # 3) Send complete
    yield _sse_event("complete", {
        "evidence": sorted(MOCK_EVIDENCE, key=lambda x: x["page"]),
        "summary": _compute_summary(MOCK_EVIDENCE),
    })


async def _live_stream(request: Request) -> AsyncGenerator[str, None]:
    """Live SSE stream using deepagents astream + file polling fallback."""
    try:
        atlas = get_atlas()
        seen_files = set()

        # Fire-and-forget the audit in background
        _run_live_audit(atlas)

        # Poll for new evidence/claims files until disconnected or all evidence arrives
        complete_sent = False
        for _ in range(240):  # max 240 * 0.5s = 2 minutes
            if await request.is_disconnected():
                break

            current_evidence = sorted(EVIDENCE_DIR.glob("*.json"))
            for f in current_evidence:
                if f.name not in seen_files:
                    seen_files.add(f.name)
                    try:
                        data = json.loads(f.read_text(encoding="utf-8"))
                        if isinstance(data, list):
                            for item in data:
                                yield _sse_event("agent_done", {
                                    "agent": f"Tracer — {item.get('data_point', 'unknown')}",
                                    "output_file": f.name,
                                })
                        elif isinstance(data, dict):
                            yield _sse_event("agent_done", {
                                "agent": f"Tracer — {data.get('data_point', 'unknown')}",
                                "output_file": f.name,
                            })
                    except (json.JSONDecodeError, IOError):
                        pass

            current_claims = sorted(CLAIMS_DIR.glob("*.json"))
            for f in current_claims:
                if f.name not in seen_files:
                    seen_files.add(f.name)
                    yield _sse_event("agent_done", {
                        "agent": "Parser",
                        "output_file": f.name,
                    })

            # Check if report exists — means audit is done
            if REPORT_PATH.exists() and not complete_sent:
                findings = _collect_evidence_files()
                yield _sse_event("complete", {
                    "evidence": sorted(findings, key=lambda x: x.get("page", 0)),
                    "summary": _compute_summary(findings),
                })
                complete_sent = True
                break

            await asyncio.sleep(0.5)

        # Fallback: if no report generated, send mock evidence
        if not complete_sent:
            yield _sse_event("complete", {
                "evidence": sorted(MOCK_EVIDENCE, key=lambda x: x.get("page", 0)),
                "summary": _compute_summary(MOCK_EVIDENCE),
            })

    except Exception as e:
        yield _sse_event("error", {"content": str(e)})


def _run_live_audit(atlas):
    """Fire-and-forget live audit invocation."""
    import threading

    def _invoke():
        try:
            atlas.invoke({
                "messages": [{
                    "role": "user",
                    "content": (
                        "Run the full CSRD audit on atlas_sustainability_statement.pdf. "
                        "Parse all pages in parallel, trace all claims, validate everything, "
                        "and generate the final audit_report.json."
                    ),
                }]
            })
        except Exception:
            pass  # Errors surface through evidence polling

    t = threading.Thread(target=_invoke, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _compute_summary(findings: list) -> dict:
    green_count = sum(1 for f in findings if f.get("flag") == "green")
    yellow_count = sum(1 for f in findings if f.get("flag") == "yellow")
    red_count = sum(1 for f in findings if f.get("flag") == "red")
    grey_count = sum(1 for f in findings if f.get("flag") not in ("green", "yellow", "red"))

    red_flags = []
    for f in findings:
        if f.get("flag") == "red":
            red_flags.append({
                "data_point": f.get("data_point", "unknown"),
                "issue": f.get("explanation", f"Deviation: {f.get('deviation_pct', 'N/A')}%"),
            })

    return {
        "green_count": green_count,
        "yellow_count": yellow_count,
        "red_count": red_count,
        "grey_count": grey_count,
        "total": len(findings),
        "red_flags": red_flags,
    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)