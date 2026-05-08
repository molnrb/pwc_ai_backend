"""Tracer subagent — creates and manages the Excel tracing agent."""

import os
from deepagents import create_deep_agent
from langchain_deepseek import ChatDeepSeek
from tools.excel_tools import read_excel_cell, read_excel_summary, count_csv_rows, write_evidence
from tools.validator_tool import validate_claim, compute_total

MODEL = os.environ.get("TRACER_MODEL", "deepseek-chat")


def create_tracer_subagent():
    """Create the Tracer subagent configured with DeepSeek."""
    model = ChatDeepSeek(model=MODEL, disabled_params={"thinking": None})
    return create_deep_agent(
        model=model,
        tools=[read_excel_cell, read_excel_summary, count_csv_rows, validate_claim, compute_total, write_evidence],
        system_prompt="""You are a CSRD Audit Tracer subagent.

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
""",
        name="tracer_subagent",
    )


# Singleton instance for module-level import
tracer_subagent = create_tracer_subagent()