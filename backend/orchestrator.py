"""Atlas orchestrator — main coordination logic using deepagents."""

import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from tools.pdf_tools import extract_page_text, get_pdf_page_count, write_claims
from tools.excel_tools import read_excel_cell, read_excel_summary, count_csv_rows, write_evidence
from tools.validator_tool import validate_claim, compute_total

load_dotenv()

MODEL = os.environ.get("ORCHESTRATOR_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None

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
1. Read the claims JSON file from workspace/claims/
2. For each claim, use the source_hint to find the right source file
3. Look up the actual value in the source document using the appropriate tool:
   - Excel files → read_excel_cell (probe with read_excel_summary first to find sheet/column names)
   - CSV files → count_csv_rows
4. Compare claimed vs source using validate_claim
5. Save results using write_evidence

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
1. READ the PDF first — use the Parser subagent to get the page count
2. CREATE a TODO list dynamically: for every 5 pages, create a Parse task
3. SPAWN Parser subagents IN PARALLEL for all page groups
4. WAIT until ALL Parsers finish writing their claims to workspace/claims/
5. SPAWN Tracer subagents to trace each batch of claims
6. WAIT until ALL Tracers finish writing evidence to workspace/evidence/
7. COLLECT all evidence files from workspace/evidence/
8. GENERATE a final audit report as workspace/audit_report.json

Report format:
{
  "audit_metadata": {
    "document": "atlas_sustainability_statement.pdf",
    "standard": "ESRS E1",
    "timestamp": "...",
    "total_pages": 15,
    "total_claims_found": 8
  },
  "findings": [...all evidence objects...],
  "summary": {
    "green_count": 5,
    "yellow_count": 0,
    "red_count": 3,
    "red_flags": [
      {
        "data_point": "scope2_emission",
        "issue": "PDF claims 4200, Excel shows 4020 (4.48% deviation)"
      },
      {
        "data_point": "scope1_scope2_total",
        "issue": "PDF claims 6050, computed 5870 (3.07% deviation)"
      },
      {
        "data_point": "headcount",
        "issue": "PDF claims 2340, CSV count is 2290 (2.18% deviation)"
      }
    ]
  }
}
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
        "tools": [read_excel_cell, read_excel_summary, count_csv_rows, validate_claim, compute_total, write_evidence],
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


def get_atlas_orchestrator():
    """Lazily construct the orchestrator so imports do not fail without env setup."""
    global _atlas_orchestrator
    if _atlas_orchestrator is None:
        _atlas_orchestrator = create_atlas_orchestrator()
    return _atlas_orchestrator


def run_live_llm_audit(progress_callback=None, pdf_filename: str = "atlas_sustainability_statement.pdf") -> dict:
    """Run the live audit using the LLM-assisted parser and deterministic trace/validate steps."""
    from pipeline import run_full_audit

    return run_full_audit(
        pdf_filename=pdf_filename,
        progress_callback=progress_callback,
        parser_mode="llm",
    )