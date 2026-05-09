import os

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek

from subagents.prompts import PARSER_SYSTEM_PROMPT
from tools.pdf_tools import extract_page_text, get_pdf_page_count, write_claims

load_dotenv()

MODEL = os.environ.get("PARSER_MODEL", "deepseek-chat")
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE") or None


def create_parser_subagent():
    """Create the Parser subagent configured with DeepSeek."""
    model = ChatDeepSeek(
        model=MODEL,
        temperature=0,
        base_url=DEEPSEEK_API_BASE,
        timeout=180.0,
        max_retries=2,
        disabled_params={"thinking": None},
    )
    return create_deep_agent(
        model=model,
        tools=[extract_page_text, get_pdf_page_count, write_claims],
                system_prompt=PARSER_SYSTEM_PROMPT,
        name="parser_subagent",
    )