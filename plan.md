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
