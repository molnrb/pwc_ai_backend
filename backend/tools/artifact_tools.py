"""Shared artifact tools for deepagents workers."""

import json
import os
from pathlib import Path

from langchain_core.tools import tool

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "workspace"))
CLAIMS_DIR = WORKSPACE_DIR / "claims"
EVIDENCE_DIR = WORKSPACE_DIR / "evidence"


def _list_json_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.glob("*.json") if path.is_file())


@tool
def list_claim_files() -> str:
    """List all claim batch files currently stored in workspace/claims."""
    return json.dumps({"files": _list_json_files(CLAIMS_DIR)})


@tool
def read_claim_file(filename: str) -> str:
    """Read one claim batch JSON file from workspace/claims."""
    path = CLAIMS_DIR / filename
    if not path.exists():
        return json.dumps({"error": f"Claim file '{filename}' not found"})
    return path.read_text(encoding="utf-8")


@tool
def list_evidence_files() -> str:
    """List all evidence batch files currently stored in workspace/evidence."""
    return json.dumps({"files": _list_json_files(EVIDENCE_DIR)})


@tool
def read_evidence_file(filename: str) -> str:
    """Read one evidence batch JSON file from workspace/evidence."""
    path = EVIDENCE_DIR / filename
    if not path.exists():
        return json.dumps({"error": f"Evidence file '{filename}' not found"})
    return path.read_text(encoding="utf-8")