"""
Canonical data model for the generic document audit pipeline.

All domain objects are explicit Pydantic models — no `dict[str, Any]` passthrough.
Raw and normalized values are stored separately; confidence scores live in
dedicated dimensions; provenance is always preserved.
"""

from __future__ import annotations

from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field


# ── Ingestion Layer models ──────────────────────────────────────────────

class DocumentAsset(BaseModel):
    """A file admitted into the audit workspace."""

    asset_id: str
    filename: str
    file_type: str  # ".pdf", ".xlsx", ".csv"
    mime_type: Optional[str] = None
    role_hint: Optional[str] = None  # "statement", "energy_source", "hr_source", ...


class DocumentPage(BaseModel):
    """Single page extracted from a PDF."""

    page_number: int
    blocks: list[TextBlock] = Field(default_factory=list)
    tables: list[TableBlock] = Field(default_factory=list)
    full_text: str = ""


class TextBlock(BaseModel):
    """A contiguous text region on a page."""

    page: Optional[int] = None
    block_id: str = ""
    text: str = ""
    bbox: Optional[tuple[float, float, float, float]] = None  # x0, y0, x1, y1
    heading_level: Optional[int] = None


class TableBlock(BaseModel):
    """A detected table region on a page or sheet."""

    block_id: str = ""
    page: Optional[int] = None
    sheet: Optional[str] = None
    rows: list[list[TableCell]] = Field(default_factory=list)
    caption: Optional[str] = None
    header_rows: int = 1  # how many top rows are headers


class TableCell(BaseModel):
    """A single cell inside a table."""

    row_idx: int
    col_idx: int
    row_label: Optional[str] = None
    col_label: Optional[str] = None
    raw_value: Optional[str | int | float] = None
    normalized_value: Optional[float | str] = None
    unit: Optional[str] = None
    year: Optional[int] = None
    cell_ref: Optional[str] = None  # e.g. "B5" or DataFrame coordinate


class SheetTable(BaseModel):
    """Represents a full Excel sheet as tabular data."""

    sheet_name: str
    source_file: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)  # list of {col: value}
    row_count: int = 0
    header_row_idx: int = 0
    merged_cells_normalized: bool = False


class CsvTable(BaseModel):
    """Represents a full CSV file as tabular data."""

    source_file: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True


# ── Candidate Extraction models ─────────────────────────────────────────

class CandidateMention(BaseModel):
    """A single span inside a block that looks like a KPI mention."""

    text: str = ""
    start_char: int = 0
    end_char: int = 0
    kind: str = ""  # "numeric", "percentage", "ratio", "count"


class CandidateValue(BaseModel):
    """The parsed numeric payload of a candidate."""

    raw: Optional[str | int | float] = None
    normalized: Optional[float] = None
    unit: Optional[str] = None
    period: Optional[str] = None  # "2024", "Q4 2024", "FY2024"
    year: Optional[int] = None


class ExtractedCandidate(BaseModel):
    """A claim candidate before normalization."""

    candidate_id: str = ""
    source_file: str = ""
    source_kind: str = ""  # "pdf_text", "pdf_table", "excel", "csv"
    raw_text: str = ""
    raw_value: Optional[str | int | float] = None
    raw_unit: Optional[str] = None
    raw_period: Optional[str] = None
    location: dict[str, Any] = Field(default_factory=dict)  # page/sheet/cell/bbox
    extraction_confidence: float = 0.0
    evidence_hint: Optional[str] = None  # e.g. "Source: xyz.xlsx"
    mentions: list[CandidateMention] = Field(default_factory=list)


# ── Normalization models ────────────────────────────────────────────────

class NormalizedClaim(BaseModel):
    """A candidate that has been mapped to a canonical data point."""

    claim_id: str = ""
    data_point_id: str = ""
    value: Optional[float | str] = None
    unit: Optional[str] = None
    period: Optional[str] = None
    source_file_hint: Optional[str] = None
    extraction_confidence: float = 0.0
    mapping_confidence: float = 0.0
    provenance: dict[str, Any] = Field(default_factory=dict)
    dedup_group: Optional[str] = None
    canonical_reason: Optional[str] = None


# ── Evidence Retrieval models ───────────────────────────────────────────

class EvidenceCandidate(BaseModel):
    """A single evidence hit found in a source document."""

    evidence_id: str = ""
    data_point_guess: Optional[str] = None
    file_name: str = ""
    source_kind: str = ""  # "pdf", "excel", "csv"
    location: dict[str, Any] = Field(default_factory=dict)
    raw_value: Optional[str | int | float] = None
    normalized_value: Optional[float | str] = None
    unit: Optional[str] = None
    period: Optional[str] = None
    retrieval_confidence: float = 0.0
    match_features: dict[str, Any] = Field(default_factory=dict)


class EvidenceMatch(BaseModel):
    """A resolved match between a claim and one evidence candidate."""

    claim_id: str = ""
    evidence_id: str = ""
    score: float = 0.0
    decision: str = ""  # "selected", "tie", "rejected"
    reason: Optional[str] = None


# ── Resolution & Validation models ──────────────────────────────────────

class ValidationResult(BaseModel):
    """Deterministic validation output for one claim-evidence pair."""

    data_point: str = ""
    claimed_value: Optional[float | str] = None
    source_value: Optional[float | str] = None
    unit: Optional[str] = None
    flag: str = "grey"  # green | yellow | red | grey
    deviation_pct: Optional[float] = None
    green_threshold: float = 0.005
    explanation: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)


class AuditFinding(BaseModel):
    """The final, reportable audit finding for one data point."""

    data_point: str = ""
    claimed_value: Optional[float | str] = None
    source_value: Optional[float | str] = None
    unit: Optional[str] = None
    flag: str = "grey"
    deviation_pct: Optional[float] = None
    extraction_confidence: float = 0.0
    mapping_confidence: float = 0.0
    retrieval_confidence: float = 0.0
    review_required: bool = False
    explanation: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)
    claim_text: str = ""
    page: Optional[int] = None
    paragraph_idx: Optional[int] = None
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    source_cell: Optional[str] = None
    review_reason: Optional[str] = None


# ── Ontology models ─────────────────────────────────────────────────────

class AliasDefinition(BaseModel):
    """A human-language alias for a data point."""

    text: str
    language: str = "en"  # "en", "hu", ...
    exact: bool = True  # whether this alias must match exactly


class UnitDefinition(BaseModel):
    """A unit and its synonyms."""

    canonical: str  # e.g. "tCO2e"
    aliases: list[str] = Field(default_factory=list)  # ["tonnes CO2eq", "tonna CO2", ...]


class ValidationRule(BaseModel):
    """A validation threshold rule."""

    green_threshold: float = 0.005  # relative deviation
    yellow_threshold: float = 0.05
    allow_missing_source: bool = False
    source_value_zero_handling: str = "red"  # "red" | "grey"


class DataPointDefinition(BaseModel):
    """A canonical data point with all its metadata."""

    id: str
    display_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    allowed_source_kinds: list[str] = Field(default_factory=list)  # ["pdf", "excel", "csv"]
    period_rules: dict[str, Any] = Field(default_factory=dict)
    aggregation_rule: str = "direct"  # "direct", "sum", "average", "count"
    validation_thresholds: ValidationRule = Field(default_factory=ValidationRule)
    examples: list[str] = Field(default_factory=list)
    source_hints: list[str] = Field(default_factory=list)  # optional filename hints


# ── Report model ────────────────────────────────────────────────────────

class AuditReport(BaseModel):
    """The complete audit report payload."""

    audit_metadata: dict[str, Any] = Field(default_factory=dict)
    document_inventory: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[AuditFinding] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    red_flags: list[dict[str, Any]] = Field(default_factory=list)
    review_required: bool = False