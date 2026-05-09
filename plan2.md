# Generic Document Audit Pipeline Plan

## 1. Goal

Ez a terv nem demo-optimalizalt, hanem egy olyan implementacios blueprint, ami alapjan egy kodolo agent fokozatosan at tudja alakitani a jelenlegi rendszert egy lenyegesen generikusabb audit engine-ne.

Cel:

- A riport PDF-bol szovegbe agyazott allitasokat, tablazatokat es numerikus KPI-jelolteket layouttol fuggetlenebben ki tudja nyerni.
- Az audit source dokumentumokbol PDF, Excel es CSV formatumok eseten ne fix cella- vagy oszlopmappinggel dolgozzon, hanem kereses + normalizalas + confidence alapu evidence matching tortenjen.
- A vegso validacio maradjon determinisztikus, auditalhato, reprodukalhato.
- A deepagents reteg tenylegesen orchestrationre legyen hasznalva, ne hardcoded demo promptokkal fix dokumentumokra.

Nem cel:

- 100%-os, minden lehetseges vilagbeli dokumentumra azonnal mukodo rendszer.
- Olyan one-shot LLM parser, ami bizonyitasi lanc nelkul "megmondja az igazsagot".

Realis cel:

- layout-agnostic
- schema-guided
- confidence-scored
- human-review-friendly


## 2. Current State Summary

A jelenlegi rendszer erossege:

- van mukodo FastAPI backend
- van mukodo React frontend
- van deepagents orchestration irany
- van determinisztikus validator
- van live SSE feed

A jelenlegi rendszer fo korlatai:

- `backend/pipeline.py` fix regexekre es fix source mapre epul
- `backend/tools/excel_tools.py` erosen schema-fuggo
- a PDF parser oldaltextbol dolgozik, nem altalanos document understandinggel
- nincs canonical ontology es synonym layer
- nincs candidate extraction reteg
- nincs confidence scoring
- nincs altalanos evidence retrieval engine
- nincs benchmark corpus es visszamerheto quality gate


## 3. Definition Of Generic

A rendszer akkor tekintheto "generikus v1" allapotunak, ha:

- uj riport PDF eseteben nem csak pontosan ugyanarra a demo layoutre mukodik
- nem fix page/paragraph vagy regex-only extraction tortenik
- uj Excel/CSV source eseten nem csak eloirt sheet/column nevvel tud dolgozni
- source PDF eseten is tud text/table evidence candidate-eket keresni
- minden kinyert claimhez es evidence matchhez confidence tartozik
- alacsony confidence eseten review queue-ba teszi az eredmenyt, nem hallucinacioval zarja le


## 4. Target Architecture

A teljes pipeline 7 retegbol alljon.

### 4.1 Ingestion Layer

Feladata: a nyers dokumentumokbol egy kozos, strukturalt koztes reprezentacio eloallitasa.

Kimeneti modellek:

- `DocumentAsset`
- `DocumentPage`
- `TextBlock`
- `TableBlock`
- `TableCell`
- `SheetTable`
- `CsvTable`

Tamogatott inputok:

- PDF
- XLSX/XLS
- CSV

Kovetelmenyek:

- PDF: page text, blocks, headings, table-like regions, optional OCR fallback
- Excel: workbook, sheets, normalized headers, merged-cell flattening, displayed values
- CSV: delimiter detection, encoding detection, header inference, type inference

### 4.2 Ontology Layer

Feladata: a domain knowledge kulon, konfiguracios adatkent legyen jelen, ne promptokba es hardcoded dictionarykbe legyen szetszorva.

Kimeneti modellek:

- `DataPointDefinition`
- `AliasDefinition`
- `UnitDefinition`
- `ValidationRule`

Tartalom:

- canonical `data_point_id`
- angol + magyar aliasok
- tipikus unitok
- period semantics
- aggregation semantics
- source-hints, ha vannak
- validation tolerances

### 4.3 Candidate Extraction Layer

Feladata: a parser ne vegso truthot gyartson, hanem claim-jelolteket.

Kimeneti modellek:

- `ExtractedCandidate`
- `CandidateMention`
- `CandidateValue`

Minden candidate tartalmazza:

- raw text
- detected value
- detected unit
- period/year
- page/sheet/cell/span
- extraction reasoning
- extraction confidence

### 4.4 Normalization Layer

Feladata: a candidate-eket canonical KPI-kra mapelni.

Kimeneti modellek:

- `NormalizedClaim`

Minden normalized claim tartalmazza:

- `data_point_id`
- normalized value
- normalized unit
- normalized period
- source reference if present
- `mapping_confidence`
- `normalization_notes`

### 4.5 Evidence Retrieval Layer

Feladata: a source dokumentumokban ne fix lookup legyen, hanem candidate evidence kereses.

Kimeneti modellek:

- `EvidenceCandidate`
- `EvidenceMatch`

Minden evidence candidate tartalmazza:

- raw location: file/sheet/page/cell/row/region
- raw value
- detected semantic label
- normalized value/unit/period
- match score
- retrieval notes

### 4.6 Resolution And Validation Layer

Feladata:

- a legjobb evidence match kivalasztasa
- deterministic math validation
- aggregation checks
- conflict detection

Kimeneti modellek:

- `ValidationResult`
- `AuditFinding`

### 4.7 Reporting Layer

Feladata:

- report JSON
- SSE progress payloadok
- frontend-friendly explanation mezok
- review-required lista


## 5. Required Repository Changes

Az alabbi uj vagy modositando file-ok a minimum javasolt szerkezet.

### 5.1 New backend modules

Hozd letre ezeket a modulokat:

- `backend/models/audit_types.py`
- `backend/ontology/data_points.yaml`
- `backend/ontology/loader.py`
- `backend/ingestion/pdf_ingestor.py`
- `backend/ingestion/excel_ingestor.py`
- `backend/ingestion/csv_ingestor.py`
- `backend/ingestion/document_store.py`
- `backend/extraction/candidate_extractor.py`
- `backend/extraction/pdf_candidate_extractor.py`
- `backend/normalization/claim_normalizer.py`
- `backend/retrieval/evidence_retriever.py`
- `backend/retrieval/pdf_evidence_search.py`
- `backend/retrieval/tabular_evidence_search.py`
- `backend/resolution/match_resolver.py`
- `backend/resolution/validation_engine.py`
- `backend/benchmark/fixtures/`
- `backend/tests/` uj tesztfile-ok

### 5.2 Existing files to refactor

- `backend/pipeline.py`
- `backend/orchestrator.py`
- `backend/api.py`
- `backend/subagents/parser_subagent.py`
- `backend/subagents/tracer_subagent.py`
- `backend/tools/pdf_tools.py`
- `backend/tools/excel_tools.py`
- `backend/tools/validator_tool.py`
- `backend/tools/artifact_tools.py`

### 5.3 Frontend files likely affected

- `frontend/src/hooks/useAtlasData.ts`
- `frontend/src/components/audit/AgentFeed.tsx`
- `frontend/src/components/audit/SourceTraceTable.tsx`
- `frontend/src/components/audit/RegulatoryExtracts.tsx`
- `frontend/src/components/dashboard/Dashboard.tsx`
- `frontend/src/services/api.ts`


## 6. Canonical Data Model

Implementalj explicit tipusokat. Ne hasznalj "dict[str, Any]"-t mindenhol.

### 6.1 Core Python dataclasses or Pydantic models

Legyenek legalabb ezek:

```python
class DocumentAsset:
    asset_id: str
    filename: str
    file_type: str
    mime_type: str | None
    role_hint: str | None


class TextBlock:
    page: int | None
    block_id: str
    text: str
    bbox: tuple[float, float, float, float] | None
    heading_level: int | None


class TableCell:
    row_idx: int
    col_idx: int
    row_label: str | None
    col_label: str | None
    raw_value: str | int | float | None
    normalized_value: float | str | None
    unit: str | None
    year: int | None
    cell_ref: str | None


class ExtractedCandidate:
    candidate_id: str
    source_file: str
    source_kind: str
    raw_text: str
    raw_value: str | int | float | None
    raw_unit: str | None
    raw_period: str | None
    location: dict
    extraction_confidence: float
    evidence_hint: str | None


class NormalizedClaim:
    claim_id: str
    data_point_id: str
    value: float | str | None
    unit: str | None
    period: str | None
    source_file_hint: str | None
    extraction_confidence: float
    mapping_confidence: float
    provenance: dict


class EvidenceCandidate:
    evidence_id: str
    data_point_guess: str | None
    file_name: str
    source_kind: str
    location: dict
    raw_value: str | int | float | None
    normalized_value: float | str | None
    unit: str | None
    period: str | None
    retrieval_confidence: float
    match_features: dict


class AuditFinding:
    data_point: str
    claimed_value: float | str | None
    source_value: float | str | None
    unit: str | None
    flag: str
    deviation_pct: float | None
    extraction_confidence: float
    mapping_confidence: float
    retrieval_confidence: float
    review_required: bool
    explanation: str
    provenance: dict
```

Kritikus elv:

- a nyers es normalizalt ertek legyen kulon tarolva
- a confidence-ek legyenek kulon dimenziokban
- a provenance mindig maradjon meg


## 7. Ontology Design

### 7.1 Create `backend/ontology/data_points.yaml`

Minden data point definicio tartalmazza:

- `id`
- `display_name`
- `aliases`
- `units`
- `allowed_source_kinds`
- `period_rules`
- `aggregation_rule`
- `validation_thresholds`
- `examples`

Pelda szerkezet:

```yaml
data_points:
    - id: renewable_pct
        display_name: Renewable energy share
        aliases:
            - renewable energy share
            - renewable share
            - share of renewable energy
            - megujulo arany
            - megujulo energia aranya
        units: ["%", "percent", "pct"]
        allowed_source_kinds: ["pdf", "excel", "csv"]
        period_rules:
            prefer_current_reporting_year: true
        aggregation_rule: direct
        validation_thresholds:
            green: 0.005
            yellow: 0.05
        examples:
            - "The share of renewable energy in total energy consumption was 67%."
```

### 7.2 Loader requirements

`backend/ontology/loader.py` feladata:

- YAML betoltese
- alias index epites
- unit synonym index epites
- invalid schema fail-fast ellenorzese


## 8. Ingestion Layer Tasks

### 8.1 PDF ingestion

Implementald a `backend/ingestion/pdf_ingestor.py` modult.

Minimum capability:

- oldalankenti text blocks
- heading-like blocks felismerese
- table-like text region detection
- oldalszamu + bounding box provenance
- scanned PDF eseten optional OCR fallback hook

Ha nincs most azonnal OCR csomag, akkor a kod ugy keszuljon, hogy kesobb bekotheto legyen.

Szukseges API:

```python
def ingest_pdf(pdf_path: Path) -> list[TextBlock | TableBlock]:
    ...
```

### 8.2 Excel ingestion

Implementald a `backend/ingestion/excel_ingestor.py` modult.

Minimum capability:

- sheetenkenti DataFrame betoltes
- merged cell normalization, amennyire pandas engedi
- header-row candidate detektalas
- multi-row header collapse heuristic
- displayed values + stringified values
- year-like oszlopok detektalasa

Szukseges API:

```python
def ingest_excel(path: Path) -> list[SheetTable]:
    ...
```

### 8.3 CSV ingestion

Implementald a `backend/ingestion/csv_ingestor.py` modult.

Minimum capability:

- encoding detection
- delimiter inference
- optional no-header handling
- semantic type inference oszloponkent

Szukseges API:

```python
def ingest_csv(path: Path) -> CsvTable:
    ...
```


## 9. Candidate Extraction Tasks

### 9.1 Replace one-shot claim extraction

A mostani `pipeline.py` regex extraction maradjon fallback, de ne legyen a fo parser.

Implementalj `backend/extraction/candidate_extractor.py` modult, ami legalabb ket strategiat tamogat:

- deterministic candidate pass
- LLM-assisted candidate pass

Feladat:

- a parser ne csak a 8 ismert claimre latszon ra regexszel
- barmely numerikus, KPI-szeru allitast osszegyujt candidate-kent
- utana normalizer dontse el, hogy canonical KPI-e vagy sem

### 9.2 PDF candidate extraction

Implementald a `backend/extraction/pdf_candidate_extractor.py` modult.

Lepesek:

1. blokk-level numerikus span keresese
2. mondat- vagy paragraph-szintu context kepzese
3. unit detection
4. year/period detection
5. source reference detection
6. confidence score kepzes

Candidate confidence faktorok:

- van-e szam
- van-e unit
- van-e domain-szeru alias
- van-e forras hivatkozas
- heading/table context erositi-e


## 10. Claim Normalization Tasks

Implementald a `backend/normalization/claim_normalizer.py` modult.

Feladata:

- alias matching ontology alapjan
- unit normalization
- year normalization
- percent/string/number normalization
- current-year vs prior-year disambiguation
- candidate deduplication

Kulonosen fontos:

- ugyanaz a KPI tobbszor is szerepelhet egy riportban
- prior-year baseline es current-year actual gyakran egy mondatban van
- a normalizernek ezt szet kell tudnia valasztani

Normalizalas utan minden claim kapjon:

- `mapping_confidence`
- `canonical_reason`
- `dedup_group`


## 11. Evidence Retrieval Tasks

### 11.1 General requirement

Az evidence retrieval ne fix sheet/cell lookup legyen.

Ehelyett legyen ranked retrieval:

- semantic label match
- unit match
- period match
- numerical proximity
- row/column context match
- file role match

### 11.2 Tabular evidence search

Implementald a `backend/retrieval/tabular_evidence_search.py` modult.

Excel/CSV search strategy:

1. header alias match
2. row label alias match
3. year column preference
4. total row preference, ha aggregate KPI
5. source value normalization
6. top-k candidate visszaadasa score-ral

Szukseges API:

```python
def find_tabular_evidence(claim: NormalizedClaim, assets: list[SheetTable | CsvTable]) -> list[EvidenceCandidate]:
    ...
```

### 11.3 PDF evidence search

Implementald a `backend/retrieval/pdf_evidence_search.py` modult.

Feladata:

- source PDF-ekben text/table evidence candidate-ek keresese
- numeric + semantic + unit + period kombinacios search

Szukseges API:

```python
def find_pdf_evidence(claim: NormalizedClaim, pdf_blocks: list[TextBlock | TableBlock]) -> list[EvidenceCandidate]:
    ...
```

### 11.4 Unified evidence retriever

Implementald a `backend/retrieval/evidence_retriever.py` modult.

Feladata:

- megfelelo search strategiak hivasa fajltipus szerint
- candidate-ek egyesitese
- top-k ranked lista visszaadasa


## 12. Resolution And Deterministic Validation Tasks

### 12.1 Match resolver

Implementald a `backend/resolution/match_resolver.py` modult.

Feladata:

- top-k evidence candidate-ek kozul a legjobb valasztasa
- tie-handling
- review-required, ha nincs eleg jo match

Javasolt szabaly:

- ha top score < threshold, ne vallaljon eros allitast
- inkabb `grey` + review

### 12.2 Validation engine

Implementald a `backend/resolution/validation_engine.py` modult.

Ez hasznalja a `validator_tool.py` determinisztikus logikajat, de bovitve:

- direct comparison
- computed aggregation checks
- subtotal/total consistency checks
- prior-year vs current-year mismatch detection
- multi-evidence conflict detection

### 12.3 Preserve deterministic truth layer

LLM nem szamol vegleges deviationt.

Mindig Python szamolja:

- normalization utan
- resolved evidence alapjan
- explicit tolerance rule alapjan


## 13. Deepagents Refactor Tasks

### 13.1 Parser subagent role change

`backend/subagents/parser_subagent.py`

Jelenlegi szerep:

- final claim extraction

Uj szerep:

- candidate extraction
- provenance-rich output
- top-level classification hints

Parser output ne vegleges finding legyen, hanem `ExtractedCandidate[]`.

### 13.2 Tracer subagent role change

`backend/subagents/tracer_subagent.py`

Jelenlegi szerep:

- fixen keresi a source ertekeket

Uj szerep:

- evidence candidate retrieval
- retrieval explanation
- confidence-rich matching hints

Tracer output ne vegleges audit finding legyen, hanem `EvidenceCandidate[]` vagy ranked resolution input.

### 13.3 Orchestrator role change

`backend/orchestrator.py`

Uj sorrend:

1. ingest documents
2. extract candidates
3. normalize claims
4. retrieve evidence candidates
5. resolve best matches
6. run deterministic validation
7. build report

Az orchestrator SSE-ben kulon statusokat kuldjon ezekhez a fazisokhoz.


## 14. Backend Pipeline Refactor Tasks

### 14.1 Slim down `backend/pipeline.py`

A `pipeline.py` legyen coordinator/fallback, ne minden logika egy fileban legyen.

Szetszervezendo reszek:

- extraction logic
- normalization logic
- source retrieval logic
- validation logic
- report assembly segedfuggvenyek

### 14.2 Keep compatibility wrapper

Addig, amig a teljes refaktor kesz nincs, a `run_full_audit()` maradjon publikus entry point.

Belso implementacio fokozatosan valthat az uj retegekre.


## 15. Tooling Tasks

### 15.1 Refactor `backend/tools/pdf_tools.py`

Uj toolok legyenek:

- `extract_pdf_blocks(file_name)`
- `extract_pdf_tables(file_name)`
- `search_pdf_numeric_context(file_name, query)`

### 15.2 Refactor `backend/tools/excel_tools.py`

Uj toolok legyenek:

- `list_workbook_sheets(filename)`
- `profile_sheet(filename, sheet)`
- `search_sheet_labels(filename, sheet, query)`
- `find_numeric_candidates(filename, sheet, data_point_hint, year_hint)`

### 15.3 Add `backend/tools/csv_tools.py`

Uj toolok legyenek:

- `profile_csv(filename)`
- `search_csv_columns(filename, query)`
- `find_csv_numeric_candidates(filename, data_point_hint, period_hint)`

### 15.4 Keep validator strict but tolerant on inputs

`backend/tools/validator_tool.py`

Maradjon deterministic, de input oldalon kezelje:

- `%`
- comma separated numbers
- stringified numerics
- locale variant numeric forms


## 16. API Contract Changes

### 16.1 Extend report payload

`backend/api.py` es `frontend/src/services/api.ts`

Az `AuditFinding` payload keruljon kibovitesre:

- `extraction_confidence`
- `mapping_confidence`
- `retrieval_confidence`
- `evidence_confidence`
- `provenance`
- `review_reason`

### 16.2 Add debug endpoints optionally

Hasznos uj endpointok:

- `GET /claims` -> normalized claims
- `GET /candidates` -> raw extracted candidates
- `GET /evidence-candidates` -> retrieval candidates

Ezek demo/dev alatt hasznosak, productionben optional feature flaggel menjenek.


## 17. Frontend Tasks

### 17.1 Show real provenance and confidence

`SourceTraceTable.tsx` es kapcsolodo komponensek jelenitsenek meg:

- confidence badge-eket
- raw source locationt
- review-required okot
- "matched by" rovid indoklast

### 17.2 Show pipeline identity explicitly

Az Agent Feed vagy status bar jelenitse meg:

- `pipeline`
- `parser_mode`
- `documents_processed`
- `claims_extracted`
- `claims_review_required`

### 17.3 Add review queue section

Kulon listazni kell azokat a findingeket, ahol:

- low extraction confidence
- low mapping confidence
- low retrieval confidence
- multiple conflicting evidence candidate
- missing source


## 18. Benchmark And Test Strategy

### 18.1 Create benchmark corpus

Hozz letre legalabb 3 szintet:

- `benchmark/basic/`
- `benchmark/medium/`
- `benchmark/hard/`

Minden szinten legyen:

- 2-3 eltero riport PDF
- 2-3 eltero Excel source layout
- 1-2 eltero CSV header schema
- legalabb 1 source PDF

### 18.2 Ground truth format

Legyen ground truth JSON:

- expected claims
- expected canonical KPI mapping
- expected source match
- expected validation flag

### 18.3 Required tests

Implementalando tesztek:

- ontology loader tests
- PDF ingestion tests
- Excel ingestion tests
- CSV ingestion tests
- candidate extraction tests
- claim normalization tests
- evidence retrieval ranking tests
- deterministic validator tests
- API integration tests

### 18.4 Quality gates

Generikus v1 minimum target:

- claim recall >= 0.85 basic corpuson
- claim precision >= 0.80 basic corpuson
- canonical mapping accuracy >= 0.85
- evidence top-1 match accuracy >= 0.75
- final flag accuracy >= 0.85 basic corpuson


## 19. Step-By-Step Execution Plan For Coding Agent

Ez a konkret, ajanlott implementacios sorrend.

### Phase 0 - Stabilization

Feladatok:

1. irj repo snapshotot es technikai baseline-t
2. tedd zoldre a mostani backend smoke testet
3. dokumentald a jelenlegi public API schema-t

Definition of done:

- `/health`, `/audit`, `/stream`, `/report` stabil
- deepagents path ellenorizve

### Phase 1 - Ontology And Types

Feladatok:

1. hozd letre `backend/models/audit_types.py`
2. hozd letre `backend/ontology/data_points.yaml`
3. hozd letre `backend/ontology/loader.py`
4. ird at a jelenlegi hardcoded source/data point strukturakat ontology alapu betoltesre, ahol lehet

Definition of done:

- canonical data point definiciok YAML-ben vannak
- ontologia fail-fast validalhato
- unit tests keszek ra

### Phase 2 - Ingestion Layer

Feladatok:

1. implementald `pdf_ingestor.py`
2. implementald `excel_ingestor.py`
3. implementald `csv_ingestor.py`
4. implementald `document_store.py`

Definition of done:

- barmely input fajl betoltheto kozos modellekbe
- provenance nem veszik el

### Phase 3 - Candidate Extraction

Feladatok:

1. implementald a generic candidate extractorokat
2. vezess be candidate artifact formatot a workspace-ban
3. a parser subagent outputja mar candidate listat irjon

Definition of done:

- parser mar nem vegleges findinget gyart
- ugyanazon PDF-bol tobbfele layout eseten is jonnek candidate-ek

### Phase 4 - Normalization

Feladatok:

1. implementald `claim_normalizer.py`
2. oldd meg alias + unit + period mappinget
3. vezesd be dedup/group logikat

Definition of done:

- candidate -> normalized claim atalakitasi tesztek mennek

### Phase 5 - Evidence Retrieval

Feladatok:

1. implementald tabular evidence searcht
2. implementald PDF evidence searcht
3. implementald unified evidence retrievert

Definition of done:

- source nem fix cella alapu lookupkal megy
- top-k evidence candidate lista eloall

### Phase 6 - Resolution And Validation

Feladatok:

1. implementald match resolver logikat
2. bovitett deterministic validation engine
3. review-required szabalyok

Definition of done:

- minden findinghez confidence + explanation van
- alacsony score eseten review queue megy

### Phase 7 - Orchestrator Integration

Feladatok:

1. ird at `orchestrator.py`-t az uj pipeline fazisokra
2. parser/tracer subagent promptokat igazitsd candidate/retrieval modra
3. SSE taxonomy bovites

Definition of done:

- live run alatt latszik a teljes generikus pipeline fazisonkent

### Phase 8 - Frontend Integration

Feladatok:

1. bovitsd a report schema-t
2. confidence es provenance mezok UI megjelenitese
3. review queue panel

Definition of done:

- a frontend vilagosan mutatja, mi biztos es mi review-required

### Phase 9 - Benchmark Hardening

Feladatok:

1. benchmark corpus feltoltese
2. meresek automatizalasa
3. precision/recall riportok
4. top regressziok javitasa

Definition of done:

- van ismetelheto benchmark futas
- a generic v1 quality gate teljesul a basic corpuson


## 20. Required Workspace Artifacts

Az agent hozzon letre uj artifact konyvtarakat a `backend/workspace/` alatt:

- `workspace/ingested/`
- `workspace/candidates/`
- `workspace/normalized_claims/`
- `workspace/evidence_candidates/`
- `workspace/final_findings/`

Cel:

- minden fazis outputja inspectalhato legyen
- regression debugging egyszerubb legyen
- deepagents reszeredmenyek latszodjanak


## 21. Migration Rules

Kodolo agent szamara kotelezo szabalyok:

1. ne egy nagy bang refaktor legyen
2. minden fazis utan legyen executable validation
3. a jelenlegi demo flow lehetoseg szerint ne torjon el
4. a deterministic validator mindig maradjon elkulonitett reteg
5. ahol nincs eleg confidence, ott review-ra kell allni, nem guesselni
6. a public `/report` contractot csak kontrollaltan bovitse, ne torje el a frontendet


## 22. Concrete Acceptance Criteria

Ezt tekintsd a projekt "done" definiciojanak.

### Backend acceptance

- ismeretlenebb layoutu PDF-bol is jonnek candidate-ek
- Excel/CSV source nem fix sheet/cell mappinggel megy
- source PDF is kezelheto evidence-kent
- report tartalmaz confidence-eket es provenance-t
- `/report` metadata egyertelmuen mutatja a pipeline modot

### Frontend acceptance

- nem stale evidence latszik uj run elott
- feed mutatja a pipeline fazisokat
- findingeknel latszik confidence + source provenance
- review-required findingek kulon kiemeltek

### Quality acceptance

- benchmark basic corpus quality gate teljesul
- regresszio tesztek mennek
- a live deepagents run nem esik vissza csendben a regi hardcoded viselkedesre


## 23. Validation Commands

Minden nagyobb fazis utan futtasd legalabb ezeket.

Backend smoke:

```bash
cd backend && /Users/balazsmolnar/Documents/pwc_ai_backend/.venv/bin/python - <<'PY'
from orchestrator import run_live_llm_audit
report = run_live_llm_audit()
print(report['audit_metadata'])
print(len(report['findings']))
PY
```

API validation:

```bash
curl -sf http://127.0.0.1:8000/health | jq
curl -sf -X POST http://127.0.0.1:8000/reset | jq
curl -sf -X POST http://127.0.0.1:8000/audit | jq
curl -sf http://127.0.0.1:8000/report | jq '.audit_metadata'
```

Frontend validation:

```bash
cd frontend && npm run build
```

Benchmark validation:

```bash
cd backend && /Users/balazsmolnar/Documents/pwc_ai_backend/.venv/bin/python -m pytest
```


## 24. Implementation Notes For Agent

Ha ezt egy masik coding agent hajtja vegre, ezek legyenek a munkaszabalyai:

- mindig a legkisebb mukodo lepest implementalja
- minden uj modult tipusokkal es tesztekkel kezdjen
- a pipeline-ot koztes artifactokkal epitse, ne monolitikusan
- kerulje a tul korai prompt engineeringet ott, ahol deterministic heuristic eleg
- csak ott hasznaljon LLM-et, ahol tenyleg dokumentum-megertes kell
- ne vegyen ki meglvo deterministic fallbacket addig, amig az uj reteg nem validalt


## 25. First Concrete Work Package

Ha az agent azonnal el akar kezdeni dolgozni, ez legyen az elso sprint:

1. `backend/models/audit_types.py`
2. `backend/ontology/data_points.yaml`
3. `backend/ontology/loader.py`
4. `backend/ingestion/excel_ingestor.py`
5. `backend/ingestion/csv_ingestor.py`
6. `backend/retrieval/tabular_evidence_search.py`
7. `backend/tools/excel_tools.py` es `backend/tools/csv_tools.py` generikus search API-ra atirasa
8. unit tests ezekre

Ennek azert ez legyen az elso csomagja, mert a legnagyobb azonnali minosegi ugrast a source oldali generikussag fogja adni.


## 26. Final Strategic Guidance

Ha kompromisszum kell a sebesseg es a minoseg kozott, ezt a sorrendet tartsd:

1. provenance
2. deterministic validation
3. generic source retrieval
4. ontology-driven normalization
5. generic PDF candidate extraction
6. UX confidence/review layer

Azert ez a helyes sorrend, mert a rendszer auditor-szeruen csak akkor lesz hiteles, ha eloszor meg tudja mutatni, honnan jott egy ertek, es csak utana probal minel okosabban generalizalni.
