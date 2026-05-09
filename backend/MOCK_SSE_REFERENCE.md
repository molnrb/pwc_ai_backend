# Mock SSE Reference

This file documents the expected `/stream` output for the current mock run when all of the following are true:

- `MOCK_MODE=true`
- `ATLAS_INPUT_SUBDIR=input2`
- the manifest is [workspace/input2/audit_index.json](workspace/input2/audit_index.json)

The backend emits standard Server-Sent Events in this wire format:

```text
event: <event_name>
data: <json_payload>

```

Example:

```text
event: phase
data: {"phase":"catalog_inputs","message":"Cataloging mock input documents..."}

```

Notes:

- The frontend adds display timestamps itself. Timestamps shown in the feed are not part of the SSE payload.
- The current mock stream emits 42 events from start to finish for `input2`.
- The final report is written before the last `complete` event.

## Expected event order for `input2`

1. `status`
   `message: "Atlas CSRD Audit Engine initializing mock pipeline from audit_index.json..."`
2. `phase`
   `phase: "catalog_inputs"`
   `message: "Cataloging mock input documents..."`
3. `file_found`
   `filename: "GHG_calculation_workbook.xlsx"`
4. `file_found`
   `filename: "audit_index.json"`
5. `file_found`
   `filename: "carbon_credits_register.xlsx"`
6. `file_found`
   `filename: "electricity_invoice_Berlin_Jul2025.pdf"`
7. `file_found`
   `filename: "siemens_E1_excerpt.pdf"`
8. `file_found`
   `filename: "utility_bills_FY2025.csv"`
9. `phase`
   `phase: "catalog_inputs"`
   `message: "Found 6 mock input files"`
10. `phase`
    `phase: "build_audit_plan"`
    `message: "Loading scripted audit plan from audit_index.json..."`
11. `todo`
    `total: 5`
    `items:`
    - `Reproduce expected finding 1: Scope 2 market-based total: PDF p.34 reports 47.0 ktCO2e, Excel Sheet3 sums to 44.8 ktCO2e (~4.7% delta)`
    - `Reproduce expected finding 2: Total Scope 1+2 market-based: PDF p.33 reports 359 ktCO2e, Excel Reconciliation reports 335 ktCO2e`
    - `Reproduce expected finding 3: EU Taxonomy revenue alignment cited as both 52.0% (Siemens w/o SHS, p.19) and 29.3% (full Siemens, p.19) - different scopes, requires human review`
    - `Reproduce expected finding 4: Scope3_categories row 3.7 (Employee Commuting): calculation_method, input_data_source, and emissions_ktCO2e are empty in Excel; PDF p.33 reports 177 ktCO2e`
    - `Reproduce expected finding 5: carbon_credits_register: Plan Vivo Standard rows have empty certificate_url field; cancellation cannot be independently verified`
12. `phase`
    `phase: "build_audit_plan"`
    `message: "Mock plan ready - 5 expected findings scripted from the manifest"`
13. `phase`
    `phase: "parse_claims"`
    `message: "Parser loading scripted checks from audit_index.json..."`
14. `agent_start`
    `agent: "Parser"`
    `task: "Loading scripted expected findings from audit_index.json"`
15. `agent_progress`
    `agent: "Parser"`
    `message: "Anchored mock check 1/5: eu_taxonomy_revenue_alignment_scope_mismatch"`
16. `agent_progress`
    `agent: "Parser"`
    `message: "Anchored mock check 2/5: scope12_market_based_total"`
17. `agent_progress`
    `agent: "Parser"`
    `message: "Anchored mock check 3/5: scope3_category7_employee_commuting"`
18. `agent_progress`
    `agent: "Parser"`
    `message: "Anchored mock check 4/5: scope2_market_based_total"`
19. `agent_progress`
    `agent: "Parser"`
    `message: "Anchored mock check 5/5: carbon_credits_certificate_url"`
20. `agent_done`
    `agent: "Parser"`
    `claims_found: 5`
    `message: "Loaded 5 scripted findings from audit_index.json"`
21. `phase`
    `phase: "trace_sources"`
    `message: "Tracer replaying expected evidence outcomes..."`
22. `agent_start`
    `agent: "Tracer"`
    `task: "Replaying 5 expected findings from the manifest"`
23. `agent_progress`
    `agent: "Tracer"`
    `message: "Checking eu_taxonomy_revenue_alignment_scope_mismatch against siemens_E1_excerpt.pdf (1/5)"`
24. `finding`
    `agent: "Tracer"`
    `data_point: "eu_taxonomy_revenue_alignment_scope_mismatch"`
    `message: "EU Taxonomy revenue alignment cited as both 52.0% (Siemens w/o SHS, p.19) and 29.3% (full Siemens, p.19) - different scopes, requires human review"`
25. `agent_progress`
    `agent: "Tracer"`
    `message: "Checking scope12_market_based_total against GHG_calculation_workbook.xlsx (2/5)"`
26. `finding`
    `agent: "Tracer"`
    `data_point: "scope12_market_based_total"`
    `message: "Total Scope 1+2 market-based: PDF p.33 reports 359 ktCO2e, Excel Reconciliation reports 335 ktCO2e"`
27. `agent_progress`
    `agent: "Tracer"`
    `message: "Checking scope3_category7_employee_commuting against GHG_calculation_workbook.xlsx (3/5)"`
28. `finding`
    `agent: "Tracer"`
    `data_point: "scope3_category7_employee_commuting"`
    `message: "Scope3_categories row 3.7 (Employee Commuting): calculation_method, input_data_source, and emissions_ktCO2e are empty in Excel; PDF p.33 reports 177 ktCO2e"`
29. `agent_progress`
    `agent: "Tracer"`
    `message: "Checking scope2_market_based_total against GHG_calculation_workbook.xlsx (4/5)"`
30. `finding`
    `agent: "Tracer"`
    `data_point: "scope2_market_based_total"`
    `message: "Scope 2 market-based total: PDF p.34 reports 47.0 ktCO2e, Excel Sheet3 sums to 44.8 ktCO2e (~4.7% delta)"`
31. `agent_progress`
    `agent: "Tracer"`
    `message: "Checking carbon_credits_certificate_url against carbon_credits_register.xlsx (5/5)"`
32. `finding`
    `agent: "Tracer"`
    `data_point: "carbon_credits_certificate_url"`
    `message: "carbon_credits_register: Plan Vivo Standard rows have empty certificate_url field; cancellation cannot be independently verified"`
33. `agent_done`
    `agent: "Tracer"`
    `findings: 5`
    `sources_resolved: 5`
    `message: "Replayed 5 expected findings from audit_index.json"`
34. `phase`
    `phase: "validate_findings"`
    `message: "Validator confirming the scripted perfect mock result..."`
35. `agent_start`
    `agent: "Validator"`
    `task: "Summarizing scripted findings for the mock report"`
36. `agent_progress`
    `agent: "Validator"`
    `green: 0`
    `yellow: 1`
    `red: 2`
    `grey: 2`
37. `agent_done`
    `agent: "Validator"`
    `message: "Validation complete - 0 green, 1 yellow, 2 red, 2 grey"`
38. `phase`
    `phase: "build_report"`
    `message: "Reporter assembling the perfect mock evidence package..."`
39. `agent_start`
    `agent: "Reporter"`
    `task: "Writing mock audit report and evidence package"`
40. `agent_done`
    `agent: "Reporter"`
    `message: "Mock evidence package saved to audit_report.json"`
41. `phase`
    `phase: "build_report"`
    `message: "Mock report complete - 5 expected findings reproduced from audit_index.json"`
42. `complete`
    `pipeline: "mock"`
    `parser_mode: "scripted-manifest"`
    `total_findings: 5`
    `review_required: true`
    `summary:`
    - `red_count: 2`
    - `yellow_count: 1`
    - `grey_count: 2`
    - `total: 5`
    `evidence:`
    - full finding array with 5 items

## Important payload shapes

### `todo`

```json
{
  "items": ["Reproduce expected finding 1: ...", "..."],
  "total": 5
}
```

### `finding`

```json
{
  "agent": "Tracer",
  "data_point": "scope2_market_based_total",
  "flag": "red",
  "claimed_value": 47.0,
  "source_value": 44.8,
  "deviation_pct": 4.7,
  "message": "Scope 2 market-based total: PDF p.34 reports 47.0 ktCO2e, Excel Sheet3 sums to 44.8 ktCO2e (~4.7% delta)"
}
```

### `complete`

```json
{
  "pipeline": "mock",
  "parser_mode": "scripted-manifest",
  "summary": {
    "green_count": 0,
    "yellow_count": 1,
    "red_count": 2,
    "grey_count": 2,
    "total": 5,
    "material_red_count": 2,
    "review_required": true
  },
  "evidence": ["5 finding objects"],
  "total_findings": 5,
  "review_required": true
}
```