import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from subagents.prompts import PARSER_SYSTEM_PROMPT
from tools.pdf_tools import extract_page_text, get_pdf_page_count, write_claims

load_dotenv()

MODEL = os.environ.get("PARSER_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None
PARSER_TIMEOUT_SECONDS = float(os.environ.get("ATLAS_PARSER_TIMEOUT_SECONDS", "300"))


def create_parser_subagent(timeout_seconds: float | None = None):
    """Create the Parser subagent configured with DeepSeek."""
    timeout = PARSER_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    model = ChatDeepSeek(
        model=MODEL,
        temperature=0,
        base_url=DEEPSEEK_API_BASE,
        timeout=timeout,
        max_retries=2,
        disabled_params={"thinking": None},
    )
    return create_deep_agent(
        model=model,
        tools=[extract_page_text, get_pdf_page_count, write_claims],
                system_prompt=PARSER_SYSTEM_PROMPT,
        name="parser_subagent",
    )