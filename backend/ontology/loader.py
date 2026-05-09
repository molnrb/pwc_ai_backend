"""
Ontology loader — reads data_points.yaml, builds alias/unit indexes,
and provides lookup functions for the normalization and retrieval layers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from models.audit_types import DataPointDefinition, UnitDefinition, ValidationRule

logger = logging.getLogger("atlas.ontology")

ONTOLOGY_PATH = Path(__file__).parent / "data_points.yaml"


class Ontology:
    """In-memory ontology registry built from data_points.yaml.

    Provides:
    - data_point lookup by id
    - alias → data_point_id fuzzy matching
    - unit canonicalization
    - fail-fast validation on load
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or ONTOLOGY_PATH
        self._raw: dict[str, Any] = {}
        self.data_points: dict[str, DataPointDefinition] = {}
        self.unit_registry: dict[str, UnitDefinition] = {}
        # alias → data_point_id (lowercased alias text)
        self._alias_index: dict[str, str] = {}
        # unit alias → canonical unit
        self._unit_index: dict[str, str] = {}

        self._load()

    # ── public API ──────────────────────────────────────────────────

    def get_data_point(self, data_point_id: str) -> Optional[DataPointDefinition]:
        """Return the definition for a canonical data point id."""
        return self.data_points.get(data_point_id)

    def find_by_alias(self, text: str) -> Optional[str]:
        """Return the data_point_id that best matches `text`.

        Returns None if no alias matches with sufficient confidence.
        """
        cleaned = text.strip().lower()
        if cleaned in self._alias_index:
            return self._alias_index[cleaned]

        # Substring match as fallback
        for alias, dp_id in self._alias_index.items():
            if alias in cleaned or cleaned in alias:
                return dp_id

        return None

    def canonical_unit(self, unit_text: str) -> str:
        """Map a unit string to its canonical form.

        e.g. "tonnes CO2eq" → "tCO2e", "szazalek" → "%"
        Returns the input unchanged if no mapping exists.
        """
        cleaned = unit_text.strip().lower()
        return self._unit_index.get(cleaned, unit_text.strip())

    def is_percentage_unit(self, unit_text: str) -> bool:
        """Check whether a unit refers to a percentage."""
        canonical = self.canonical_unit(unit_text)
        return canonical in ("%", "percent", "pct")

    @property
    def all_ids(self) -> list[str]:
        return list(self.data_points.keys())

    # ── loading ─────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Ontology file not found: {self._path}")

        with open(self._path, encoding="utf-8") as fh:
            self._raw = yaml.safe_load(fh) or {}

        self._validate_schema()
        self._build_data_points()
        self._build_unit_registry()
        self._build_indexes()

        logger.info(
            "Ontology loaded: %d data points, %d unit types, %d alias entries",
            len(self.data_points),
            len(self.unit_registry),
            len(self._alias_index),
        )

    def _validate_schema(self) -> None:
        """Fail fast if the YAML structure is invalid."""
        if "data_points" not in self._raw:
            raise ValueError("Ontology YAML must contain a 'data_points' key")
        dp_list = self._raw["data_points"]
        if not isinstance(dp_list, list):
            raise ValueError("'data_points' must be a list")
        for entry in dp_list:
            if not isinstance(entry, dict):
                raise ValueError(f"Each data_point entry must be a dict, got {type(entry)}")
            if "id" not in entry:
                raise ValueError(f"Data point missing 'id': {entry}")

    def _build_data_points(self) -> None:
        for entry in self._raw.get("data_points", []):
            vt = entry.pop("validation_thresholds", {})
            validation = ValidationRule(
                green_threshold=float(vt.get("green_threshold", 0.005)),
                yellow_threshold=float(vt.get("yellow_threshold", 0.05)),
                allow_missing_source=bool(vt.get("allow_missing_source", False)),
                source_value_zero_handling=str(vt.get("source_value_zero_handling", "red")),
            )
            entry["validation_thresholds"] = validation
            dp = DataPointDefinition(**entry)
            self.data_points[dp.id] = dp

    def _build_unit_registry(self) -> None:
        for unit_canonical, info in self._raw.get("unit_registry", {}).items():
            ud = UnitDefinition(
                canonical=info.get("canonical", unit_canonical),
                aliases=info.get("aliases", []),
            )
            self.unit_registry[unit_canonical] = ud

    def _build_indexes(self) -> None:
        # Alias → data_point_id
        for dp in self.data_points.values():
            for alias in dp.aliases:
                key = alias.strip().lower()
                if key:
                    self._alias_index[key] = dp.id

        # Unit alias → canonical
        for ud in self.unit_registry.values():
            for alias in ud.aliases:
                key = alias.strip().lower()
                if key:
                    self._unit_index[key] = ud.canonical
            # The canonical itself is also an entry
            self._unit_index[ud.canonical.strip().lower()] = ud.canonical


# ── Singleton ───────────────────────────────────────────────────────

_ontology_instance: Optional[Ontology] = None


def get_ontology() -> Ontology:
    """Return the singleton Ontology instance, loading on first call."""
    global _ontology_instance
    if _ontology_instance is None:
        _ontology_instance = Ontology()
    return _ontology_instance


def reload_ontology() -> Ontology:
    """Force-reload the ontology (useful after config changes)."""
    global _ontology_instance
    _ontology_instance = Ontology()
    return _ontology_instance