"""
Document store — unified access layer for all ingested documents.

Maintains a registry of DocumentAssets and their parsed representations
(TextBlock, SheetTable, CsvTable) indexed by file name.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from models.audit_types import (
    DocumentAsset,
    TextBlock,
    TableBlock,
    SheetTable,
    CsvTable,
)

from ingestion.pdf_ingestor import ingest_pdf
from ingestion.excel_ingestor import ingest_excel
from ingestion.csv_ingestor import ingest_csv

logger = logging.getLogger("atlas.ingestion.store")

WORKSPACE = Path(__file__).parent.parent / "workspace"
INGESTED_DIR = WORKSPACE / "ingested"


class DocumentStore:
    """Holds all ingested documents and provides query access.

    Usage:
        store = DocumentStore()
        store.ingest_all(INPUT_DIR)
        pdf_blocks = store.get_pdf_blocks("atlas_sustainability_statement.pdf")
        csv_table = store.get_csv_table("hr_export_2024.csv")
    """

    def __init__(self) -> None:
        self.assets: dict[str, DocumentAsset] = {}  # filename → asset
        self.pdf_blocks: dict[str, list[TextBlock | TableBlock]] = {}
        self.sheet_tables: dict[str, list[SheetTable]] = {}  # filename → list of sheets
        self.csv_tables: dict[str, CsvTable] = {}  # filename → CsvTable

    # ── ingest ──────────────────────────────────────────────────────

    def ingest_all(self, input_dir: Path) -> int:
        """Load every supported file from a directory.

        Returns total number of files ingested.
        """
        count = 0
        for path in sorted(input_dir.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            try:
                if suffix == ".pdf":
                    self.ingest_pdf_file(path)
                elif suffix in (".xlsx", ".xls"):
                    self.ingest_excel_file(path)
                elif suffix == ".csv":
                    self.ingest_csv_file(path)
                else:
                    logger.debug("Skipping unsupported file: %s", path.name)
                    continue
                count += 1
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", path.name, exc)

        logger.info("Document store: %d files ingested", count)
        return count

    def ingest_pdf_file(self, path: Path) -> None:
        blocks = ingest_pdf(path)
        self.pdf_blocks[path.name] = blocks
        self.assets[path.name] = DocumentAsset(
            asset_id=f"doc_{hash(path.name) & 0x7FFFFFFF:08x}",
            filename=path.name,
            file_type=".pdf",
            role_hint=_infer_role(path.name),
        )

    def ingest_excel_file(self, path: Path) -> None:
        tables = ingest_excel(path)
        self.sheet_tables[path.name] = tables
        self.assets[path.name] = DocumentAsset(
            asset_id=f"doc_{hash(path.name) & 0x7FFFFFFF:08x}",
            filename=path.name,
            file_type=path.suffix.lower(),
            role_hint=_infer_role(path.name),
        )

    def ingest_csv_file(self, path: Path) -> None:
        table = ingest_csv(path)
        self.csv_tables[path.name] = table
        self.assets[path.name] = DocumentAsset(
            asset_id=f"doc_{hash(path.name) & 0x7FFFFFFF:08x}",
            filename=path.name,
            file_type=".csv",
            role_hint=_infer_role(path.name),
        )

    # ── query ───────────────────────────────────────────────────────

    def get_pdf_blocks(self, filename: str) -> list[TextBlock | TableBlock]:
        return self.pdf_blocks.get(filename, [])

    def get_excel_sheets(self, filename: str) -> list[SheetTable]:
        return self.sheet_tables.get(filename, [])

    def get_csv_table(self, filename: str) -> Optional[CsvTable]:
        return self.csv_tables.get(filename)

    def get_text_blocks_only(self, filename: str) -> list[TextBlock]:
        """Return only TextBlock items (no TableBlock) from a PDF."""
        return [b for b in self.get_pdf_blocks(filename) if isinstance(b, TextBlock)]

    def list_filenames(self, role_hint: Optional[str] = None) -> list[str]:
        """List all ingested filenames, optionally filtered by role."""
        if role_hint is None:
            return sorted(self.assets.keys())
        return sorted(
            f for f, a in self.assets.items() if a.role_hint == role_hint
        )

    # ── persistence ─────────────────────────────────────────────────

    def save_artifacts(self) -> None:
        """Serialize all ingested tables as JSON for inspection/debugging."""
        INGESTED_DIR.mkdir(parents=True, exist_ok=True)
        # Save PDF blocks
        for filename, blocks in self.pdf_blocks.items():
            data = []
            for b in blocks:
                if isinstance(b, TextBlock):
                    data.append({"type": "text", "page": b.page, "block_id": b.block_id, "text": b.text[:500]})
                elif isinstance(b, TableBlock):
                    data.append({"type": "table", "page": b.page, "block_id": b.block_id, "rows": len(b.rows)})
            out_path = INGESTED_DIR / f"{Path(filename).stem}_pdf_blocks.json"
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        # Save sheet tables
        for filename, tables in self.sheet_tables.items():
            out_path = INGESTED_DIR / f"{Path(filename).stem}_sheets.json"
            payload = [t.model_dump() for t in tables]
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))

        # Save CSV tables
        for filename, table in self.csv_tables.items():
            out_path = INGESTED_DIR / f"{Path(filename).stem}_csv.json"
            out_path.write_text(json.dumps(table.model_dump(), indent=2, ensure_ascii=False, default=str))

        logger.info("Document store artifacts saved to %s", INGESTED_DIR)


# ── helpers ─────────────────────────────────────────────────────────


def _infer_role(filename: str) -> str:
    """Infer the role of a document from its filename."""
    name = filename.lower()
    if "statement" in name or "sustainability" in name:
        return "statement"
    if "energia" in name and "szamla" in name:
        return "supporting_invoice"
    if "energia" in name:
        return "energy_source"
    if "hr" in name or "human" in name:
        return "hr_source"
    if "scope3" in name or "szallito" in name:
        return "scope3_source"
    return "supporting"


# ── singleton ───────────────────────────────────────────────────────

_store_instance: Optional[DocumentStore] = None


def get_document_store() -> DocumentStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = DocumentStore()
    return _store_instance