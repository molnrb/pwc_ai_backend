"""Helpers for selecting the active audit input bundle and manifest."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

INPUT_SUBDIR_ENV = "ATLAS_INPUT_SUBDIR"
STATEMENT_PDF_ENV = "ATLAS_STATEMENT_PDF"
DEFAULT_INPUT_SUBDIR = "input"
MANIFEST_FILENAME = "audit_index.json"


def get_workspace_dir(workspace_dir: str | Path | None = None) -> Path:
    if workspace_dir is not None:
        return Path(workspace_dir)

    return Path(os.environ.get("WORKSPACE_DIR", str(Path(__file__).parent / "workspace")))


def get_input_subdir() -> str:
    return os.environ.get(INPUT_SUBDIR_ENV, DEFAULT_INPUT_SUBDIR).strip() or DEFAULT_INPUT_SUBDIR


def get_input_dir(workspace_dir: str | Path | None = None) -> Path:
    return get_workspace_dir(workspace_dir) / get_input_subdir()


def get_manifest_path(workspace_dir: str | Path | None = None) -> Path:
    return get_input_dir(workspace_dir) / MANIFEST_FILENAME


def load_audit_manifest(workspace_dir: str | Path | None = None) -> dict[str, Any] | None:
    manifest_path = get_manifest_path(workspace_dir)
    if not manifest_path.exists():
        return None

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def get_statement_filename(default_filename: str | None = None, workspace_dir: str | Path | None = None) -> str | None:
    env_filename = os.environ.get(STATEMENT_PDF_ENV, "").strip()
    if env_filename:
        return env_filename

    manifest = load_audit_manifest(workspace_dir)
    if manifest is not None:
        statement = manifest.get("statement_document")
        if isinstance(statement, dict):
            statement_path = str(statement.get("path", "")).strip()
            if statement_path:
                return Path(statement_path).name

    return default_filename


def resolve_input_path(filename: str, workspace_dir: str | Path | None = None) -> Path:
    return get_input_dir(workspace_dir) / filename