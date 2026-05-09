import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from subagents.prompts import TRACER_SYSTEM_PROMPT
from tools.artifact_tools import list_claim_files, read_claim_file
from tools.excel_tools import read_excel_cell, read_excel_summary, count_csv_rows, write_evidence
from tools.csv_tools import profile_csv, search_csv_columns, find_csv_numeric_candidates
from tools.pdf_tools import extract_document_page_text, get_document_page_count
from tools.validator_tool import validate_claim, compute_total

load_dotenv()

MODEL = os.environ.get("TRACER_MODEL", "deepseek-v4-pro")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None


def make_tracer_model() -> ChatDeepSeek:
    return ChatDeepSeek(
        model=MODEL,
        temperature=0,
        base_url=DEEPSEEK_API_BASE,
        timeout=180.0,
        max_retries=2,
        extra_body={"thinking": {"type": "disabled"}},
    )


def create_tracer_subagent():
    """Create the Tracer subagent configured with DeepSeek."""
    model = make_tracer_model()
    return create_deep_agent(
        model=model,
        tools=[
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
        system_prompt=TRACER_SYSTEM_PROMPT,
        name="tracer_subagent",
    )