# ESRS E1 — Éghajlatváltozás (Climate Change) Knowledge Base

## Áttekintés
Az ESRS E1 standard az EU CSRD (Corporate Sustainability Reporting Directive) része, amely a vállalatok éghajlatváltozással kapcsolatos közzétételeit szabályozza. Ez a dokumentum a rendszer által auditálandó adatpontok definícióját és az elvárt formátumokat tartalmazza.

## Adatpontok (Data Points)

### E1-6 — Gross Scopes 1, 2, 3 and Total GHG Emissions

| Adatpont azonosító | Megnevezés | Mértékegység | Tipikus eltérés küszöb |
|---------------------|------------|--------------|------------------------|
| scope1_emission | Scope 1 kibocsátás (közvetlen) | tonna CO₂-egyenérték | 0.5% |
| scope2_emission | Scope 2 kibocsátás (közvetett, energia) | tonna CO₂-egyenérték | 0.5% |
| scope3_emission | Scope 3 kibocsátás (értéklánc) | tonna CO₂-egyenérték | 5.0% |
| total_ghg_emission | Teljes GHG kibocsátás | tonna CO₂-egyenérték | 0.5% |

### E1-5 — Energy Consumption and Mix

| Adatpont azonosító | Megnevezés | Mértékegység | Tipikus eltérés küszöb |
|---------------------|------------|--------------|------------------------|
| total_energy_consumption | Teljes energiafogyasztás | MWh | 0.5% |
| renewable_energy_share | Megújuló energia aránya | % | 0.5% |
| fossil_energy_share | Fosszilis energia aránya | % | 0.5% |
| nuclear_energy_share | Nukleáris energia aránya | % | 0.5% |

### E1-9 — Anticipated Financial Effects

| Adatpont azonosító | Megnevezés | Mértékegység | Tipikus eltérés küszöb |
|---------------------|------------|--------------|------------------------|
| carbon_credit_expenditure | Karbon kredit kiadás | millió Ft | 10.0% |
| carbon_price_per_ton | Karbon ár / tonna | Ft/tonna | 5.0% |
| transition_capex | Átállási CAPEX | millió Ft | 10.0% |
| physical_risk_financial_impact | Fizikai kockázat pénzügyi hatás | millió Ft | 10.0% |

## Flag Szintek (Risk Classification)

| Flag | Jelentés | Eltérés küszöb | Színkód |
|------|----------|---------------|---------|
| green | Nincs jelentős eltérés | < 0.5% | 🟢 |
| yellow | Kisebb eltérés, figyelmet igényel | 0.5% — 5.0% | 🟡 |
| red | Kritikus eltérés, azonnali beavatkozás szükséges | > 5.0% | 🔴 |
| grey | Nem auditálható / hiányos adat | N/A | ⚪ |

## PDF Parsing Szabályok

- A PDF-ek jellemzően magyar nyelvű fenntarthatósági jelentések
- A claim-ek (állítások) lehetnek szövegbe ágyazva vagy táblázatokban
- Egy oldalon több adatpontra vonatkozó állítás is szerepelhet
- A parser subagent feladata: oldalanként kigyűjteni az összes azonosítható állítást
- Kimenet formátuma: page_X.json → `{ "page": X, "claims": [...] }`

## Excel Parsing Szabályok

- Az Excel fájlok tartalmazzák a forrásadatokat
- Cellák lehetnek névvel ellátva (named range) vagy koordináta alapján hivatkozva
- A tracer subagent feladata: cella szinten visszakeresni a forrásértékeket
- Kimenet formátuma: batch_X.json → `{ "batch_id": X, "results": [...] }`

## Validációs Szabályok (Determinisztikus, NEM LLM!)

A validator_tool.py tiszta Python számításokat végez:
- Százalékos eltérés: `abs(claimed_value - source_value) / source_value * 100`
- Flag meghatározás: eltérés < 0.5% → green, 0.5-5.0% → yellow, > 5.0% → red
- Ha bármelyik érték hiányzik (None): flag = grey
- Ha source_value == 0: speciális kezelés (0-val osztás elkerülése)

## Példa egy teljes EvidenceResult-ra

```json
{
  "data_point": "scope2_emission",
  "flag": "red",
  "claimed_value": 4200,
  "source_value": 4020,
  "unit": "tonna",
  "deviation_pct": 4.48,
  "claim_text": "A vállalat 2024-es Scope 2 kibocsátása 4 200 tonna CO₂-egyenérték. (Forrás: energia_2024.xlsx)",
  "source_file": "energia_2024.xlsx",
  "source_sheet": "Scope1_Scope2",
  "source_cell": "Scope2_tonna3",
  "page": 7,
  "paragraph_idx": 3,
  "explanation": "KRITIKUS ELTÉRÉS: Scope 2 kibocsátás. Állítás: 4200 tonna. Forrás: 4020 tonna. Eltérés: 4.48%."
}