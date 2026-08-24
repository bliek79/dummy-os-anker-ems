# Dummy OS EMS 0.0.1-alpha.57

## Release title
Automatic Execution Monitor

## Git tag
`v0.0.1-alpha.57`

## Doel
Alpha57 voegt uitsluitend een read-only observabilitylaag toe bovenop de known-good alpha56-basis. De release is bedoeld om de eerste natuurlijke `automatic_72h_planner` fysieke run volledig te kunnen volgen zonder de planner, prijslaag, reserveberekening, Safety Guard of Anker-aansturing inhoudelijk te wijzigen.

## Nieuw

### `sensor.dummy_os_ems_execution_monitor`
Centrale live monitor met onder andere:
- monitorstatus: `waiting`, `blocked`, `ready_disarmed`, `armed_ready`, `arming`, `executing` of `stopping`;
- actuele execution stage uit de automatische stage trace;
- arm-status en technische readiness;
- geselecteerd planner-slot en planner identity;
- actie, purpose, gevraagd vermogen en target SOC;
- actuele SOC;
- werkelijk gemeten laad- en ontlaadvermogen;
- actuele Anker operating mode;
- resterende runtime en start/stop timestamps;
- pre-mode en post-mode readiness inclusief reden en stabiliteitstijd;
- control-path status;
- actuele blockers en warnings;
- samenvatting van de laatst afgeronde automatische run;
- compacte Plan-vs-Actual uitkomsten van de laatste run.

### `sensor.dummy_os_ems_execution_preflight`
Read-only samenvatting van de al bestaande uitvoeringsvoorwaarden:
- automatische actie geselecteerd;
- Pre-Start safe;
- Safety handoff safe;
- Execution handoff ready;
- Final Revalidation safe;
- Mode-Switch preview ready;
- Plan72 execution buffer safe;
- forecast ready;
- control path configured/ready;
- physical test idle;
- execution idle;
- manual override clear;
- trading price confidence toegestaan.

De sensor geeft daarnaast `passed_checks`, `total_checks`, blockers en warnings. De preflight bepaalt zelf niets en kan geen fysieke actie starten of blokkeren; hij presenteert uitsluitend bestaande gates.

## Bewust niet gewijzigd
- Plan72-strategie en 72-uurs horizon;
- native Stroomvoorspeller-prijslaag en markups;
- dynamische reserve en 2 procentpunt execution buffer;
- Automatic Plan Bridge;
- drie persistente planslots en manual priority;
- Scheduler en alpha53 expiry reconciliation;
- Pre-Start, Safety Guard en Final Revalidation;
- two-stage Anker readiness;
- alpha54 guarded physical execution en safe-stop;
- alpha55 Execution Audit;
- alpha56 Plan-vs-Actual.

## Validatie na installatie
1. Controleer dat de integratie versie `0.0.1-alpha.57` meldt.
2. Controleer dat `sensor.dummy_os_ems_execution_monitor` bestaat.
3. Controleer dat `sensor.dummy_os_ems_execution_preflight` bestaat.
4. Controleer dat Plan72 nog `count=72` en `valid=true` toont wanneer brondata geldig zijn.
5. Controleer dat de native prijsforecast nog uurvariatie toont en `direct_forecast_available=true` blijft.
6. Controleer dat exact drie persistente planslots aanwezig blijven en manual priority ongewijzigd is.
7. Controleer dat de Automatic Execution switch zijn bestaande status behoudt.
8. Laat de eerste natuurlijke automatische actie plaatsvinden; start geen extra fysieke test uitsluitend voor alpha57.
9. Volg tijdens die run de monitorstatus/stage, pre/post-mode readiness, operating mode, werkelijk batterijvermogen en blockers/warnings.
10. Controleer na afloop Execution Audit en Plan-vs-Actual tegen de monitor-last-run velden.

## Verwachte status vóór de eerste natuurlijke run
Wanneer geen automatische actie startklaar is, is `sensor.dummy_os_ems_execution_preflight` normaal `waiting_action`. De monitor staat dan normaal op `waiting`. Dit is geen fout.

## Rollback
Bij onverwacht gedrag kan rechtstreeks worden teruggekeerd naar de complete alpha56 release. Alpha57 wijzigt geen opslagformaat van plans, execution audit of Plan-vs-Actual en introduceert geen nieuwe write-call naar de Anker.
