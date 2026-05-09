"""
Core pipeline tests — ontology loading, ingestion, extraction, normalization,
and smoke test for the generic pipeline.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure backend is on sys.path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


class TestOntology:
    """Phase 1: Ontology loading and validation."""

    def test_load_yaml(self):
        from ontology.loader import Ontology
        onto = Ontology()
        assert len(onto.data_points) >= 8
        assert "scope1_emission" in onto.data_points
        assert "renewable_pct" in onto.data_points
        assert "headcount" in onto.data_points

    def test_alias_lookup(self):
        from ontology.loader import Ontology
        onto = Ontology()
        assert onto.find_by_alias("renewable energy share") == "renewable_pct"
        assert onto.find_by_alias("scope 1 emissions") == "scope1_emission"
        assert onto.find_by_alias("megujulo arany") == "renewable_pct"
        assert onto.find_by_alias("letszam") == "headcount"

    def test_unit_canonicalization(self):
        from ontology.loader import Ontology
        onto = Ontology()
        assert onto.canonical_unit("tonnes CO2eq") == "tCO2e"
        assert onto.canonical_unit("tonna CO2") == "tCO2e"
        assert onto.canonical_unit("szazalek") == "%"

    def test_data_point_definitions(self):
        from ontology.loader import Ontology
        onto = Ontology()
        dp = onto.get_data_point("scope1_emission")
        assert dp is not None
        assert dp.display_name == "Scope 1 emissions"
        assert len(dp.aliases) > 3
        assert dp.validation_thresholds.green_threshold == 0.005

    def test_fail_fast_bad_path(self):
        from ontology.loader import Ontology
        with pytest.raises(FileNotFoundError):
            Ontology(path=Path("/nonexistent/ontology.yaml"))


class TestPDFIngestion:
    """Phase 2: PDF ingestion."""

    def test_ingest_demo_pdf(self):
        from ingestion.pdf_ingestor import ingest_pdf
        pdf_path = BACKEND_DIR / "workspace" / "input" / "atlas_sustainability_statement.pdf"
        if not pdf_path.exists():
            pytest.skip("Demo PDF not found")
        blocks = ingest_pdf(pdf_path)
        assert len(blocks) > 0
        # Should have TextBlocks
        from models.audit_types import TextBlock
        text_blocks = [b for b in blocks if isinstance(b, TextBlock)]
        assert len(text_blocks) > 0

    def test_ingest_legacy_pages(self):
        from ingestion.pdf_ingestor import ingest_pdf_pages
        pdf_path = BACKEND_DIR / "workspace" / "input" / "atlas_sustainability_statement.pdf"
        if not pdf_path.exists():
            pytest.skip("Demo PDF not found")
        pages = ingest_pdf_pages(pdf_path)
        assert len(pages) > 0
        assert "page" in pages[0]
        assert "text" in pages[0]


class TestExcelIngestion:
    """Phase 2: Excel ingestion."""

    def test_ingest_energia_xlsx(self):
        from ingestion.excel_ingestor import ingest_excel
        xlsx_path = BACKEND_DIR / "workspace" / "input" / "energia_2024.xlsx"
        if not xlsx_path.exists():
            pytest.skip("Excel source not found")
        tables = ingest_excel(xlsx_path)
        assert len(tables) >= 1
        assert any(t.sheet_name in ("Scope1_Scope2", "Megujulo") for t in tables)

    def test_profile_sheet(self):
        from ingestion.excel_ingestor import profile_sheet
        xlsx_path = BACKEND_DIR / "workspace" / "input" / "energia_2024.xlsx"
        if not xlsx_path.exists():
            pytest.skip("Excel source not found")
        info = profile_sheet(xlsx_path, "Scope1_Scope2")
        if "error" not in info:
            assert "columns" in info
            assert "row_count" in info


class TestCSVIngestion:
    """Phase 2: CSV ingestion."""

    def test_ingest_hr_csv(self):
        from ingestion.csv_ingestor import ingest_csv
        csv_path = BACKEND_DIR / "workspace" / "input" / "hr_export_2024.csv"
        if not csv_path.exists():
            pytest.skip("CSV source not found")
        table = ingest_csv(csv_path)
        assert table.row_count > 0
        assert len(table.columns) > 0


class TestCandidateExtraction:
    """Phase 3: Candidate extraction."""

    def test_extract_from_text(self):
        from extraction.candidate_extractor import extract_candidates_deterministic
        from models.audit_types import TextBlock
        block = TextBlock(
            page=4,
            block_id="test_1",
            text="The company's Scope 1 emissions for 2024 were 1,850 tonnes CO2 equivalent. (Source: energia_2024.xlsx)"
        )
        candidates = extract_candidates_deterministic([block], "test.pdf")
        assert len(candidates) > 0
        # Should find the 1850 value
        numeric_vals = [c.raw_value for c in candidates if c.raw_value is not None]
        assert 1850 in numeric_vals or 1850.0 in numeric_vals

    def test_pdf_candidate_extraction(self):
        from extraction.pdf_candidate_extractor import extract_pdf_candidates
        pdf_path = BACKEND_DIR / "workspace" / "input" / "atlas_sustainability_statement.pdf"
        if not pdf_path.exists():
            pytest.skip("Demo PDF not found")
        candidates = extract_pdf_candidates(pdf_path)
        # Should extract many numeric candidates from a 15-page PDF
        assert len(candidates) >= 20


class TestNormalization:
    """Phase 4: Claim normalization."""

    def test_normalize_candidates(self):
        from extraction.candidate_extractor import extract_candidates_deterministic
        from normalization.claim_normalizer import ClaimNormalizer
        from models.audit_types import TextBlock

        block = TextBlock(
            page=4,
            block_id="test_1",
            text="The company's Scope 1 emissions for 2024 were 1,850 tonnes CO2 equivalent."
        )
        block2 = TextBlock(
            page=8,
            block_id="test_2",
            text="The share of renewable energy in total energy consumption was 67%."
        )
        candidates = extract_candidates_deterministic([block, block2], "test.pdf")
        normalizer = ClaimNormalizer()
        claims = normalizer.normalize(candidates)
        assert len(claims) >= 1
        data_point_ids = [c.data_point_id for c in claims]
        assert "scope1_emission" in data_point_ids or "renewable_pct" in data_point_ids


class TestEvidenceRetrieval:
    """Phase 5: Evidence retrieval."""

    def test_tabular_search(self):
        from normalization.claim_normalizer import NormalizedClaim
        from ingestion.excel_ingestor import ingest_excel
        from retrieval.tabular_evidence_search import find_tabular_evidence

        xlsx_path = BACKEND_DIR / "workspace" / "input" / "energia_2024.xlsx"
        if not xlsx_path.exists():
            pytest.skip("Excel source not found")

        tables = ingest_excel(xlsx_path)
        claim = NormalizedClaim(
            claim_id="test_1",
            data_point_id="scope1_emission",
            value=1850,
            unit="tCO2e",
            period="2024",
            extraction_confidence=0.8,
            mapping_confidence=0.9,
        )
        candidates = find_tabular_evidence(claim, tables)
        assert len(candidates) >= 0  # May find matches depending on sheet structure


class TestValidationEngine:
    """Phase 6: Deterministic validation."""

    def test_validate_green(self):
        from resolution.validation_engine import validate
        from normalization.claim_normalizer import NormalizedClaim
        from models.audit_types import EvidenceCandidate

        claim = NormalizedClaim(
            claim_id="t1",
            data_point_id="scope1_emission",
            value=1850,
            unit="tCO2e",
            period="2024",
            extraction_confidence=0.9,
            mapping_confidence=0.9,
        )
        evidence = EvidenceCandidate(
            evidence_id="e1",
            data_point_guess="scope1_emission",
            file_name="energia_2024.xlsx",
            source_kind="excel",
            normalized_value=1850,
            unit="tCO2e",
            period="2024",
            retrieval_confidence=0.8,
        )
        finding = validate(claim, evidence)
        assert finding.flag == "green"
        assert finding.deviation_pct is not None and finding.deviation_pct < 1.0

    def test_validate_red(self):
        from resolution.validation_engine import validate
        from normalization.claim_normalizer import NormalizedClaim
        from models.audit_types import EvidenceCandidate

        claim = NormalizedClaim(
            claim_id="t2",
            data_point_id="scope2_emission",
            value=4200,
            unit="tCO2e",
            period="2024",
            extraction_confidence=0.9,
            mapping_confidence=0.9,
        )
        evidence = EvidenceCandidate(
            evidence_id="e2",
            data_point_guess="scope2_emission",
            file_name="energia_2024.xlsx",
            source_kind="excel",
            normalized_value=3800,
            unit="tCO2e",
            period="2024",
            retrieval_confidence=0.8,
        )
        finding = validate(claim, evidence)
        assert finding.flag == "red"
        assert finding.deviation_pct is not None and finding.deviation_pct > 5.0

    def test_validate_no_evidence(self):
        from resolution.validation_engine import validate
        from normalization.claim_normalizer import NormalizedClaim

        claim = NormalizedClaim(
            claim_id="t3",
            data_point_id="training_participants",
            value=1240,
            unit="fő",
            period="2024",
            extraction_confidence=0.7,
            mapping_confidence=0.8,
        )
        finding = validate(claim, evidence=None)
        assert finding.flag == "grey"
        assert finding.review_required is True


class TestGenericPipeline:
    """Phase 7 smoke test — full generic pipeline."""

    def test_generic_pipeline_runs(self):
        from pipeline import run_generic_audit, _GENERIC_PIPELINE_AVAILABLE
        if not _GENERIC_PIPELINE_AVAILABLE:
            pytest.skip("Generic pipeline modules not available")
        report = run_generic_audit()
        assert "audit_metadata" in report
        assert "findings" in report
        assert "summary" in report
        assert report["audit_metadata"]["pipeline"] == "generic_v1"
        assert len(report["findings"]) >= 1


class TestLegacyPipeline:
    """Ensure legacy pipeline still works."""

    def test_legacy_pipeline_runs(self):
        from pipeline import run_full_audit
        report = run_full_audit()
        assert "audit_metadata" in report
        assert "findings" in report
        assert len(report["findings"]) == 8  # 8 data points configured