import json
import os
import fitz  # pymupdf
from langchain_core.tools import tool

from input_bundle import get_statement_filename, resolve_input_path

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "workspace")


def _input_path(filename: str) -> str:
    return str(resolve_input_path(filename, WORKSPACE_DIR))


def _statement_path() -> str:
    statement_filename = get_statement_filename("atlas_sustainability_statement.pdf", WORKSPACE_DIR)
    return _input_path(statement_filename)


def _claims_path(filename: str) -> str:
    return os.path.join(WORKSPACE_DIR, "claims", filename)


def _extract_blocks(filepath: str, page_number: int) -> str:
    try:
        doc = fitz.open(filepath)
    except Exception as exc:
        return json.dumps({"error": str(exc), "filepath": filepath})

    if page_number < 1 or page_number > len(doc):
        doc.close()
        return json.dumps({"error": f"Page {page_number} out of range (1-{len(doc)})"})

    page = doc[page_number - 1]
    blocks = page.get_text("blocks")

    result = []
    for idx, block in enumerate(blocks):
        text = block[4].strip()
        if text:
            result.append({
                "paragraph_idx": idx,
                "page": page_number,
                "text": text,
            })

    doc.close()
    return json.dumps(result, indent=2)


@tool
def extract_page_text(page_number: int) -> str:
    """Extracts text from a PDF page, broken down by paragraph blocks.
    
    Args:
        page_number: 1-indexed page number to extract
        
    Returns:
        JSON string with list of paragraphs, each containing paragraph_idx, page, and text
    """
    filepath = _statement_path()
    return _extract_blocks(filepath, page_number)


@tool
def get_pdf_page_count() -> str:
    """Returns the total number of pages in the sustainability statement PDF."""
    filepath = _statement_path()
    try:
        doc = fitz.open(filepath)
        count = len(doc)
        doc.close()
        return json.dumps({"total_pages": count})
    except Exception as exc:
        return json.dumps({"error": str(exc), "filepath": filepath})


@tool
def extract_document_page_text(filename: str, page_number: int) -> str:
    """Extract text from any PDF file in the active input bundle.

    Args:
        filename: PDF filename inside the active input bundle
        page_number: 1-indexed page number to extract

    Returns:
        JSON string with paragraph blocks from the selected page
    """
    filepath = _input_path(filename)
    return _extract_blocks(filepath, page_number)


@tool
def get_document_page_count(filename: str) -> str:
    """Return page count for any PDF file in the active input bundle."""
    filepath = _input_path(filename)
    try:
        doc = fitz.open(filepath)
        count = len(doc)
        doc.close()
        return json.dumps({"filename": filename, "total_pages": count})
    except Exception as exc:
        return json.dumps({"error": str(exc), "filename": filename, "filepath": filepath})


@tool
def write_claims(page_range: str, claims: str) -> str:
    """Saves claims found by the Parser subagent to the shared filesystem.
    
    Args:
        page_range: e.g. "1-5" or "6-10" to identify which pages were parsed
        claims: JSON string of claim objects
        
    Returns:
        Confirmation message with the file path
    """
    os.makedirs(os.path.join(WORKSPACE_DIR, "claims"), exist_ok=True)
    
    path = _claims_path(f"page_{page_range}.json")
    with open(path, "w") as f:
        f.write(claims)
    return f"Claims saved to {path}"
