"""Parser subagent — creates and manages the PDF parsing agent."""

import os
from deepagents import create_deep_agent
from langchain_deepseek import ChatDeepSeek
from tools.pdf_tools import extract_page_text, get_pdf_page_count, write_claims

# Use DeepSeek model — set DEEPSEEK_API_KEY in .env
MODEL = os.environ.get("PARSER_MODEL", "deepseek-chat")


def create_parser_subagent():
    """Create the Parser subagent configured with DeepSeek."""
    model = ChatDeepSeek(model=MODEL, disabled_params={"thinking": None})
    return create_deep_agent(
        model=model,
        tools=[extract_page_text, get_pdf_page_count, write_claims],
        system_prompt="""You are a CSRD Audit Parser subagent.

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
""",
        name="parser_subagent",
    )


# Singleton instance for module-level import
parser_subagent = create_parser_subagent()