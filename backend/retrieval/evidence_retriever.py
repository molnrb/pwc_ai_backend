"""
Unified evidence retriever — routes claims to the correct search strategy
based on file type and returns a top-k ranked candidate list.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from models.audit_types import (
    NormalizedClaim,
    EvidenceCandidate,
    TextBlock,
    TableBlock,
    SheetTable,
    CsvTable,
)
from retrieval.tabular_evidence_search import find_tabular_evidence
from retrieval.pdf_evidence_search import find_pdf_evidence

logger = logging.getLogger("atlas.retrieval")

WORKSPACE = Path(__file__).parent.parent / "workspace"
CANDIDATES_DIR = WORKSPACE / "evidence_candidates"


class EvidenceRetriever:
    """Retrieves evidence candidates across all source document types.

    Usage:
        retriever = EvidenceRetriever()
        retriever.add_excel_sheets("energia_2024.xlsx", sheet_tables)
        retriever.add_pdf_blocks("energia_szamla_Q4.pdf", pdf_blocks)
        candidates = retriever.retrieve(claim)
    """

    def __init__(self) -> None:
        self._excel_tables: dict[str, list[SheetTable]] = {}
        self._csv_tables: dict[str, CsvTable] = {}
        self._pdf_blocks: dict[str, list[TextBlock | TableBlock]] = {}

    def add_excel_sheets(self, filename: str, tables: list[SheetTable]) -> None:
        self._excel_tables[filename] = tables

    def add_csv_table(self, filename: str, table: CsvTable) -> None:
        self._csv_tables[filename] = table

    def add_pdf_blocks(self, filename: str, blocks: list[TextBlock | TableBlock]) -> None:
        self._pdf_blocks[filename] = blocks

    def retrieve(self, claim: NormalizedClaim) -> list[EvidenceCandidate]:
        """Find top-k evidence candidates for a normalized claim.

        Searches across all known source documents and returns a unified,
        ranked list.
        """
        all_candidates: list[EvidenceCandidate] = []

        # Excel search
        for filename, tables in self._excel_tables.items():
            all_candidates.extend(find_tabular_evidence(claim, tables))

        # CSV search
        for filename, table in self._csv_tables.items():
            all_candidates.extend(find_tabular_evidence(claim, [table]))

        # PDF search
        for filename, blocks in self._pdf_blocks.items():
            all_candidates.extend(find_pdf_evidence(claim, blocks))

        # Sort by retrieval confidence, take top-k
        all_candidates.sort(key=lambda c: c.retrieval_confidence, reverse=True)

        return all_candidates[:5]  # top-5

    def save_artifacts(self, claims: list[NormalizedClaim]) -> None:
        """Save all evidence candidates for inspection."""
        CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
        for claim in claims:
            candidates = self.retrieve(claim)
            payload = [c.model_dump() for c in candidates]
            out_path = CANDIDATES_DIR / f"evidence_{claim.claim_id}.json"
            out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        logger.info("Evidence candidates saved to %s", CANDIDATES_DIR)


# ── singleton ───────────────────────────────────────────────────────

_retriever_instance: Optional[EvidenceRetriever] = None


def get_retriever() -> EvidenceRetriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = EvidenceRetriever()
    return _retriever_instance