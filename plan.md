# Atlas - CSRD Audit Intelligence

## Hackathon fejlesztesi terv

Ez a terv arra keszult, hogy 2 ember 20 ora alatt a jelenlegi allapotbol egy eros, stabil, bemutathato hackathon MVP-t rakjon ossze.

Nem a teljes vegleges termeket epiti meg, hanem egy dijnyertes demohoz szukseges minimumot:

- valos uzleti problema
- latvanyos agentic workflow
- audit-grade source trace
- determinisztikus red flag detection
- jol bemutathato UI

## A hackathon MVP celja

Az MVP egy szuk E1 use case-et old meg.

Mit kell tudnia a vegere:

1. Feltolt egy sustainability statement PDF-et es nehany supporting source file-t.
2. Kinyer 5-8 tamogatott E1 adatpontot a PDF-bol.
3. Visszakeresi ezek forrasat Excelbol, CSV-bol es opcionaalisan egy supporting PDF-bol.
4. Determinisztikusan ellenorzi az eltereseket.
5. A UI-ban megmutatja a claim -> source -> deviation -> flag lancot.
6. Piros flag eseten review required allapotot mutat.
7. A vegere general egy evidence package JSON-t.

## Amit NEM csinalunk meg a hackathon alatt

Ezeket tudatosan kivagjuk, hogy ne essen szet a scope:

1. Nem tamogatunk mindenfele dokumentumformatumot.
2. Nem epitunk teljes altalanos LangGraph workflow engine-t checkpointinggal.
3. Nem epitunk teljes ketkapus HITL approval rendszert.
4. Nem csinalunk production minosegu annotalt PDF exportot.
5. Nem terjesztjuk ki E2, S1, G1 disclosure-okra.
6. Nem epitunk altalanos, barmilyen Excel-semahoz alkalmazkodo tracert.
7. Nem epitunk vector DB-t, ha a demo anelkul is eros.

## Jelenlegi allapot roviden

A jelenlegi rendszer mar tud egy mukodo demo-flowt:

- backend API futtatas: `backend/api.py`
- fix determinisztikus pipeline: `backend/pipeline.py`
- tool reteg: `backend/tools/*.py`
- frontend dashboard es upload flow: `frontend/src/**`

Jelenlegi erossegek:

1. Van mukodo upload flow.
2. Van mukodo audit inditas.
3. Van findings UI.
4. Van SSE-alapu live feed.
5. Van determinisztikus validator reteg.

Jelenlegi hianyossagok, amiket a hackathon MVP-ben javitani kell:

1. A workflow meg mindig tul fix es tul pipeline-szeru.
2. A parser-tracer-validator szerepek a UI-ban es a backendben nem eleg tisztak.
3. A trace outputot egysegesiteni kell.
4. A demo narrativat ra kell epiteni a valos audit trail-re.
5. Kell egy jol ertelmezheto review required allapot.

## Vegleges hackathon scope freeze

### Tamogatott disclosure

- csak ESRS E1

### Tamogatott adatpontok

1. scope1_emission
2. scope2_emission
3. scope1_scope2_total
4. scope3_emission
5. renewable_pct
6. headcount
7. training_participants vagy production_sites opcionaalis fallback

### Tamogatott source formatumok

1. 1 statement PDF
2. 1-2 Excel workbook
3. 1 CSV export
4. 1 optional supporting PDF vagy invoice PDF

### Tamogatott validaciok

1. claim vs source value
2. arithmetic consistency
3. row count consistency
4. missing evidence detection

### Vegso outputok

1. live workflow feed
2. findings dashboard
3. source trace table
4. review required panel
5. evidence package JSON

## Csapat es felelossegek

### Ember A - Backend + workflow + data

Tulajdon:

1. `backend/api.py`
2. `backend/pipeline.py`
3. `backend/tools/*.py`
4. `backend/orchestrator.py` csak annyiban, amennyiben a demo narrativat segiti
5. demo dataset stabilizalasa
6. SSE es report output

### Ember B - Frontend + UX + pitch

Tulajdon:

1. `frontend/src/components/**`
2. `frontend/src/hooks/**`
3. findings, feed, review UI
4. upload flow polish
5. demo script
6. pitch narrative es slide-ok

## Minden lenyegi dontes elore meghozva

Itt NINCSENEK nyitott architekturalis kerdesek. A hackathon alatt nem tervezunk tovabb, hanem vegrehajtunk.

### Vegleges technikai dontesek

1. Nem epitunk teljes LangGraph rendszert a hackathon alatt.
2. A jelenlegi `backend/pipeline.py` marad a futo mag, de agentic workflow-kent lesz dramaturgiailag es API/SSE szinten szetbontva.
3. A backend orchestrator a hackathonon nem full workflow engine lesz, hanem egy konnyu koordinacios reteg es event producer.
4. A Parser lehet LLM-es vagy deterministic fallback, de a demo dataseten garantaltan stabilan kell mukodnie.
5. A Tracer elsosorban deterministic source resolution lesz, nem altalanos szemantikus keresorendszer.
6. A Validator teljesen deterministic marad.
7. A Reporter a hackathonon JSON evidence package + UI summary lesz. Nem epitunk teljes annotalt PDF exportot.
8. A review flow a hackathonon UI-driven lesz. Nem epitunk teljes audit approval state machine-t.
9. A tamogatott disclosure csak E1.
10. A tamogatott dokumentumok csak: statement PDF, Excel, CSV, optional invoice/supporting PDF.
11. A demo csak egy fix, elore osszerakott dokumentumcsomagra lesz optimalizalva.
12. A frontenden a fo demo-nezet az `Audit Logs` marad, ide kerul minden ero.
13. A `New Audit` csak upload + launch szerepet tol be, nem lesz belole teljes konfiguracios wizard.
14. A siker definicioja: stabil 3 perces demo, nem altalanos platform.

### Vegleges funkciok a demo buildben

Ezeknek keszen kell lenniuk:

1. File upload mukodik.
2. Audit inditas mukodik.
3. Live workflow feed mutatja a stage-eket.
4. Parser / Tracer / Validator szerepkor latszik a UI-ban.
5. Legalabb 5 claim jelenik meg.
6. Legalabb 3 findinghoz konkret source trace van.
7. Legalabb 2 red flag biztosan kijon.
8. Review required blokk latszik.
9. Evidence package JSON elerheto.
10. Demo narrativaba illeszkedo summary latszik.

### Amit biztosan nem csinalunk meg

1. Nem keszitunk uj adatmodellt SQLite-tal.
2. Nem keszitunk vector DB integraciot.
3. Nem keszitunk altalanos schema inference motort.
4. Nem keszitunk production quality review workflow backendet.
5. Nem keszitunk E2/S1/G1 tamogatast.
6. Nem keszitunk OCR pipeline-t.

## Vegrehajtasi szabalyok

1. Ember A csak backendhez nyul, kiveve ha handshake miatt pici frontendes schema update kell.
2. Ember B csak frontendhez es pitch anyaghoz nyul, kiveve ha sample JSON-t kell ellenorizni.
3. Barmilyen schema valtozas elott Ember A eloszor rogzit egy mintakimenetet, es azt atadja Ember B-nek.
4. Nincs improvizalt feature addicio a 11. ora utan.
5. A 14. ora utan csak polish, pitch es blocker fix.

## Fix fajlfelelosseg

### Ember A altal modositott fajlok

1. `backend/api.py`
2. `backend/pipeline.py`
3. `backend/orchestrator.py`
4. `backend/tools/validator_tool.py`
5. `backend/tools/pdf_tools.py` csak ha muszaj
6. `backend/tools/excel_tools.py` csak ha muszaj
7. `backend/workspace/*` demo inputok es kimenetek

### Ember B altal modositott fajlok

1. `frontend/src/hooks/useAtlasData.ts`
2. `frontend/src/services/api.ts`
3. `frontend/src/App.tsx`
4. `frontend/src/components/audit/AgentFeed.tsx`
5. `frontend/src/components/audit/SourceTraceTable.tsx`
6. `frontend/src/components/audit/RegulatoryExtracts.tsx`
7. `frontend/src/components/dashboard/Dashboard.tsx`
8. `frontend/src/components/new-audit/*`
9. `frontend/src/components/layout/*` csak ha muszaj

## Ember A - konkret vegrehajtasi backlog

Ez a lista mar vegleges. Ember A ennek sorrendjeben halad. Nem kell ujratervezni, csak leirni a kodot.

### A0 - demo dataset lock

Celpont:

1. Vegleges demo input csomag legyen.
2. Garantalt legyen benne legalabb 2 red flag.

Teendo:

1. Ellenorizze a `backend/workspace/input` tartalmat.
2. Ellenorizze, hogy a jelenlegi inputokbol ugyanaz a finding keszlet jon ki minden futasnal.
3. Ha kell, modositson a demo file-okon vagy a deterministic mappingen, hogy a red flag-ek fixen kijojjenek.

Elfogadasi kriterium:

1. ugyanarra a dokumentumcsomagra ugyanaz a 9 finding jon vissza
2. legalabb 2 red flag stabil

### A1 - vegleges event taxonomy a backendben

Celpont:

Az SSE feed ne technikai zaj legyen, hanem demo-kompatibilis audit workflow.

Fajlok:

1. `backend/api.py`
2. opcionaalisan `backend/pipeline.py`

Teendo:

1. Hozzon letre fix event-nevlistat.
2. A live es mock oldalon ugyanazokat a szemantikai stage-eket adja vissza.
3. Az uzenetek emberileg ertelmesek legyenek.

Vegleges event lista:

1. `status`
2. `phase`
3. `todo`
4. `agent_start`
5. `agent_progress`
6. `agent_done`
7. `finding`
8. `complete`
9. `error`

Vegleges phase-ek:

1. `catalog_inputs`
2. `build_audit_plan`
3. `parse_claims`
4. `trace_sources`
5. `validate_findings`
6. `build_report`

Elfogadasi kriterium:

1. mock es live futasnal is ugyanaz a workflow dramaturgia latszik
2. frontend oldalon nem kell kulon logikat irni a mock es live szetkezelesere

### A2 - pipeline stage-ek explicit szetbontasa

Celpont:

A jelenlegi fix pipeline maradjon, de latszodjon rajta a parser / tracer / validator bontas.

Fajl:

1. `backend/pipeline.py`

Teendo:

1. A `run_full_audit` belsejeben nevezze kulon blokkra a lepeseket.
2. Minden blokk kuldjon kulon progress callback eventet.
3. A claim extraction stage parser-kent legyen cimkezve.
4. A trace stage tracer-kent legyen cimkezve.
5. A deterministic math validator-kent legyen cimkezve.

Elfogadasi kriterium:

1. a live streambol egyertelmu, mikor dolgozik a parser, tracer, validator

### A3 - evidence schema veglegesitese

Celpont:

Minden finding ugyanazt a szerkezetet kovesse.

Fajlok:

1. `backend/pipeline.py`
2. `backend/api.py`

Vegleges finding schema:

1. `data_point`
2. `claim_text`
3. `claimed_value`
4. `source_value`
5. `unit`
6. `source_file`
7. `source_sheet`
8. `source_cell`
9. `deviation_pct`
10. `flag`
11. `explanation`
12. `page`
13. `paragraph_idx`
14. `review_required`

Teendo:

1. Minden finding tartalmazza a fenti mezoket.
2. Missing source eseten is maradjon ervenyes a schema.
3. A `review_required` legyen `true`, ha `flag == red`.

Elfogadasi kriterium:

1. frontend egy schema szerint tud renderelni mindent

### A4 - missing evidence kezelese

Celpont:

Ha nincs source, az ne nema hiba legyen, hanem bemutathato finding.

Fajlok:

1. `backend/pipeline.py`
2. ha kell `backend/tools/*`

Teendo:

1. Source nelkul ne torjon a pipeline.
2. Keszitsen explicit grey findingot.
3. Az explanation egyertelmuen mondja ki, hogy manual verification kell.

Elfogadasi kriterium:

1. a UI-ban a missing evidence ugyanolyan findingkent latszik

### A5 - report JSON rendbetetele

Celpont:

Legyen kezbe veheto audit package.

Fajl:

1. `backend/pipeline.py`

Vegleges report szerkezet:

1. `audit_metadata`
2. `document_inventory`
3. `findings`
4. `summary`
5. `red_flags`
6. `review_required`

Teendo:

1. `audit_metadata` tartalmazza a dokumentum nevet, idot, total pages, total claims, total findings.
2. `document_inventory` sorolja fel a bemeneti file-okat.
3. `summary` tartalmazza a countokat es a verdictet.
4. `red_flags` kulon tomb legyen.
5. `review_required` legyen top-level bool.

Elfogadasi kriterium:

1. a report JSON demonstralhato mint audit evidence package

### A6 - evidence package endpoint veglegesitese

Celpont:

A frontend es a demo is le tudja kerni a teljes audit package-et.

Fajl:

1. `backend/api.py`

Teendo:

1. A `GET /report` endpoint biztosan a vegleges report szerkezetet adja.
2. Hibakezeles legyen ertelmes.
3. Ures report eseten jo hiba legyen.

Elfogadasi kriterium:

1. a frontend vagy browserbol megnyithato a teljes package

### A7 - review summary logika

Celpont:

A backend egyertelmuen mondja ki, hogy auditor review szukseges-e.

Fajlok:

1. `backend/pipeline.py`
2. `backend/api.py`

Teendo:

1. A summaryba tegye bele a `review_required` mezojet.
2. Red flag eseten ez legyen `true`.
3. Keszitsen `material_red_count` vagy hasonlo mezojet, ha segiti a frontend renderelest.

Elfogadasi kriterium:

1. Ember B mar kulon business logika nelkul ki tudja irni a review calloutot

### A8 - mock es live output osszehangolasa

Celpont:

Frontend ugyanazt a formatumot kapja mock es live modban.

Fajl:

1. `backend/api.py`

Teendo:

1. A mock evidence es a live evidence mezozese egyezzen.
2. A summary szerkezet egyezzen.
3. Az SSE dramaturgia egyezzen.

Elfogadasi kriterium:

1. a frontend special-case nelkul mukodik mindket modban

### A9 - stabilitasi tesztkor

Celpont:

Ne a demo alatt deruljon ki, hogy valami flaky.

Teendo:

1. Futtassa le legalabb 5-szor a teljes auditot.
2. Hasonlitsa ossze a finding countot.
3. Hasonlitsa ossze a red flag countot.
4. Ellenorizze a `health`, `audit`, `report`, `evidence` endpointokat.

Elfogadasi kriterium:

1. nincs flaky kimenet

### A10 - fallback terv

Celpont:

Ha az LLM layer bizonytalan, a demo akkor is mukodjon.

Teendo:

1. A deterministic fallback legyen mindig futtathato.
2. Mock mod is maradjon hasznalhato vegso tartaleknak.
3. Legyen elore dokumentalt command a biztos demo inditasahoz.

Elfogadasi kriterium:

1. van B terv a szinpadra

## Ember B - konkret vegrehajtasi backlog

Ez a lista mar vegleges. Ember B ennek sorrendjeben halad. Nem kell ujratervezni, csak leirni a kodot.

### B0 - vegleges demo UX dontesek rogzitese

Celpont:

Ne legyen felesleges kepernyo a demo kozben.

Vegleges demo flow:

1. `New Audit` - upload es launch
2. `Audit Logs` - fo demo nezet
3. `Dashboard` - zaro osszegzo nezet, ha kell

Teendo:

1. Minden felesleges UI-elemet vegyen ki vagy halkitson el.
2. A fo hangsuly az `Audit Logs` nezetre keruljon.

Elfogadasi kriterium:

1. a demo alatt nincs zavaros navigacio

### B1 - SSE feed vegleges renderelese

Celpont:

A workflow feed legyen a demo egyik fo latvanyelementuma.

Fajlok:

1. `frontend/src/hooks/useAtlasData.ts`
2. `frontend/src/components/audit/AgentFeed.tsx`

Teendo:

1. A backend fix event taxonomyat lekovesse.
2. Kulon cimkeje legyen az agent tipusanak.
3. Az uzenetek olvashatoak legyenek.
4. A piros finding eventek kulon kiemelest kapjanak.
5. Az utolso 30-50 eventet tartsa meg.

Elfogadasi kriterium:

1. a biro 5 masodperc alatt ertse, hogy itt workflow fut, nem csak log spam

### B2 - Source Trace Table atalakitas az uj schemahoz

Celpont:

A trace tabla legyen a demo hitelessegenek kozeppontja.

Fajl:

1. `frontend/src/components/audit/SourceTraceTable.tsx`

Teendo:

1. Az uj finding schema alapjan rendereljen.
2. Kotelezo oszlopok:
   - Data Point
   - Source File
   - Sheet / Ref
   - Cell
   - Source Value
   - Deviation
   - Flag
3. Missing evidence is ertelmesen jelenjen meg.
4. Red findingok legyenek azonnal lathatok.

Elfogadasi kriterium:

1. a tabla onmagaban is elmondja a trace sztorit

### B3 - Regulatory Extracts es trace kapcsolat eroszitese

Celpont:

A claim oldali es a source oldali nezopont ossze legyen kotve.

Fajlok:

1. `frontend/src/components/audit/RegulatoryExtracts.tsx`
2. ha kell `frontend/src/App.tsx`

Teendo:

1. A claim kartyakon latszodjon a flag.
2. A claim kartyak es a trace tabla ugyanazt a findingot tudjak reprezentalni.
3. Ha belefer, kattintaskor same item legyen aktiv mindket panelen.

Elfogadasi kriterium:

1. a demo soran egy findingrol gyorsan at lehet menni claimrol source-ra

### B4 - review required panel

Celpont:

Mutatni, hogy az auditor a vegso kontrollpont.

Fajlok:

1. `frontend/src/components/dashboard/Dashboard.tsx`
2. vagy uj komponens `frontend/src/components/audit/*`

Teendo:

1. Keszitsen kulon panelt a material red flag-eknek.
2. A panel mutassa:
   - data point
   - claim vs source
   - deviation
   - miert fontos
3. Top-level callout: `Auditor Review Required`.
4. Ha belefer, action buttonok csak UI-szinten:
   - Accept for review
   - Needs manual evidence
   - Override

Elfogadasi kriterium:

1. a demo alatt a human-in-the-loop koncepcio latszik

### B5 - summary cardok ujradefinialasa

Celpont:

A summary ne dekoracio legyen, hanem business message.

Fajlok:

1. `frontend/src/components/dashboard/Dashboard.tsx`
2. `frontend/src/components/dashboard/SummaryCard.tsx`
3. `frontend/src/components/layout/StatusBar.tsx`

Vegleges summary elemek:

1. Total Findings
2. Red Flags
3. Files Checked
4. Review Required

Teendo:

1. Ezeket a summarybol vagy health-bol toltse.
2. A `review_required` legyen vizualisan hangsulyos.

Elfogadasi kriterium:

1. a summary a pitch uzleti allitasat tamogatja

### B6 - upload flow polish

Celpont:

Az upload ne tunjon technikai mellekfunkcionak.

Fajlok:

1. `frontend/src/components/new-audit/StepUpload.tsx`
2. `frontend/src/components/new-audit/StepReview.tsx`
3. `frontend/src/components/new-audit/NewAudit.tsx`

Teendo:

1. Ellenorizze, hogy a statement PDF kulon jol latszik.
2. Ellenorizze, hogy a source file-ok listaja ertelmes.
3. A launch CTA legyen egyertelmu.
4. A launch utan az app vigyen at a fo demo nezetre.

Elfogadasi kriterium:

1. a demo upload resze 20-30 masodperc alatt vegigkattinthato

### B7 - evidence package UX

Celpont:

Legyen megmutathato a kezbe veheto kimenet.

Fajlok:

1. `frontend/src/services/api.ts`
2. megfelelo komponens a dashboardban vagy audit nezetben

Teendo:

1. Hozzon be egy `View Evidence Package` akciot.
2. Ha nincs szep viewer, legalabb nyissa meg vagy jelenitse meg letisztultan a JSON-t.
3. A usernek latszodjon, hogy ez exportalhato audit artifact.

Elfogadasi kriterium:

1. a demo vegen van mit megmutatni, mint output deliverable

### B8 - szovegezesi es vizualis polish

Celpont:

A UI hangja PwC-kompatibilis, professzionalis legyen.

Teendo:

1. Minden cimkeszoveget letisztit.
2. Kiveszi a zavaros vagy generikus AI-os megfogalmazasokat.
3. Az allapotnyelv legyen kovetkezetes:
   - Audit Running
   - Trace Complete
   - Review Required
   - Evidence Package Ready
4. A red / yellow / green nyelv mindenhol egyforma legyen.

Elfogadasi kriterium:

1. a UI nem startup hobby projektnek, hanem komoly audit toolnak tunik

### B9 - pitch anyagok

Celpont:

Ne csak app legyen, hanem eladhato sztori.

Teendo:

1. 60 masodperces opening megirasa.
2. 3 perces demo script megirasa.
3. 4 slide osszerakasa:
   - problema
   - megoldas
   - workflow
   - uzleti impact
4. Backup screenshotok keszitese.

Elfogadasi kriterium:

1. ha a demo reszben technikai csuszas van, a pitch akkor is eros marad

## Handshake pontok

Ezek kotelezo egyeztetesi pontok. Itt meg kell allni 10-15 percre es szinkronizalni.

### Handshake 1 - 2. ora vegen

Ellenorizni kell:

1. mi a vegleges demo dataset
2. mi a vegleges finding schema
3. milyen SSE event nevek lesznek

### Handshake 2 - 5. ora vegen

Ellenorizni kell:

1. a frontend mar tudja-e fogyasztani az uj schema-t
2. a source trace tabla jo oszlopokat kap-e
3. a piros flag-ek biztosan latszanak-e

### Handshake 3 - 9. ora vegen

Ellenorizni kell:

1. van-e review required panel
2. megnyithato-e a report package
3. megvan-e a demo wow moment

### Handshake 4 - 14. ora vegen

Ellenorizni kell:

1. feature freeze
2. pitch anyagok allapota
3. fallback terv

## Parhuzamositas pontos matrixa

### Egyszerre futhat

1. A1 es B1
2. A3 es B2
3. A4 es B3
4. A5 es B5
5. A7 es B4
6. A9 es B9

### Nem futhat egyszerre egyeztetes nelkul

1. A3 es B2 akkor, ha a schema meg valtozik
2. A5 es B7 akkor, ha a report contract meg nem fix
3. B4 nem indulhat el, amig A7 nincs nagyjabol kesz

## Ha valami csuszik, mit vagnunk ki eloszor

1. UI action gombok a review panelbol
2. kattinthato kapcsolat claim es trace panel kozott
3. optional supporting PDF trace
4. orchestrator wrapper barmilyen extra logikaja

Ezeket NEM vagjuk ki:

1. audit inditas
2. workflow feed
3. source trace tabla
4. red flag-ek
5. evidence package

## 20 oras reszletes terv

## 0. ora - kickoff es scope lock (30-45 perc, kozosen)

Feladatok:

1. Rogzitsetek a hackathon one-linert:
   `Atlas egy agentic audit trail rendszer, amely automatikusan visszavezeti az ESRS E1 allitasokat a forrasdokumentumokig, es mar a folyamat kozben kimutatja az ellentmondasokat.`
2. Veglegesitsetek a demo dokumentumcsomagot.
3. Veglegesitsetek a tamogatott adatpontokat.
4. Dontsetek el, mi a demo fo wow momentje.
5. Dontsetek el, mi az a 3 dolog, ami semmikepp sem csuszhat ki.

Kimenet:

1. fix scope
2. fix demo dataset
3. fix success criteria

## 1-2. ora - baseline stabilizalas

### Ember A feladatai a baseline stabilizalasban

1. Lefuttatja a jelenlegi backend flow-t ugyanazzal a demo inputtal tobbszor.
2. Ellenorzi, hogy ugyanazokat a findingokat adja-e vissza minden futasban.
3. Letisztitja a `run_audit`, `stream`, `evidence`, `report` endpointokat.
4. Ha kell, javitja a determinisztikus trace vagy validation szabalyokat.

### Ember B feladatai a baseline stabilizalasban

1. Lefuttatja a frontendet a mostani flow-val.
2. Vegignezi, melyik kepernyo kell a demohoz es melyik felesleges.
3. Letisztitja a fo navigaciot.
4. Megtervezi a vegleges 3 fo nezetet:
   - upload / start
   - live audit
   - findings / review

Kesz allapot definicio:

1. a jelenlegi rendszer stabilan indul
2. a demo inputtal stabil kimenetet ad
3. ismert, hogy mi marad bent a UI-ban

## 2-4. ora - workflow dramaturgia es SSE feed

Cel: a rendszer ne egyszeru pipeline-nak tunjon, hanem agentic audit workflow-nak.

### Ember A feladatai a workflow dramaturgiaban

1. A pipeline lepeseket explicit stage-ekre bontja:
   - catalog_inputs
   - build_audit_plan
   - parser_run
   - tracer_run
   - validator_run
   - report_build
2. Ezekhez SSE eventeket kuld.
3. A stage-ekhez emberileg ertheto `message` mezo tartozzon.
4. A parser es tracer lepesekhez worker-szeru outputot irjon a feedhez.

### Ember B feladatai a workflow dramaturgiaban

1. A frontend feedben kulon stilust ad ezeknek a szereploknek:
   - Orchestrator
   - Parser
   - Tracer
   - Validator
   - Reporter
2. Kiir egy audit tasklistat vagy progress summary-t.
3. Vizualisan kiemeli a piros findingokat a live feedben is.

Kesz allapot definicio:

1. a futas kozben latni, hogy mi tortenik
2. a workflow emberileg ertelmezheto
3. a demo alatt nem kell magyarazni, hogy epp melyik komponens dolgozik

## 4-7. ora - source trace hitelesitese

Ez a legfontosabb blokk. Itt dol el, hogy audit-grade vagy csak chatbot demo.

### Ember A feladatai a source trace hitelesitesben

1. Egyseges evidence schema-t vezet be.
2. Minden findinghoz kotelezoen legyen:
   - data_point
   - claim_text
   - claimed_value
   - source_value
   - source_file
   - source_sheet vagy source_cell vagy source_row
   - deviation_pct
   - flag
   - explanation
3. Missing evidence eseten explicit finding keletkezzen.
4. A validator magyarazatok legyenek rovidek, auditnyelven erthetok.

### Ember B feladatai a source trace hitelesitesben

1. A Source Trace Table-t a schemahoz igazitja.
2. Kattinthato vagy reszletesebb trace panelt tesz moge.
3. A piros findingoknak kulon highlightot ad.
4. A Regulatory Extracts es a Source Trace panel kozott erosebb kapcsolatot teremt.

Kesz allapot definicio:

1. egy findingrol azonnal latszik a source
2. a trace panel ertelmezheto extra magyarazat nelkul is
3. a red flag valosnak es reprodukalhatonak tunik

## 7-9. ora - review required allapot

Cel: megmutatni, hogy az AI nem "dont", hanem review-ra keszit elo.

### Ember A feladatai a review state kialakitasaban

1. Bevezet egy `review_required` allapotot a report summary-ba.
2. A red findingokat kulon tombbe rendezi.
3. Opcionaalisan keszit egy egyszeru endpointot a finding review state-hez.
4. Ha nincs ido, maradjon csak report-level state.

### Ember B feladatai a review state kialakitasaban

1. Keszit egy `Auditor Review Required` blokkot.
2. Ide kiemelten listazza a material red flag-eket.
3. Minden red flagnel mutatja:
   - mi volt a claim
   - mi a source
   - mekkora az elteres
   - miert fontos
4. Ha belefer, csinal 3 action gombot:
   - Accept for review
   - Needs manual evidence
   - Override

Kesz allapot definicio:

1. a demo soran egyertelmu, hogy az auditor tovabbra is a kontrollpont
2. a red findingok kulon review zona-ban latszanak

## 9-11. ora - evidence package es export

### Ember A feladatai az evidence package kialakitasaban

1. Letisztitja a vegso report JSON-t.
2. Hozzaadja ezeket a blokkokat:
   - audit_metadata
   - document_inventory
   - findings
   - summary
   - red_flags
3. Biztosit egy endpointot a package lekerdezesere.

### Ember B feladatai az evidence package UX-ben

1. A frontendben tesz egy `View Evidence Package` vagy `Export JSON` akciot.
2. A summary kartyakba beleteszi a legfontosabb szamokat:
   - total findings
   - red flags
   - files checked
   - audit readiness

Kesz allapot definicio:

1. a rendszernek van kezbe veheto kimenete
2. a demo vegen lehet mutatni, hogy ez mar nem csak egy UI, hanem audit artifact

## 11-14. ora - polish, stabilitas, demo dataset

### Ember A feladatai a stabilitasban

1. Veglegesiti a demo input file-okat.
2. Ugy allitja be oket, hogy legalabb 2-3 biztos red flag legyen.
3. Keszit fallbacket arra az esetre, ha az LLM layer bizonytalan vagy lassu.
4. Ellenorzi a portokat, dependency-ket, env beallitasokat.

### Ember B feladatai a polish soran

1. Letisztitja az osszes UI szoveget.
2. Kiveszi a demohoz nem szukseges elemeket.
3. Egysegesiti a szineket, a cimkeszovegeket es az allapotnyelvet.
4. Keszit 1-2 backup screenshotot.

Kesz allapot definicio:

1. a demo flow stabil
2. a design konzisztens
3. a backup anyagok megvannak

## 14-16. ora - pitch epites

Ezt kozosen kell csinalni, de a fokusz megoszthato.

### Ember A feladatai a pitch technikai reszeben

1. Osszerak egy egyszeru architektura abrat.
2. Leirja a technikai uzenetet:
   - parser
   - tracer
   - validator
   - reporter
   - orchestrator
3. Megfogalmazza, miert nem summary app a termek.

### Ember B feladatai a pitch es demo narrativaban

1. Megirja a 60 masodperces openinget.
2. Megirja a 3 perces demo scriptet.
3. Osszerak 3-4 slide-ot:
   - problema
   - megoldas
   - workflow
   - uzleti hatas

Kesz allapot definicio:

1. van rovid pitch
2. van demo script
3. van 3-4 stabil slide

## 16-18. ora - teljes dry run

Kozosen:

1. Vegigmentek az egesz demon legalabb ketszer.
2. Egyszer normal futassal.
3. Egyszer fallback tervvel.
4. Kijavitjatok a zavaros szovegeket.
5. Megnezitek, hol csuszik a sztori vagy a technika.

Kesz allapot definicio:

1. a teljes demo 3 perc alatt vegigviheto
2. nincs olyan lepes, ahol improvizalni kell

## 18-20. ora - bugfix freeze es szinpadkesz allapot

1. Innentol csak blocker bugot javitunk.
2. Nincs uj feature.
3. Ellenorizni kell:
   - szerverek indulnak
   - upload mukodik
   - audit lefut
   - findings UI helyes
   - export mukodik
   - slides megvannak
4. Kijelolni, ki beszel es ki kattint.

Kimenet:

1. stabil demo build
2. stabil pitch
3. stabil fallback terv

## Konkreten parhuzamosan vegezheto munkak

Ezek a munkak egymastol jol fuggetlenek, ezert parhuzamosan mehetnek.

### Track A - Backend / workflow

1. SSE event schema tisztitasa
2. pipeline stage-ek szetbontasa
3. evidence schema egysegesites
4. report JSON szerkezet rendbetetele
5. missing evidence finding bevezetese

### Track B - Frontend / UX

1. live feed polish
2. trace table javitas
3. review panel kialakitasa
4. summary cards finomitasa
5. export gomb es package nezet

### Track C - Demo es pitch

1. demo dataset finomitasa
2. wow moment script kidolgozasa
3. slides osszerakasa
4. opening es closing szoveg megirasa
5. backup screenshotok keszitese

### Mit lehet egyszerre csinalni utkozes nelkul

1. Ember A dolgozhat a `backend/api.py` es `backend/pipeline.py` fajlokon, mikozben Ember B a `frontend/src/components/**` es `frontend/src/hooks/**` fajlokon dolgozik.
2. Ember A tudja tisztitani az SSE eventeket, mikozben Ember B a feed vizualis megjeleniteset epiti.
3. Ember A tudja egysegesiteni a findings schema-t, mikozben Ember B a findings es trace tablakat atalakítja az uj schemahoz.
4. Ember B tud pitch slide-okat es demo scriptet irni, mikozben Ember A stabilitasi teszteket futtat.

### Mit NEM erdemes parhuzamosan csinalni

1. Ne dolgozzatok ketten ugyanazon a backend fajlon egyszerre.
2. Ne valtoztasson egyszerre ket ember a findings schema-n es a hozza tartozo frontend mappingen egyeztetes nelkul.
3. Ne legyen uj feature a polish fazisban.

## Prioritas szerinti backlog

### P0 - kotelezo

1. stabil upload
2. stabil audit run
3. live workflow feed
4. legalabb 5 feldolgozott claim
5. legalabb 3 source trace
6. legalabb 2 red flag
7. review required allapot
8. evidence package JSON

### P1 - erosito elemek

1. tasklist vagy plan nezet
2. jobb trace drawer
3. jobb summary cardok
4. red flag kulon review panel

### P2 - csak ha minden kesz

1. egyszeru orchestrator wrapper
2. supporting PDF trace finomitasa
3. javitott export UX

## Definition of Done

Az app akkor kesz a hackathonra, ha mind a 10 pont igaz:

1. Feltoltheto a statement PDF es a supporting files.
2. Egy gombbal indithato az audit.
3. A UI mutatja az audit workflow lepeseket.
4. Legalabb 5 claim feldolgozasra kerul.
5. Legalabb 3 claimhez van konkret source trace.
6. Legalabb 2 red flag kimutathato.
7. A trace panelbol latszik a claim-source elteres.
8. A rendszer review required allapotot mutat.
9. A vegere letoltheto vagy megtekintheto evidence package van.
10. A teljes demo 3 perc alatt lefut.

## Demo script rovid vazlat

1. Feltoltjuk a sustainability statementet es a supporting source file-okat.
2. Elinditjuk az auditot.
3. Megmutatjuk, hogy az Orchestrator feldarabolja a munkat.
4. Megmutatjuk, hogy a Parser kinyeri a claim-eket.
5. Megmutatjuk, hogy a Tracer visszamegy a source file-okhoz.
6. Megmutatjuk, hogy a Validator determinisztikusan kiszamolja az elterest.
7. Kiemejuk a material red flag-eket.
8. Megmutatjuk az evidence package-et.

## Zaro mondat a pitchhez

Az Atlas nem egy ujabb sustainability chatbot. Az Atlas egy agentic audit trail rendszer, amely a CSRD audit legdragabb es leglassabb reszet - a forrasvisszakeresest es az ellentmondasok feltarasat - gyorsitja fel audit-grade minosegben.
