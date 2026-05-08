# Atlas — Pitch Materials

## Opening (60 seconds)

> A CSRD audit legdrágább, leglassabb része nem a jelentésírás. Hanem az, amikor az auditor hónapokon át kézzel keresi vissza, hogy az ESG-állítások mögött valóban ott vannak-e a számok a forrásdokumentumokban.
>
> Egyetlen E1 klímajelentés mögött 5-8 különböző Excel, CSV és PDF fájl van. A Scope 1, Scope 2, Scope 3 kibocsátási számok több munkalapon, több cellában rejtőznek. Az auditor egyesével nyitogatja, keresi, hasonlítja. Ez nem audit — ez archeológia.
>
> Az Atlas ezt a folyamatot építi be egy agentic audit trail rendszerbe. Ön feltölti a fenntarthatósági jelentést és a forrásfájlokat. Az Atlas kinyeri a claim-eket, visszakeresi a forrásértékeket, determinisztikusan validálja az eltéréseket, és azonnal megmutatja a piros zászlókat.
>
> Ez nem egy újabb ESG chatbot. Ez egy audit-grade forrásvisszakereső és ellentmondás-feltáró rendszer. A CSRD-audit legnehezebb részét gyorsítja fel, miközben az auditor marad a végső kontrollpont.

## 3-Minute Demo Script

### Phase 1 — Setup (0:00–0:45)

1. **"Upload"**: Megnyitjuk a New Audit felületet. Behúzzuk a statement PDF-et (`sustainability_report_2024.pdf`). Hozzáadjuk a source fájlokat: `emissions_data.xlsx`, `audit_summary_2024.csv`. A drag & drop azonnal visszajelzést ad.
2. **"Configure"**: Next → látjuk a beállításokat. E1 Climate, FY2024. Minden előre ki van töltve.
3. **"Launch"**: A Review oldalon Launch Audit. Az alkalmazás átnavigál az Audit Logs nézetre.

### Phase 2 — Live Workflow (0:45–1:30)

4. **"Watch the agents work"**: A Live Agent Feed mutatja az öt agent szereplőt:
   - **Orchestrator** — `Cataloguing input files... 3 files detected`
   - **Orchestrator** — `Building audit plan. 7 claims to verify.`
   - **Parser** — `Parsing sustainability_report_2024.pdf... 7 claims extracted.`
   - **Tracer** — `Tracing 7 claims against source files...`
   - **Tracer** — `Source detected: emissions_data.xlsx → Scope2_GHG sheet → cell B12`
   - **Validator** — `Scope 2 mismatch: claimed 4,200 vs source 4,020. Δ 4.48%`
   - **Validator** — `Red Flag: Scope 1+2 total inconsistency. Claimed 6,050 vs computed 5,870.`

5. **"Source Trace in action"**: A Source Trace Table mutatja a Flag oszlopot. OK / FAIL / REVIEW badge-ek. Minden sor: data point → source file → sheet → cell → claimed vs source → deviation.

### Phase 3 — The Reveal (1:30–2:15)

6. **"Review Required"**: A piros csík felugrik az Agent Feed alatt. Két red flag:
   - Scope 2 market-based emissions: 4,200 (claimed) → 4,020 (actual) → Δ 4.48%
   - Scope 1+2 total: 6,050 (claimed) → 5,870 (computed) → Δ 3.07%
   - Mindkettőhöz source trace: fájlnév, munkalap, cellahivatkozás.

7. **"The Evidence Package"**: Rákattintunk az Evidence Pkg gombra. Letöltődik a teljes audit package JSON: metadata, findings, summary, red flags, review_required.

### Phase 4 — Dashboard & Closing (2:15–3:00)

8. **"Dashboard"**: Átváltunk a Dashboard nézetre. Bal oldalt a Verdict, Coverage statok, Evidence Package download. Jobb oldalt a Critical Findings részletes bontással és a Recent Activity stream.

9. **Closing**: "Az Atlas 3 perc alatt elvégezte azt, ami manuálisan órákat venne igénybe. Audit-grade source trace. Determinisztikus validáció. És a végén egy kezbe vehető evidence package. Az auditor dönt, de az Atlas megadja hozzá a tényeket."

## Slides Outline (4 slides)

### Slide 1 — The Problem
- **Title**: The $500B Blind Spot in CSRD Audits
- **Key message**: Auditors spend 60-70% of CSRD time on manual source tracing — opening Excel files, comparing cells, hunting for discrepancies.
- **Data point**: E1 Climate alone: 7-12 disclosed data points, 3-5 source files, 20+ spreadsheet tabs.
- **Visual**: Split screen — sustainability PDF left, Excel grid right, auditor in the middle with magnifying glass.

### Slide 2 — The Solution
- **Title**: Atlas — Agentic Audit Trail for CSRD
- **Key message**: Five AI agents (Orchestrator → Parser → Tracer → Validator → Reporter) automate the full claim-to-source verification chain.
- **Visual**: Agent workflow diagram with arrows connecting the five agents.
- **Tags**: E1 Climate · Deterministic validation · Audit-grade trace · Real-time findings

### Slide 3 — The Workflow
- **Title**: From Claim to Source in Seconds
- **Key message**: Upload → Parse → Trace → Validate → Flag → Package. Every finding linked to a specific source cell.
- **Visual**: Annotated screenshot of the Audit Logs view showing the full layout:
  - Regulatory Extracts (claim cards)
  - Source Trace Table (with Flag column)
  - Review Required panel (red flags)
  - Live Agent Feed
  - Evidence Pkg download button
- **Callout**: "Red Flag: Scope 2 emissions — claimed 4,200 tCO2e, actual 4,020. Source: emissions_data.xlsx [B12]"

### Slide 4 — Business Impact
- **Title**: Faster, Cheaper, More Reliable CSRD Audits
- **Key messages**:
  - **Speed**: Claim-to-source trace in seconds vs. hours
  - **Accuracy**: Deterministic validation — no hallucination, no guesswork
  - **Trust**: Every finding linked to a source cell; auditor stays in control
  - **Scale**: E1 today → E2, S1, G1 tomorrow
- **Visual**: Side by side: "Manual Audit" (stack of files, clock) vs "Atlas Audit" (single screen, evidence package, time saved)
- **Bottom line**: "Atlas doesn't replace the auditor. It gives them superpowers."

## Technical Architecture (Backup Slide)

- **Frontend**: React 19 + TypeScript + Tailwind CSS + Vite + Motion (animations)
- **Backend**: FastAPI + Python + deterministic validation tools
- **Communication**: SSE (Server-Sent Events) for real-time agent feed
- **Output**: JSON evidence package with full audit trail
- **Demo dataset**: Fixed E1 document bundle with guaranteed 2+ red flags

## Key Talking Points

1. "We're not building a general platform — we're solving the hardest 80% of CSRD audit work."
2. "The source trace goes down to the exact cell in the Excel file."
3. "The validator is deterministic — no LLM guessing on numbers."
4. "The auditor remains the final decision-maker. Atlas prepares the evidence."
5. "This is E1 only today. The architecture scales to E2, S1, G1."

## Backup Screenshots

Screenshots to capture for backup:
1. New Audit upload screen with files loaded
2. Audit Logs view with live feed running
3. Source Trace Table with OK/FAIL/REVIEW flags visible
4. Review Required panel expanded with red flag details
5. Dashboard view with Verdict and Critical Findings
6. Evidence Package JSON preview (or download prompt)