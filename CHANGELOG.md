## 0.0.1-alpha.53

- Fixes automatic plan-slot expiry reconciliation using the Scheduler's own `verlopen` decision as the primary release signal.
- Planner-owned `pending` slots that the Scheduler marks expired are released in the same coordinator cycle, so the Automatic Plan Bridge can reuse the slot immediately.
- Keeps an independent timestamp/window expiry check in the Plan Store as a fallback.
- Manual plans are never automatically cleared by this reconciliation.
- Re-evaluates the Scheduler after cleanup before Bridge evaluation, preventing a stale expired slot from remaining visible/occupied until a later poll.
- Adds diagnostics `scheduler_expired_slots`, `expired_release_changed`, and `expired_released_slots` to the bridge diagnostics.
- Leaves the native Stroomvoorspeller 168-hour price path from alpha52.3 unchanged.
- Leaves Plan72 strategy, execution-buffer rules, manual priority, three-slot capacity and Anker two-stage control-path readiness unchanged.
- Automatic physical execution remains disabled/shadow-only.
- README remains release-independent.

## 0.0.1-alpha.52.3

- Moves the multi-day hourly price forecast into Dummy OS EMS itself instead of consuming the legacy package sensor `sensor.forecast_prices_all_in_data`.
- Fetches the native Stroomvoorspeller 7-day hourly forecast directly from `https://stroomvoorspeller.nl/data/forecast.json` with a 30-minute cache.
- Converts the raw Stroomvoorspeller market forecast from EUR/MWh to EUR/kWh inside the integration.
- Keeps `sensor.stroomvoorspeller_data` `today`/`tomorrow` hourly market prices authoritative as `known` prices.
- Uses the direct hourly forecast for later Plan72 hours as `forecast`, then applies the configured Dummy OS EMS import/export markups exactly once.
- Removes the alpha52.2 runtime dependency on the package forecast sensor for hourly shaping.
- Keeps Stroomvoorspeller daily model averages only as a transparent degraded fallback when the native hourly feed is unavailable.
- Adds Plan72 diagnostics for direct-forecast availability, hour count, generation timestamp, last successful fetch and fetch error.
- Planner source-change detection now includes the native forecast generation timestamp so a new Stroomvoorspeller model run can trigger a Plan72 refresh.
- README remains release-independent; no alpha/update section is added.
- No scheduler, slot-lifecycle, Anker control-path or physical execution logic changes are included in this release.
- Automatic physical execution remains disabled/shadow-only.

## 0.0.1-alpha.52.2

- Releases expired planner-owned automatic plan slots after their complete Scheduler start window, allowing the Automatic Plan Bridge to reuse them without a manual reset to `geen`.
- Manual expired plans remain protected and are never silently cleared by the automatic planner.
- Restores recursive extraction of timed Stroomvoorspeller forecast rows so an available hourly/quarter-hour forecast is no longer flattened to a daily tariff.
- When Stroomvoorspeller only exposes a daily market estimate, uses the configured hourly forecast only as an intra-day shape and rebases it around the Stroomvoorspeller daily market estimate.
- Keeps a flat daily estimate only as a final fallback when no hourly forecast shape is available.
- Adds diagnostics for shaped versus unshaped daily forecast fallback hours.
- Rewrites README as a stable project/architecture description; release-specific alpha updates remain only in CHANGELOG and GitHub Releases.
- Keeps alpha52 two-stage Anker readiness and alpha52.1 execution-buffer accounting unchanged.
- Automatic non-zero physical execution remains disabled/shadow-only.

## 0.0.1-alpha.52.1

- Fixed Plan72 safety-precharge capacity accounting when solar charging and grid safety charging share the same hourly charge-power limit.
- The safety pre-planner now subtracts forecast solar-surplus input from the charge-input headroom available for grid safety charging.
- Prevents an execution-reserve miss such as SOC 79.9% versus required 80.9% during a partially elapsed hour.
- Keeps the 2 percentage-point execution buffer strict; no safety gate was relaxed.
- Keeps alpha52 two-stage Anker control-path readiness unchanged.
- Automatic physical execution remains disabled; shadow-only behavior is unchanged.

## 0.0.1-alpha.52

- Added two-stage Anker control-path readiness for automatic execution shadow validation.
- Pre-mode readiness now requires only the operating-mode select to be configured, available and stable for 60 seconds.
- Direction and power-setpoint are treated as post-mode requirements while the device remains in self_consumption.
- Added explicit `pre_mode_ready`, `pre_mode_reason`, `post_mode_ready`, `post_mode_reason`, and post-mode-required diagnostics.
- Added control-entity detail diagnostics to the Automatic Execution Shadow sensor.
- `awaiting_third_party_control` is now reported instead of treating unavailable direction/setpoint in self_consumption as a control-path failure.
- Automatic physical execution remains deliberately disabled; shadow execution only.
- Updated integration version to 0.0.1-alpha.52.

## 0.0.1-alpha.51.1

- Naming correction before first install: the new arm switch is now `Dummy OS EMS Automatic Execution` instead of the accidental Dutch label.
- This ensures Home Assistant creates the intended entity ID `switch.dummy_os_ems_automatic_execution` on first install rather than a temporary Dutch entity ID.
- No planner, safety, scheduler, or physical execution logic changed.

- Added native `Dummy OS EMS Automatic Execution` fail-safe arm switch.
- Added final end-to-end automatic execution shadow gate.
- Added `Dummy OS EMS Automatic Execution Ready` binary sensor.
- Added `Dummy OS EMS Automatic Execution Shadow` diagnostic command sensor.
- Manual execution has priority over future automatic execution.
- Trading execution is blocked unless every price source hour is `known`.
- Control path must be available and stable before shadow readiness can become true.
- Automatic physical non-zero execution remains deliberately disabled in alpha51.1.
- Persist planner price-source confidence into planner-owned plan slots.
- Updated integration version to 0.0.1-alpha.51.1.

# Changelog

## 0.0.1-alpha.50.2 - 2026-08-21

- Functional market-price horizon fix: Stroomvoorspeller `forecast.days` is now used when exact `today`/`tomorrow` prices are unavailable.
- Daily `average_market_estimate` values are expanded over the corresponding local day so the 72-hour planner no longer receives `null` prices outside the published day-ahead window.
- Exact known `today.hours` / `tomorrow.hours` prices keep precedence over the daily model estimate.
- Import and export markups remain independently applied by Dummy OS EMS.
- No physical execution changes; automatic execution remains disabled in this alpha.

## 0.0.1-alpha.50.1 - 2026-08-21

### Stroomvoorspeller parserfix
- Leest nu expliciet het veld `market` uit `today.hours` en `tomorrow.hours` van `sensor.stroomvoorspeller_data`.
- Hierdoor kan de nieuwe prijsarchitectuur de echte marktprijsregels daadwerkelijk vullen in plaats van terug te vallen op legacy bekende/forecastprijzen.
- Import- en exportprijs blijven worden berekend als marktprijs plus de afzonderlijk ingestelde markup.
- Geen wijziging aan plannerstrategie, reserveberekening of fysieke batterijuitvoering.

## 0.0.1-alpha.50 - 2026-08-21

### Functionele prijslaag
- Activeert de ingestelde marktprijsbron, importmarkup en exportmarkup als primaire prijslaag voor de EMS-forecast en planner.
- Corrigeert quarter-hour brondata: vier kwartierprijzen binnen hetzelfde uur worden nu gemiddeld naar één uurprijs in plaats van dat de laatste kwartierwaarde stilzwijgend het hele uur overschrijft.
- Bekende marktprijzen houden voor hetzelfde uur voorrang op forecastprijzen.
- Corrigeert bronvalidatie: wanneer de nieuwe marktprijsarchitectuur geldige data levert, wordt de prijsbron niet meer ten onrechte als ontbrekend gemarkeerd omdat de legacy prijsentiteiten leeg zijn.
- Voegt diagnostiek toe voor ruwe marktprijsregels, geaggregeerde uren en kwartierdekking.
- De 72-uursplanner blijft bewust op uurblokken draaien; bij gekozen 15-minutenprijsresolutie wordt de marktprijslaag veilig naar uurprijzen geaggregeerd. Een echte 15-minutenplanner volgt pas in een aparte functionele migratie.
- Geen cosmetische wijzigingen en geen wijziging aan fysieke uitvoering.

## 0.0.1-alpha.49.3

- Herstelt de Options Flow naar de door Home Assistant voorgeschreven `init`-stap.
- Verwijdert de tijdelijke `settings`-redirect uit alpha49.1/49.2.
- Verwijdert `strings.json`; custom integrations gebruiken runtimebestanden in `translations/`.
- Houdt volledige `translations/nl.json` en `translations/en.json` aan met Nederlandse/Engelse veldlabels.
- Voegt een compatibele `config.step.init`-mirror toe als fallback naast `options.step.init`.
- Verwijdert meegeleverde `__pycache__`/`.pyc`-bestanden uit de release.
- Geen wijziging aan opgeslagen waarden, plannerlogica of fysieke batterijbesturing.

## 0.0.1-alpha.49.2 - 2026-08-21

- Fixes Options Flow field translations for the custom integration by adding the required `translations/en.json` baseline.
- Keeps the Dutch `translations/nl.json` translation and the `settings` step from alpha49.1.
- No functional changes to stored settings, pricing logic, planner, Scheduler, Safety Guard or physical execution.
- This specifically addresses raw field keys such as `electrical_profile`, `import_markup_per_kwh` and `tariff_resolution` being shown in Home Assistant.

# Changelog

## 0.0.1-alpha.49.1 - 2026-08-21

### Fixed
- Options Flow gebruikt nu een nieuwe productie-step-id `settings` in plaats van de historisch gecachte `init`-weergave.
- Hierdoor vraagt Home Assistant de actuele titel, beschrijving en veldlabels opnieuw op en kunnen oude alpha46/diagnostische teksten niet meer aan de bestaande `init`-vertalingssleutel blijven hangen.
- De werkende configuratie en opslag uit alpha49 blijven inhoudelijk ongewijzigd.
- `init` blijft intern als compatibele ingang bestaan en verwijst direct door naar `settings`.

### Validation
- Python compile-check: geslaagd.
- JSON-validatie: geslaagd.
- ZIP-integriteitscontrole: geslaagd.

## 0.0.1-alpha.49 - 2026-08-21

### Options Flow productieteksten en vertalingen
- Alpha48 is live gevalideerd: 60- en 15-minutenresolutie openen, slaan op en blijven na opnieuw openen behouden.
- Verwijdert alle tijdelijke alpha-, stap- en diagnostische teksten uit de zichtbare Options Flow.
- Titel is nu definitief **EMS instellingen**.
- Beschrijving is herschreven als normale gebruikersuitleg voor elektrische limieten en prijsinstellingen.
- Hernoemt **Nieuwe marktprijsarchitectuur gebruiken** naar **Marktprijsarchitectuur gebruiken**.
- Synchroniseert `translations/nl.json` met de actuele Options Flow, inclusief exportmarkup en prijsresolutie. Hierdoor verschijnen geen technische sleutel-namen meer wanneer Home Assistant de Nederlandse vertaling gebruikt.
- Behoudt exact dezelfde acht gevalideerde velden en dezelfde opslaglogica uit alpha48.
- Import- en exportmarkup blijven `0.1288 €/kWh`; bestaande opgeslagen waarden blijven leidend.
- Geen wijziging aan prijsberekening, planner, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.49` toont.
2. Open **Configureren**.
3. Verwacht de titel **EMS instellingen**, zonder alpha-/test-/staptekst.
4. Controleer dat alle acht velden duidelijke Nederlandse labels hebben.
5. Klik **Verzenden** en open **Configureren** opnieuw.
6. Controleer dat alle eerder opgeslagen waarden ongewijzigd behouden blijven.

## 0.0.1-alpha.48

- Behoudt alle live gevalideerde Options Flow-velden uit alpha47.
- Voegt uitsluitend `tariff_resolution` toe als veilige dropdown.
- Keuzes: `hourly` (60 minuten) en `quarter_hourly` (15 minuten).
- Standaard blijft 60 minuten voor bestaande installaties zonder opgeslagen keuze.
- Opgeslagen keuze krijgt altijd voorrang bij opnieuw openen van Configureren.
- Geen wijziging aan planner-, scheduler-, Safety Guard-, Execution Controller- of fysieke batterijlogica.
- Import- en exportmarkup blijven HA-veilig via Voluptuous floatvalidatie en staan standaard op 0,1288 €/kWh.

## 0.0.1-alpha.47 - 2026-08-21

### Options Flow rebuild - stap 6: exportmarkup
- Alpha46.1 is live geslaagd: de HA-veilige numerieke invoer voor `import_markup_per_kwh` opent zonder 400-fout en blijft na opslaan op `0.1288 €/kWh` staan.
- Daarmee is de eerdere 400-fout reproduceerbaar herleid tot de fijnmazige Home Assistant `NumberSelector`-opbouw voor markupvelden.
- Alpha47 behoudt de zes live gevalideerde velden en voegt uitsluitend `export_markup_per_kwh` toe.
- Exportmarkup gebruikt exact dezelfde veilige Voluptuous float-validatie als de importmarkup (`vol.Coerce(float)` + bereik -1.0 t/m 2.0).
- De actuele exportmarkup voor deze installatie is ingesteld op `0.1288 €/kWh`.
- Bestaande opgeslagen exportmarkup krijgt voorrang; fallback is `0.1288`.
- Importmarkup blijft `0.1288 €/kWh` en alle eerder bewezen Options blijven behouden.
- Uur-/kwartierresolutie is nog niet toegevoegd en volgt als afzonderlijke vervolgstap.
- Geen wijziging aan Plan72, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.47` toont.
2. Open **Configureren**.
3. Verwacht zeven velden; onderaan staan **Importmarkup** en **Exportmarkup**.
4. Voor de huidige installatie verwacht je voor beide `0.1288 €/kWh`.
5. Klik **Verzenden** en open **Configureren** opnieuw.
6. Controleer dat beide markupwaarden behouden blijven.
7. Indien succesvol: de volgende stap voegt uitsluitend de keuze **60 minuten / 15 minuten** toe.

## 0.0.1-alpha.46.1 - 2026-08-21

- Reparatie van de Options Flow na de live vastgestelde 400-fout in alpha46.
- Oorzaak geïsoleerd tot de `NumberSelector` voor `import_markup_per_kwh` met `step=0.0001` en/of de selector-unit in Home Assistant 2026.8.
- Vervangt uitsluitend dat markupveld door een eenvoudige Voluptuous float-validatie (`vol.Coerce(float)` + bereik -1.0 t/m 2.0).
- De opgeslagen waarde blijft een echte float; standaard blijft `0.1288` €/kWh.
- De unit staat nu in het veldlabel in plaats van in de NumberSelector.
- Alle in alpha45 bewezen velden en opslaglogica blijven ongewijzigd.
- Exportmarkup en 15/60-minutenkeuze zijn nog niet toegevoegd.
- Geen wijziging aan planner, scheduler, safety guard, execution controller of fysieke batterijbesturing.

## 0.0.1-alpha.46 - 2026-08-21

### Options Flow rebuild - stap 5: importmarkup
- Alpha45 is live geslaagd: `market_price_entity` opent correct, slaat op en blijft op `sensor.stroomvoorspeller_data` staan na opnieuw openen.
- Behoudt de vijf gevalideerde velden en voegt uitsluitend `import_markup_per_kwh` toe.
- De actuele importmarkup voor deze installatie is ingesteld op `0.1288 €/kWh`.
- Het veld gebruikt een Home Assistant NumberSelector met vier decimalen nauwkeurigheid (`step=0.0001`).
- Toegestaan bereik: `-1.0` tot `2.0 €/kWh`, zodat ook negatieve of hogere contractcorrecties later mogelijk blijven.
- Bestaande waarde wordt gelezen uit options, met fallback naar config-entry data en daarna `0.1288`.
- De door de gebruiker opgegeven actuele exportmarkup is eveneens `0.1288 €/kWh`, maar blijft in alpha46 bewust nog verborgen; die volgt als losse alpha47-stap.
- Bestaande verborgen options blijven behouden bij opslaan.
- Nog geen exportmarkup of uur-/kwartierresolutie zichtbaar.
- Geen wijzigingen aan Plan72, prijsberekening, Plan Store, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.46` toont.
2. Open **Configureren**.
3. Verwacht zes velden: **Aansluitprofiel**, **Maximaal laadvermogen**, **Maximaal ontlaadvermogen**, **Nieuwe marktprijsarchitectuur gebruiken**, **Marktprijsbron** en **Importmarkup**.
4. Voor de huidige installatie verwacht: **Eigen groep**, **3200 W**, **3200 W**, schakelaar aangevinkt, `sensor.stroomvoorspeller_data` en importmarkup `0.1288 €/kWh`.
5. Klik **Verzenden** en open **Configureren** opnieuw.
6. Controleer dat alle zes waarden behouden blijven.
7. Indien succesvol: alpha47 voegt als volgende losse stap uitsluitend de exportmarkup toe, met actuele waarde `0.1288 €/kWh`.

## 0.0.1-alpha.45 - 2026-08-21

### Options Flow rebuild - stap 4: marktprijsbron
- Alpha44 is live geslaagd: de marktprijsarchitectuur-schakelaar opent correct, slaat op en blijft aangevinkt na opnieuw openen.
- Behoudt de vier gevalideerde velden en voegt uitsluitend `market_price_entity` toe.
- De marktprijsbron gebruikt een Home Assistant EntitySelector beperkt tot het domein `sensor`.
- Bestaande waarde wordt gelezen uit options, met fallback naar config-entry data en daarna `sensor.stroomvoorspeller_data`.
- Bestaande verborgen options blijven behouden bij opslaan.
- Nog geen importmarkup, exportmarkup of uur-/kwartierresolutie zichtbaar; die worden daarna één voor één teruggebracht.
- Geen wijzigingen aan Plan72, prijsberekening, Plan Store, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.45` toont.
2. Open **Configureren**.
3. Verwacht vijf velden: **Aansluitprofiel**, **Maximaal laadvermogen**, **Maximaal ontlaadvermogen**, **Nieuwe marktprijsarchitectuur gebruiken** en **Marktprijsbron**.
4. Voor de huidige installatie verwacht: **Eigen groep**, **3200 W**, **3200 W**, schakelaar aangevinkt en marktprijsbron `sensor.stroomvoorspeller_data` wanneer die nog niet eerder anders is opgeslagen.
5. Klik **Verzenden** en open **Configureren** opnieuw.
6. Controleer dat alle vijf waarden behouden blijven.
7. Indien succesvol: alpha46 voegt als volgende losse stap uitsluitend de importmarkup toe.

## 0.0.1-alpha.44 - 2026-08-21

### Options Flow rebuild - stap 3: marktprijsarchitectuur-schakelaar
- Alpha43 is live geslaagd: aansluitprofiel en beide vermogenslimieten openen correct met **Eigen groep**, **3200 W laden** en **3200 W ontladen**.
- Behoudt de drie gevalideerde basisvelden en voegt uitsluitend `market_price_architecture_enabled` toe.
- De schakelaar leest de bestaande waarde uit options, met fallback naar config-entry data en daarna `false`.
- Bestaande verborgen options blijven behouden bij opslaan.
- Nog geen prijsbron, importmarkup, exportmarkup of uur-/kwartierresolutie zichtbaar; die worden daarna één voor één teruggebracht.
- Geen wijzigingen aan Plan72, prijsberekening, Plan Store, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.44` toont.
2. Open **Configureren**.
3. Verwacht vier velden: **Aansluitprofiel**, **Maximaal laadvermogen**, **Maximaal ontlaadvermogen** en **Nieuwe marktprijsarchitectuur gebruiken**.
4. Voor de huidige installatie verwacht: **Eigen groep**, **3200 W**, **3200 W**.
5. De nieuwe schakelaar mag uit staan wanneer hij nog niet eerder was opgeslagen.
6. Klik **Verzenden** en open **Configureren** opnieuw.
7. Controleer dat alle vier waarden behouden blijven.
8. Indien succesvol: alpha45 voegt als volgende losse stap de marktprijsbron toe.

## 0.0.1-alpha.43 - 2026-08-21

### Options Flow rebuild - stap 2: centrale vermogenslimieten
- Alpha42 is live geslaagd: `electrical_profile` opent, slaat op en blijft behouden na opnieuw openen.
- Behoudt `electrical_profile` en voegt uitsluitend `max_charge_power_w` en `max_discharge_power_w` toe.
- Huidige eigen-groepwaarden blijven 3200 W laden en 3200 W ontladen.
- NumberSelectors gebruiken 100 W stappen en de absolute technische bovengrens uit de centrale constants.
- Bij `shared_group` blijft de bestaande 800 W fail-safe via validatie van kracht.
- Bestaande verborgen options blijven behouden bij opslaan.
- Geen wijzigingen aan Plan72, prijslogica, Plan Store, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.43` toont.
2. Open **Configureren**.
3. Verwacht drie velden: **Aansluitprofiel**, **Maximaal laadvermogen** en **Maximaal ontlaadvermogen**.
4. Voor de huidige installatie verwacht: **Eigen groep**, **3200 W**, **3200 W**.
5. Klik **Verzenden** en open **Configureren** opnieuw.
6. Controleer dat alle drie waarden behouden blijven.
7. Indien succesvol: alpha44 voegt als volgende losse stap alleen de schakelaar voor de nieuwe marktprijsarchitectuur toe.

## 0.0.1-alpha.42 - 2026-08-21

### Options Flow rebuild - stap 1: aansluitprofiel
- Alpha41 is live geslaagd: de diagnostische minimale Options Flow opent op Home Assistant Core 2026.8.2.
- Verwijdert het tijdelijke diagnostische booleanveld uit de Options Flow.
- Brengt als eerste echte instelling uitsluitend `electrical_profile` terug.
- Gebruikt hiervoor de bestaande Home Assistant `SelectSelector` met `dedicated_group` en `shared_group`.
- Leest de huidige waarde veilig uit `config_entry.options`, met fallback naar `config_entry.data` en daarna de standaardwaarde.
- Bij opslaan worden bestaande verborgen options behouden.
- Geen wijzigingen aan Plan72, prijslogica, Plan Store, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.42` toont.
2. Open **Configureren**.
3. Verwacht precies één veld: **Aansluitprofiel**.
4. Voor de huidige installatie hoort **Eigen groep** geselecteerd te zijn.
5. Sla de instelling op en open **Configureren** opnieuw.
6. Verwacht dat **Eigen groep** behouden blijft.
7. Indien opnieuw `400 Bad Request`: de `SelectSelector`/waardeopbouw van `electrical_profile` is de eerstvolgende verdachte.
8. Indien succesvol: alpha43 brengt uitsluitend de twee vermogenslimieten terug.

## 0.0.1-alpha.41 - 2026-08-21

### Options Flow isolation recovery
- Bevestigt alpha40.9 als nog niet opgelost: Home Assistant 2026.8.2 bleef `400 Bad Request` geven voordat het formulier verscheen.
- Brengt de Options Flow terug tot de kleinst mogelijke bruikbare vorm met één gewone boolean en zonder selectors of config-entry reads tijdens form creation.
- Houdt `@staticmethod` + `@callback` op `async_get_options_flow()`, overeenkomstig de actuele Home Assistant Options Flow API.
- Bestaande options worden alleen bij expliciet opslaan gemerged en blijven anders onaangeraakt.
- Geen wijzigingen aan Plan72, Automatic Plan Bridge, Plan Store, Scheduler, Safety Guard, Execution Controller of fysieke batterijbesturing.
- Doel: onderscheid maken tussen een fout in de HA Options Flow route/registratie en een fout in de uitgebreide alpha40.8/40.9 schema-opbouw.

### Live validatie
1. Controleer dat Home Assistant `0.0.1-alpha.41` toont.
2. Klik op **Configureren**.
3. Verwacht: het formulier opent met exact één testoptie.
4. Niet opslaan is voldoende voor deze eerste test.
5. Indien nog steeds 400: probleem zit vóór de schema-opbouw; volgende stap is flowregistratie/config-entry-route onderzoeken.
6. Indien het formulier opent: probleem zit in de uitgebreide options-schema-opbouw; daarna velden één voor één terugbrengen.

# Changelog

## 0.0.1-alpha.40.9 - HA 2026.8 Options Flow Callback Fix

- Restores the required Home Assistant `@callback` decorator on `async_get_options_flow`, which was documented in alpha40.7 but accidentally missing again in alpha40.8.
- Keeps the alpha40.8 minimal Options Flow and its eight core fields unchanged.
- Synchronizes the internal `const.py` version with the manifest; alpha40.8 incorrectly still reported alpha40.7 internally.
- No planner, safety, scheduler, execution, entity-count or physical-control behavior is changed.
- Validation target: Home Assistant Core 2026.8.2.

## 0.0.1-alpha.40.7

### Config flow hardening
- Rebuilt the Options Flow using Home Assistant's current `self.config_entry` and `add_suggested_values_to_schema` pattern.
- Added the required `@callback` marker to `async_get_options_flow`.
- Separated optional EMS tuning from setup-critical Anker source reconfiguration.
- Reconfigure now uses `async_update_and_abort`, avoiding a double reload with the existing config-entry update listener on HA 2026.6+.
- Added `translations/nl.json` with the same flow structure as `strings.json`.
- Preserves alpha40.5 Control Path Readiness and alpha40.4 Recorder optimizations.
- No expansion of automatic non-zero battery actuation.

## 0.0.1-alpha.40.6 - Reconfigure Flow Fix

- Added a native Home Assistant `async_step_reconfigure` flow for the pencil/edit action.
- Reconfigure now exposes Anker source entities, electrical limits and the supplier-independent price settings in one form.
- Existing config-entry data and options are preserved and updated in place; no duplicate EMS entry is created.
- Successful changes schedule a reload of the same config entry.
- Keeps alpha40.5 Control Path Readiness Guard and alpha40.4 Recorder optimizations unchanged.
- Keeps the entity count at 105 and does not expand physical automatic power control.


## 0.0.1-alpha.40.5

- Herstelt de Options Flow / Configureren-pagina voor de alpha40.3 prijsarchitectuur.
- Marktprijsbron, importmarkup, exportmarkup en uur-/kwartierresolutie zijn weer configureerbaar.
- Voegt een Control Path Readiness Guard toe voor de trager opstartende Anker-besturing.
- Automatische mode-switch raakt de batterij pas aan nadat modus, richting en vermogenssetpoint minimaal 60 seconden beschikbaar en stabiel zijn.
- Een nog niet gereed control path wordt als normale startup-conditie behandeld en markeert de planneractie niet als mislukt.
- Bestaande Plan72- en forecast Recorder-optimalisaties blijven behouden.
- Geen uitbreiding van niet-nul automatische laad-/ontlaadbesturing; alpha40 fysieke scope blijft ongewijzigd.
- Aantal entiteiten blijft 105.

## 0.0.1-alpha.40.4 - Forecast Recorder Optimization

- Fixes repeated Recorder warnings for `sensor.dummy_os_ems_forecast_status` exceeding Home Assistant's 16,384-byte state-attribute limit.
- Keeps the full live `forecast` attribute available on Forecast Status for diagnostics, but marks it as unrecorded so Recorder stores only the compact attributes.
- Preserves the alpha40.2 Plan72 recorder optimization; both heavy live payloads (`plan` and `forecast`) are now excluded from history.
- Replaces the stale Alpha27 Plan72 note with a version-neutral description of the current execution-buffer/reserve behavior.
- Preserves the alpha40.3 supplier-independent price architecture, separate import/export markups and hourly/quarter-hour tariff-resolution setting.
- No change to the alpha40 controlled physical mode-switch scope; automatic non-zero charge/discharge execution remains disabled.
- No entities are added or removed; entity count remains 105.

## 0.0.1-alpha.40.3 - Price Architecture Foundation

- Adds opt-in supplier-independent market-price architecture using `sensor.stroomvoorspeller_data`.
- Adds configurable import and export markup in Options Flow.
- Adds tariff resolution selection (`hourly` / `quarter_hourly`).
- Splits planner pricing into `market_price`, `import_price` and `export_price`.
- Safety/grid charging uses import price; grid trade discharge uses export price.
- Keeps the legacy EnergyZero + forecast price path as fail-safe fallback until the new price layer is explicitly enabled and live-validated.
- Quarter-hour selection is persisted as architecture input, but alpha40.3 still runs the 72h planner effectively hourly; 15-minute planner execution is not enabled yet.
- No change to alpha40/40.1 physical execution scope.


## 0.0.1-alpha.40.2 - Plan72 Refresh & Recorder Optimization

- Keeps the coordinator on its fast 10-second cadence for live safety, Scheduler and execution state, while caching the expensive 72-hour planner result.
- Limits periodic 72-hour planner recalculation to at most once per local hour between 05:00 and 22:00.
- Disables periodic 72-hour planner recalculation between 22:00 and 05:00.
- Allows immediate extra planner recalculation on relevant source-content changes, forecast recovery, integration startup and start-critical automatic-plan transitions.
- Counts an event-driven refresh inside the active hour as that hour's periodic refresh to avoid a redundant second calculation.
- Keeps the full live `plan` payload only on `sensor.dummy_os_ems_plan72_hours`; the remaining Plan72 sensors now expose compact summary attributes.
- Marks the large `plan` attribute as unrecorded using Home Assistant's supported entity-level recorder exclusion, while keeping it available live for the dashboard graph.
- Adds Plan72 refresh diagnostics: policy, cached state, refresh reason, last refresh time and refresh count today.
- Preserves alpha40.1 planner-outage persistence behavior and alpha40 controlled physical mode-switch scope.
- No entities are added or removed; entity count remains 105.

## 0.0.1-alpha.40.1 - Planner Outage Persistence Fix

- Preserves existing planner-owned concept/pending plans when planner, forecast or execution-buffer gates are temporarily unavailable.
- Prevents a transient startup/source outage from being interpreted as an authoritative empty planner result.
- Stale automatic-plan cleanup still runs when the planner gate is open and a valid current planner result explicitly contains no matching action.
- Adds `auto_bridge_plan_store_preserved_due_gate_closed` diagnostics to the existing Action Candidates sensor.
- Keeps the Alpha40 controlled physical mode-switch scope unchanged: 0 W guard, `third_party_control`, post-mode revalidation and safe return only; no direction or non-zero automatic power command.
- Entity count remains 105.

## 0.0.1-alpha.40 - Controlled Physical Mode Switch

- Enables the first narrowly scoped physical step in the automatic planner chain.
- Requires the existing start-ready Scheduler selection, authoritative Pre-Start gate, Safety Guard, Execution Controller handoff, Final Live Revalidation and Mode Switch Preview to all be ready.
- Applies a 0 W zero-power guard before changing operating mode.
- Physically switches to `third_party_control`, waits for external controls, and revalidates the complete live chain.
- Never selects charge/discharge direction and never applies a non-zero automatic power setpoint.
- Immediately returns to `self_consumption` after a successful validation, and also attempts zero-power + `self_consumption` on any failure.
- Persists the last handled `planner_identity` so the same automatic plan is not mode-switched repeatedly, including after Home Assistant restart.
- Blocks concurrent manual execution and physical tests while the mode-switch transaction is active.
- Adds live mode-switch transaction status attributes to the existing Action Candidates sensor; entity count remains 105.

## 0.0.1-alpha.39

### Mode Switch Transaction Preview
- Adds an explicit observer-only transaction preview after Final Live Revalidation.
- Defines the future safe sequence: zero-power guard, `third_party_control` switch, wait for external controls, post-mode revalidation, direction/power handoff, and guaranteed safe return to `self_consumption`.
- Exposes readiness, blockers, current mode, current setpoint and zero-power-guard requirement on Action Candidates.
- Does not call Home Assistant control services. Automatic physical execution remains disabled.
- Entity count remains unchanged.

## 0.0.1-alpha.39 - Final Live Revalidation Preview

- Added a final non-actuating live revalidation stage after the Execution Controller handoff preview.
- Rechecks Scheduler selection, planner identity/revision, authoritative pre-start state, Safety Guard state, forecast readiness and execution-buffer safety.
- Revalidates configured charge/discharge limits, live SOC versus target, discharge execution reserve, control-path readiness and conflicting battery power.
- Exposes detailed final-revalidation checks, blockers, warnings and timestamp on the existing Action Candidates sensor.
- External-mode transition remains a warning/next-stage requirement; no mode switch or battery command is issued.
- Automatic execution permission and physical control remain disabled.
- Entity count remains 105.
- README remains a compact current-state guide; release history stays in this changelog and GitHub Releases.

# Changelog

## 0.0.1-alpha.37 - Safety Guard to Execution Controller Handoff Preview

- Adds the first automatic, non-actuating Safety Guard -> Execution Controller handoff preview.
- Requires an automatic Scheduler-ready plan and a successful Safety Guard handoff before the execution handoff can become ready.
- Revalidates planner identity, action, configured power limits, target SOC, runtime, control-path configuration, physical-test idle state and Execution Controller idle state.
- Exposes the selected slot, action, power, target SOC, runtime, blockers and warnings through the existing Action Candidates sensor attributes.
- Treats the future external-mode switch as an expected warning rather than performing it.
- Marks final live revalidation as mandatory before any future physical command path may be enabled.
- Keeps `execution_permitted` and physical control explicitly false; no Home Assistant control service is called by this new path.
- Keeps centralized configurable charge/discharge limits from alpha36.3 unchanged.
- No Home Assistant entities are added or removed; entity count remains 105.

## 0.0.1-alpha.36.3 - Correct Release Packaging

- Repackages the alpha36.2 Options Flow compatibility fix from the verified corrected source tree.
- Ensures `manifest.json` and `const.py` both report `0.0.1-alpha.36.3`.
- Ensures `async_get_options_flow()` returns `AnkerEmsOptionsFlow()` without passing the config entry constructor argument.
- Ensures there is no manual `self.config_entry = config_entry` assignment in the options-flow handler.
- Keeps the v1 -> v2 config-entry migration and central electrical profile / power-limit behavior unchanged.
- Automatic planner-owned physical execution remains disabled.
- Entity count remains 105.

## 0.0.1-alpha.36.2 - Options Flow Compatibility Fix

- Fixes the Home Assistant Options Flow 500 error when opening **Configure**.
- Stops passing the config entry into the options-flow handler constructor.
- Removes the unsupported manual assignment to `self.config_entry`; Home Assistant now provides the config entry to the options flow.
- Keeps the v1 -> v2 migration from alpha36.1 unchanged.
- Keeps the central electrical profile and charge/discharge power-limit behavior from alpha36 unchanged.
- Automatic planner-owned physical execution remains disabled.
- No Home Assistant entities are added or removed; entity count remains 105.

## 0.0.1-alpha.36.1 - Config Entry Migration Fix

- Adds the missing Home Assistant `async_migrate_entry()` path for existing version 1 config entries.
- Preserves all existing configuration data during migration.
- Adds safe migration defaults: `shared_group`, 800 W charge and 800 W discharge.
- Updates the config entry to schema version 2 so Options Flow can then be used to select the real electrical profile and power limits.
- No planner, Scheduler, Safety Guard, or execution behavior is otherwise changed from alpha36.
- Automatic planner-owned physical execution remains disabled.

## 0.0.1-alpha.36 - Central Configurable Power Limits

- Adds an electrical connection profile to Config Flow: dedicated group or shared/non-dedicated group.
- Adds configurable `max_charge_power_w` and `max_discharge_power_w` values.
- Dedicated-group configuration supports up to 3500 W charge and 3500 W discharge.
- Shared/non-dedicated-group configuration is hard-capped at 800 W in both directions.
- Existing upgraded entries without an explicit profile fail safe to 800 W until configured in Options Flow.
- Applies the same central limits to planner preview, 72-hour planner, Action Bridge, Scheduler validation, pre-start validation, Safety Guard and Execution Controller.
- Manual plan power input is constrained by the configured limits.
- Keeps automatic planner-owned physical execution explicitly blocked in the legacy scheduled auto-start listener while the automatic execution phase is still under validation.
- Automatic physical execution remains disabled.
- No new Home Assistant entities are added; entity count remains 105.

## 0.0.1-alpha.35 - Scheduler to Safety Guard Handoff

- Adds the first automatic, non-actuating handoff from a Scheduler-ready planner-owned plan to the Safety Guard layer.
- Requires the authoritative pre-start gate to be active and safe before Safety Guard handoff can pass.
- Revalidates planner identity continuity, Action Bridge validity, forecast readiness, execution-buffer safety, action, power, SOC, target SOC and conflicting battery power.
- Verifies that all three configured control-path entities exist in the integration configuration without requiring `third_party_control` to be active yet.
- Blocks handoff while a physical test or another execution is active, preserving the one-controller-at-a-time principle before physical automation is enabled.
- Exposes handoff status, reasons, warnings, selected slot, identity and control-path readiness through the existing Action Candidates attributes.
- A changed planner signature remains a warning when stable planner identity still matches.
- Automatic Execution Controller handoff and physical battery commands remain disabled.
- Runtime bridge note is now version-neutral instead of carrying an old alpha number.
- Entity count remains unchanged at 105.

## 0.0.1-alpha.34 - Time-Aware Pre-Start Diagnostics

- Separated continuous early diagnostics from the authoritative Scheduler-ready pre-start gate.
- Added explicit diagnostic phase (`early`, `near_start`, `due`) and non-authoritative status metadata.
- Current SOC direction and execution-reserve failures are warnings while a plan is outside the live pre-start decision window.
- The same SOC checks become hard blockers inside the decision window and remain hard blockers for the real Scheduler-ready pre-start gate.
- Added diagnostic metadata for whether live SOC is currently enforced and the active decision-window duration.
- Dry-run safety tests now respect the same time relevance as the continuous diagnostic.
- Automatic physical execution remains disabled.
- Entity count remains unchanged at 105.
- Reworked README into a compact current-state guide; alpha-by-alpha history now remains in CHANGELOG and GitHub Releases only.

## 0.0.1-alpha.33 - Pre-Start Diagnostics & Testability

- Adds continuous dry-run pre-start diagnostics for the nearest future planner-owned pending plan.
- Exposes every individual pre-start check as structured attributes on the existing Action Candidates sensor.
- Adds diagnostic slot, start time, minutes-to-start, SOC, target SOC, execution reserve, identity/signature match, blockers and warnings.
- Adds an in-memory dry-run test matrix for current conditions plus forecast-not-ready, unsafe execution-buffer and invalid-planner scenarios.
- Keeps the actual Scheduler-ready pre-start gate unchanged in safety intent.
- No physical battery commands are enabled; automatic execution remains disabled.
- No new Home Assistant entities; entity count remains 105.

## 0.0.1-alpha.32 - Pre-Start Safety Validation

- Adds a dedicated observational pre-start safety gate for automatic Scheduler-ready plans.
- Revalidates the current 72-hour planner validity, forecast readiness, 2% execution buffer and Action Bridge validity immediately before an automatic plan would be eligible for execution.
- Requires the Scheduler-selected automatic plan to still exist in the current rolling planner by stable `planner_identity`.
- Rechecks current SOC against the stored target SOC and, for discharge actions, the current execution-reserve floor.
- Reports a changed planner revision/signature as a warning while stable planner identity remains the hard continuity requirement.
- Exposes pre-start diagnostics through the existing Action Bridge entity attributes; no new Home Assistant entities are added.
- Automatic physical execution remains disabled and no Anker command is sent by the new validator.
- Entity count remains unchanged at 105.

## 0.0.1-alpha.31 - Automatic Pending Plan Reconciliation

- Separates stable `planner_identity` from mutable `planner_signature`.
- Matches planner-owned pending plans by action identity instead of exact forecast revision.
- Reconciles future pending plans when target SOC, power or expected energy changes.
- Clears stale future planner-owned pending plans that disappear from the rolling 72-hour preview.
- Freezes automatic plans at their planned start so Scheduler-ready/due plans are not rewritten.
- Keeps manual/user-edited plans protected.
- Scheduler handoff remains enabled; automatic physical execution remains disabled.
- Entity count remains unchanged.

# 0.0.1-alpha.30

## Controlled Scheduler Handoff

- Adds the first automatic handoff from validated planner-owned Plan Store concepts to Scheduler-visible `pending` plans.
- Handoff is allowed only when the 72-hour plan is valid, the 2% execution buffer is safe, forecast sources are ready, all bridge candidates are valid, and the persistent planner signature still exactly matches the current proposal.
- Planner-owned pending slots are matched by signature on later refreshes so they are not misreported as manual conflicts.
- Manual/user-edited plans remain protected and are never promoted automatically.
- Automatic physical execution remains disabled; alpha30 stops at Scheduler handoff.
- Empty planner slots are reset with neutral/manual origin instead of retaining `automatic_72h_planner`.
- Adds bridge attributes for Scheduler handoff gate, changed state, handed-off slots and skipped slots.
- Entity count remains unchanged at 105.

# 0.0.1-alpha.29

## Controlled Automatic Plan Store Write

- The validated 72-hour Action Bridge can now persist automatic proposals into reusable Plan Store slots.
- Automatic plans are always stored with lifecycle `concept`; Scheduler handoff remains disabled and no physical execution can start from this automatic write path.
- Existing active/actionable manual plans keep priority and are never overwritten.
- Cancelled, completed, failed and empty slots remain reusable as established in alpha28.
- Planner-owned concept slots can be refreshed by the rolling automatic preview. A user edit immediately claims that slot back as `manual`.
- Stale planner-owned slots are cleared when the rolling preview no longer needs them.
- Writes are idempotent through a planner signature to avoid persistent-storage writes on every 10-second coordinator refresh.
- Existing bridge entities expose write-gate state plus written, cleared and skipped slot diagnostics; no new entities are added. Entity count remains 105.
- Alpha27 Forward Reserve Precharge and the 2% execution buffer remain required gates before automatic Plan Store write is allowed.

## Safety gates

Automatic Plan Store write requires:

- valid 72-hour plan;
- safe execution buffer;
- ready forecast sources;
- zero invalid action candidates;
- a reusable slot for the candidate.

Still disabled in alpha29:

- Scheduler handoff;
- automatic lifecycle promotion to `pending`;
- automatic physical charge/discharge execution.

# 0.0.1-alpha.28

## English entity naming cleanup
- All 105 Dummy OS EMS entities now use English technical display names.
- Entity IDs are shortened to consistent English object IDs such as `plan72_exec_margin`, `bridge_candidates` and `plan_1_power`.
- Existing unique IDs are intentionally unchanged. Alpha28 migrates registered entity IDs during config-entry setup so the same registry entities are retained.
- Internal planner/store field names and existing plan option/state values are not migrated in this alpha; this avoids mixing a naming cleanup with behavioural state migration.

## Manual plan-slot lifecycle fix
- Cancelled (`geannuleerd`), completed (`voltooid`) and failed (`fout`) plans no longer keep a manual planslot permanently occupied for the automatic bridge preview.
- Empty/no-action slots remain reusable.
- Active or still actionable manual plans remain protected and are never considered available for automatic overwrite.
- With two cancelled slots and one empty slot, `available_manual_slots` should now become 3 and `manual_slot_conflict_count` should become 0.

## Safety unchanged
- Automatic Plan Store writes remain disabled.
- Scheduler handoff remains disabled.
- Automatic execution remains disabled.
- The alpha27 Forward Reserve Precharge and 2% execution buffer remain unchanged.

## Validation
- Confirm Home Assistant still exposes exactly 105 Dummy OS EMS entities.
- Confirm technical entity IDs are English and shortened.
- Confirm the action bridge reports cancelled/completed slots as available.
- Confirm `available_manual_slots: 3`, `manual_slot_conflict: false` and `manual_slot_conflict_count: 0` in the current validation scenario.
- Confirm planner buffer remains safe with zero breach hours before any later Plan Store-write work.

# 0.0.1-alpha.27

## Forward Reserve Precharge
- Correctie van een timingfout in de dynamische veiligheidslading die in alpha26 zichtbaar werd bij een plotselinge stijging van de uitvoeringsreserve.
- De planner behandelt de reserve die na een uur geldt nu als een echte einde-van-uur deadline.
- Een toekomstige reservepiek moet daardoor al aan het einde van het voorafgaande planningsuur haalbaar zijn en wordt niet meer pas in het volgende uur gecorrigeerd.
- Voor elke aantoonbare toekomstige uitvoeringsreservepiek wordt vooraf berekend hoeveel opgeslagen energie beschikbaar zal zijn uit start-SOC en gratis zonne-overschot.
- Alleen het resterende tekort wordt als veiligheidslading uit het net gepland.
- Dat tekort wordt verdeeld over de goedkoopste technisch haalbare uren vóór of op de reserve-deadline.
- De 2 procentpunt uitvoeringsbuffer uit alpha25 blijft ongewijzigd.
- Horizon-fallback zonder aantoonbare volgende bruikbare zonneperiode blijft behouden en creëert geen kunstmatige extra netlading.

## Actiebrug
- De observerende planner-naar-planslot brug uit alpha26 blijft aanwezig.
- De brug blijft blokkeren zolang `execution_buffer_safe=false`.
- Zodra de 72-uursplanner weer een veilige buffer berekent, kan de brug automatisch de netlaad-/netontlaadkandidaten tonen.

## Veiligheid
- `plan_store_write_enabled=false`.
- `scheduler_handoff_enabled=false`.
- `execution_enabled=false`.
- Geen automatische planslot-write en geen fysieke batterijaansturing.

## Te valideren
- `execution_buffer_breach_hours` moet bij een technisch haalbaar plan terug naar 0.
- `min_execution_headroom_soc` mag niet negatief zijn.
- `Dummy OS EMS Automatisch plan uitvoeringsbuffer veilig` moet dan `on` worden.
- De eerder waargenomen reservepiek rond een einde-van-uur overgang mag niet meer één uur te laat worden aangevuld.
- Veiligheidslading mag alleen toenemen met de hoeveelheid die nodig is om de toekomstige reserve op tijd te halen.
- Na een veilige plannerbuffer moet de alpha26 actiebrug weer actiekandidaten kunnen produceren.
- Automatische fysieke uitvoering moet uitgeschakeld blijven.

# 0.0.1-alpha.26

## Observerende planner-naar-planslot brug
- Nieuwe `planner_action_bridge` vertaalt de 72-uurs planneroutput naar concrete uitvoerbare voorstellen.
- Alleen geforceerde acties worden vertaald:
  - veiligheidsladen uit het net;
  - handelsladen uit het net;
  - handelsontladen naar het net.
- Zonneladen en woningontlading blijven onder normale `self_consumption` en worden niet als planslot aangemaakt.
- Opeenvolgende uren met dezelfde actie en hetzelfde doel worden samengevoegd.
- Per voorstel worden onder andere starttijd, eindtijd, vermogen, doel-SOC, looptijd en verwachte energie berekend.
- De eerstvolgende maximaal drie acties vormen een rolling 3-slot preview.
- Extra toekomstige acties blijven zichtbaar als overflow-kandidaten.
- Bestaande handmatige planslots worden als leidend behandeld en nooit automatisch overschreven.

## Nieuwe entiteiten
- Dummy OS EMS Automatische actiebrug status.
- Dummy OS EMS Automatische actiekandidaten.
- Dummy OS EMS Automatische planslot preview.
- Dummy OS EMS Automatisch voorstel plan 1.
- Dummy OS EMS Automatisch voorstel plan 2.
- Dummy OS EMS Automatisch voorstel plan 3.
- Dummy OS EMS Automatische actiebrug geldig.

## Veiligheid
- De 2% uitvoeringsbuffer uit alpha25 blijft volledig actief.
- De brug blokkeert bij een ongeldig 72-uursplan of een onveilige uitvoeringsbuffer.
- Handmatige planslots worden niet overschreven.
- `plan_store_write_enabled=false`.
- `scheduler_handoff_enabled=false`.
- `execution_enabled=false`.
- Geen fysieke batterijaansturing vanuit de automatische planner.

## Te valideren
- De actiebrug moet `ready_preview`, `idle_no_forced_actions` of een duidelijke blokkeerstatus tonen.
- Netveiligheidsladen moet als `laden` / `veiligheidsladen` verschijnen.
- Handelsontladen moet als `ontladen` / `handel_ontladen` verschijnen.
- Zonneladen en woningontlading mogen niet als automatische planslotactie verschijnen.
- De eerste drie toekomstige geforceerde acties moeten in voorstel plan 1 t/m 3 staan.
- Bij meer dan drie acties moet `overflow_count` groter dan 0 worden.
- Bestaande handmatige plannen mogen alleen een conflictstatus opleveren en nooit gewijzigd worden.
- Geen Scheduler- of fysieke uitvoering mag automatisch starten.

# 0.0.1-alpha.25

## Uitvoeringsbuffer voor toekomstige automatische uitvoering
- Standaard 2 procentpunt SOC operationele buffer boven de berekende dynamische reserve.
- De inhoudelijke dynamische reserve blijft ongewijzigd en afzonderlijk zichtbaar.
- Veiligheidsladen wordt nu gepland tegen de gebufferde uitvoeringsreserve.
- Woning- en handelsontlading mogen de gebufferde uitvoeringsreserve niet onderschrijden.
- Per planuur toegevoegd:
  - `execution_reserve_floor_start_soc`
  - `execution_reserve_floor_soc`
  - `execution_buffer_percent`
  - `execution_headroom_soc`
- Nieuwe samenvattende diagnose voor minimale uitvoeringsmarge en bufferonderschrijdingen.
- Nieuwe sensor: Dummy OS EMS Automatisch plan uitvoeringsreserve.
- Nieuwe sensor: Dummy OS EMS Automatisch plan minimale uitvoeringsmarge.
- Nieuwe sensor: Dummy OS EMS Automatisch plan bufferonderschrijding.
- Nieuwe binary sensor: Dummy OS EMS Automatisch plan uitvoeringsbuffer veilig.

## README
- De vaste EMS-besturingsfilosofie is expliciet opgenomen: nul op de meter eerst,
  daarna tekortgestuurd goedkoop netladen, dure netafname vermijden en alleen
  werkelijk vrije energie financieel zinvol verkopen.

## Ongewijzigd
- Planner blijft observerend.
- `execution_enabled=false`.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep vanuit de 72-uurs planner.
- Geen fysieke batterijaansturing vanuit de automatische planner.

## Te valideren
- `execution_buffer_percent` moet 2,0% tonen.
- De uitvoeringsreserve moet normaal 2 procentpunt boven de dynamische reserve liggen,
  behalve wanneer 100% SOC de bovengrens vormt.
- `execution_buffer_breach_hours` hoort bij een uitvoerbaar plan 0 te zijn.
- `Dummy OS EMS Automatisch plan uitvoeringsbuffer veilig` hoort dan aan te staan.
- Veiligheidslading mag iets toenemen wanneer dat nodig is om de extra buffer te bewaken.
- Geen enkele automatische fysieke actie mag door deze alpha worden gestart.

# 0.0.1-alpha.24.4

## Correctie dynamische reserve
- `next_usable_solar: null` wordt niet meer geïnterpreteerd als bewijs dat er
  binnen de toekomst geen bruikbare zon meer komt.
- Bij een onvolledige solarhorizon valt de reserve terug op:
  5% apparaatgrens + softwarematige veiligheidsreserve.
- De resterende woningforecast wordt dan niet meer volledig opgestapeld tot
  een kunstmatige 100% reserve.
- Nieuwe diagnosevelden:
  - `solar_horizon_complete`
  - `solar_horizon_incomplete_hours`
  - per planuur `solar_horizon_complete`

## Goedkoopste noodzakelijke veiligheidsuren
- Dynamische veiligheidslading wordt vooraf gepland.
- Voor elk aantoonbaar reservepiekmoment wordt alleen het werkelijk benodigde
  energietekort bepaald.
- De planner selecteert vervolgens de goedkoopste haalbare uren vóór dat
  tekortmoment.
- Maximaal laadvermogen en laadrendement blijven onderdeel van de selectie.
- Veiligheidslading blijft gescheiden van handelslading.

## Nieuwe entiteiten
- Dummy OS EMS Automatisch plan solarhorizon
- Dummy OS EMS Automatisch plan solarhorizon ontbrekende uren

## Ongewijzigd
- Solar Charge Delay blijft actief.
- Handelsreserve-logica blijft actief.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep.
- Geen fysieke batterijaansturing.

## Te valideren
- Reserve mag bij ontbrekende toekomstige solar niet meer naar 100% springen.
- `solarhorizon` moet `onvolledig` aangeven wanneer de resterende forecast geen
  volgende bruikbare zonneperiode bevat.
- Veiligheidslading moet naar goedkopere beschikbare uren verschuiven wanneer
  het tekort pas later optreedt.
- Alleen de benodigde hoeveelheid veiligheidsenergie mag worden gepland.
- SOC en dynamische reserve moeten gedurende de volledige horizon consistent
  blijven.

# 0.0.1-alpha.24.3

## Dynamische 72-uurs reserve
- Reservevloer wordt nu voor ieder forecastuur opnieuw berekend.
- Dezelfde bruikbare-zonregel als alpha21 wordt gebruikt:
  eerste van twee opeenvolgende uren waarin solar >= woningverbruik.
- Woningbehoefte tot de volgende bruikbare zonneperiode wordt per uur bepaald.
- Ontlaadrendement wordt meegenomen bij de benodigde opgeslagen energie.
- 5% apparaatgrens en softwarematige veiligheidsreserve blijven onderdeel van
  de reservevloer.
- Woningontlading en handelsontlading mogen de dynamische reserve niet
  onderschrijden.
- Observerende veiligheidslading kan worden toegevoegd wanneer de opgeslagen
  energie na zonnelading onder de actuele dynamische reservebehoefte ligt.
- Nieuwe planvelden:
  - `reserve_floor_start_soc`
  - `reserve_floor_soc`
  - `dynamic_need_until_solar_kwh`
  - `dynamic_need_after_hour_kwh`
  - `next_usable_solar`
- Nieuwe sensoren:
  - Dummy OS EMS Automatisch plan dynamische reserve
  - Dummy OS EMS Automatisch plan maximale reserve

## Ongewijzigd
- Solar Charge Delay uit alpha24.1 blijft actief.
- Handelsreserve-logica blijft actief.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep.
- Geen fysieke batterijaansturing.

## Te valideren
- Reservevloer moet door de 72 uur heen zichtbaar veranderen.
- Reserve moet in de avond/nacht oplopen wanneer meer energie nodig is tot
  de volgende bruikbare zon.
- Reserve moet terugvallen wanneer bruikbare solar beschikbaar wordt.
- SOC mag na woning- of handelsontlading niet onder de dynamische reserve komen.
- Eventuele veiligheidslading moet alleen ontstaan wanneer de actuele
  batterijvoorraad werkelijk onvoldoende is voor behoefte plus reserve.

# 0.0.1-alpha.24.2

## Hotfix
- Runtime `NameError` in `planner_72h.py` opgelost.
- Verwijderde variabele `trade_charge_stored` werd nog gebruikt in de
  samenvattende uitvoer van de 72-uurs planner.
- `auto_plan_72h_trade_charge_stored_kwh` wordt nu berekend als:
  geplande handelsnetlading × laadrendement.
- Hierdoor kan de coordinator weer normaal vernieuwen en worden de
  Dummy OS EMS-entiteiten opnieuw beschikbaar.

## Functioneel
- De Solar Charge Delay- en handelsreservecorrecties uit alpha24.1 blijven
  ongewijzigd.
- Geen wijziging aan fysieke besturing of Scheduler.

# 0.0.1-alpha.24.1

## Correctie op alpha24
- Solar Charge Delay nu daadwerkelijk toegepast op handelsladen.
- Geen handelslading uit het net wanneer verwacht solaroverschot vóór het
  geselecteerde handelsontlaaduur de benodigde batterijruimte kan vullen.
- Handelsladen wordt beperkt tot de vrije capaciteit die naar verwachting niet
  door gratis zonne-energie wordt gevuld.
- Handelsenergie wordt als tijdelijke reserve bijgehouden.
- Woningontlading mag deze handelsreserve niet meer automatisch in
  financieel minder interessante uren opmaken.
- De handelsreserve mag wel voor de woning worden gebruikt wanneer het actuele
  tarief minimaal gelijkwaardig is aan de effectieve laadkost plus de ingestelde
  minimum handelsmarge.
- Op het gekozen handelsontlaaduur heeft woningverbruik eerst prioriteit; alleen
  resterend ontlaadvermogen/energie wordt naar het net gestuurd.
- Per planuur nieuw attribuut `trade_reserved_kwh` voor diagnose.

## Veiligheid
- Nog steeds uitsluitend observerend.
- Geen automatische planslot-creatie.
- Geen Scheduler-aanroep.
- Geen fysieke batterijaansturing.

## Te valideren
- Het eerder waargenomen handelsladen vlak vóór een grote zonnepiek moet
  verdwijnen of sterk afnemen.
- Solar Charge Delay moet voorkomen dat netgeladen energie kort daarna vrije
  zonnelading verdringt.
- Handelsenergie mag niet in goedkope tussenuren voor woningverbruik verdwijnen.
- SOC-keten moet 72 uur aaneengesloten blijven.
- Reservevloer moet intact blijven.

# 0.0.1-alpha.24

## Toegevoegd
- Eerste volledige, doorlopende automatische 72-uurs planpreview.
- Sequentiële SOC-berekening per forecastuur.
- Batterijcapaciteit 7,2 kWh en 5% absolute ondergrens.
- Softwarematige veiligheidsreserve wordt gedurende de planning bewaakt.
- Solar dekt eerst woningverbruik; overschot kan de batterij laden.
- Veiligheidslading uit alpha21/22 wordt in de 72-uurs preview geplaatst.
- Financieel beste handelslaaduur uit alpha23 kan observerend worden ingepland.
- Financieel beste handelsontlaaduur uit alpha23 kan observerend worden ingepland.
- Woningtekort kan uit de batterij worden gedekt zolang de reserve intact blijft.
- Laadlimiet 3,5 kW en ontlaadlimiet 3,0 kW.
- Laad- en ontlaadverliezen worden in het SOC-pad verwerkt.
- Volledige uurreeks wordt gepubliceerd in het `plan`-attribuut.

## Nieuwe entiteiten
- Dummy OS EMS Automatisch plan 72u status
- Dummy OS EMS Automatisch plan 72u
- Dummy OS EMS Automatisch plan eind-SOC
- Dummy OS EMS Automatisch plan minimum-SOC
- Dummy OS EMS Automatisch plan zonnelading
- Dummy OS EMS Automatisch plan veiligheidslading
- Dummy OS EMS Automatisch plan handelslading
- Dummy OS EMS Automatisch plan ontladen woning
- Dummy OS EMS Automatisch plan ontladen net
- Dummy OS EMS Automatisch plan 72u geldig

## Veiligheid
- Geen automatische plancreatie in de drie planslots.
- Geen Scheduler-aanroep vanuit de 72-uurs planner.
- Geen fysieke batterijaansturing vanuit de 72-uurs planner.
- Bestaande handmatige besturingsketen blijft ongewijzigd.

## Te valideren
- Plan bevat maximaal 72 chronologische uren.
- SOC blijft tussen 5% en 100%.
- Reservevloer wordt niet door normale woning-/handelsontlading onderschreden.
- Zonnelading, veiligheidslading en handelslading worden apart zichtbaar.
- Laad- en ontlaadlimieten worden per uur gerespecteerd.
- Eind-SOC komt overeen met het laatste planuur.
- Plan-attribuut blijft stabiel beschikbaar in Home Assistant.

# 0.0.1-alpha.23

## Toegevoegd / gewijzigd
- Observerende financiële handelslogica bovenop de alpha22 Planner Decision Preview.
- Configureerbaar laadrendement, standaard 92%.
- Configureerbaar ontlaadrendement, standaard 92%.
- Configureerbare minimale netto handelsmarge, standaard € 0,10/kWh.
- Roundtrip-rendement wordt expliciet berekend.
- Effectieve laadkost wordt gecorrigeerd voor laad- én ontlaadverliezen.
- Alle toekomstige prijsuren worden als laad/ontlaad-combinatie vergeleken.
- Beste handelslaaduur en beste handelsontlaaduur worden gepubliceerd.
- Verwachte netto handelsmarge wordt gepubliceerd.
- Nieuwe binary sensor `Dummy OS EMS Handel rendabel`.
- Plannerbeslissing kan observerend `handelsladen` of `ontladen` aangeven wanneer het huidige uur financieel het beste uur is en de veiligheidsvoorwaarden dit toelaten.
- Veiligheidslading blijft altijd leidend boven handel.

## Nieuwe entiteiten
- Dummy OS EMS Planner roundtrip rendement
- Dummy OS EMS Effectieve laadkost
- Dummy OS EMS Verwachte handelsmarge
- Dummy OS EMS Minimale handelsmarge
- Dummy OS EMS Beste handelslaaduur
- Dummy OS EMS Beste handelslaadprijs
- Dummy OS EMS Beste handelsontlaaduur
- Dummy OS EMS Beste handelsontlaadprijs
- Dummy OS EMS Handel rendabel

## Veiligheid
- Nog geen automatische plancreatie.
- Nog geen nieuwe fysieke handelsuitvoering.
- Bestaande Scheduler, Safety Guard, Action Controller en Execution Controller blijven ongewijzigd.

## Te valideren
- Roundtrip-rendement bij 92% / 92% moet 84,6% zijn.
- Effectieve laadkost en verwachte handelsmarge controleren tegen actuele prijsuren.
- Beste laad- en ontlaaduren controleren op chronologische volgorde.
- `Handel rendabel` moet alleen Aan zijn wanneer netto marge minimaal € 0,10/kWh bedraagt.
- Veiligheidslading moet handelslogica blijven overrulen.

# 0.0.1-alpha.22

## Toegevoegd / gewijzigd
- Nieuwe observerende `Planner Decision Preview` bovenop de alpha21-energiebalans.
- Plannerbeslissing en leesbare plannerreden.
- Vereiste minimum-SOC uit behoefte, 5% absolute ondergrens en softwarematige reserve.
- Energie boven reserve zichtbaar gemaakt voor latere handelslogica.
- Veiligheidslading als afzonderlijke plannerbeslissing.
- Goedkoopste benodigde kandidaat-laaduren tot bruikbare zon.
- Controle of voldoende laaduren beschikbaar zijn om het berekende tekort te dekken.
- `Solar Charge Delay` als observerende status wanneer netladen kan worden uitgesteld tot bruikbare zon.
- Observerende status voor mogelijke ontlading boven reserve.
- Observerende handelslading-kandidaat op basis van vrije capaciteit en forecast-prijsverschil.
- Planner prijsverschil en herplanreden als diagnosewaarden.

## Belangrijke begrenzing
- Alpha22 maakt nog geen automatische plannen aan.
- Alpha22 voert geen nieuwe fysieke acties uit.
- Handelslading is alleen een kandidaatstatus.
- Laadverlies, ontlaadverlies en minimale netto handelsmarge zijn nog niet gemodelleerd.
- Kandidaat-laaduren gebruiken maximaal 3500 W alleen voor een observatieve ureninschatting; dit is geen uitvoeringscommando.

## Nieuwe entiteiten
- Dummy OS EMS Planner preview status
- Dummy OS EMS Planner beslissing
- Dummy OS EMS Planner reden
- Dummy OS EMS Vereiste minimum-SOC
- Dummy OS EMS Energie boven reserve
- Dummy OS EMS Veiligheidslading nodig
- Dummy OS EMS Goedkoopste benodigde laaduren
- Dummy OS EMS Planner prijsverschil
- Dummy OS EMS Herplan reden
- Dummy OS EMS Planner veiligheidslading nodig
- Dummy OS EMS Planner handelslading kandidaat
- Dummy OS EMS Planner ontladen mogelijk
- Dummy OS EMS Solar Charge Delay

## Te valideren
- Plannerbeslissing gedurende zonnige uren.
- Omschakeling naar veiligheidsladen wanneer de behoefte tot bruikbare zon groter wordt dan beschikbare batterij-energie minus reserve.
- Selectie van de goedkoopste benodigde laaduren.
- Solar Charge Delay in de periode voor verwachte bruikbare zon.
- Gedrag van handels- en ontlaadkandidaten zonder dat deze fysieke acties veroorzaken.

# 0.0.1-alpha.21

## Toegevoegd
- Eerste **observatieve energiebalans** als rekenlaag voor de toekomstige automatische planner.
- Nieuwe berekening van netto energiebehoefte vanaf nu tot de eerstvolgende bruikbare zonneproductie.
- Bruikbare zon wordt in deze eerste versie gedefinieerd als het eerste van twee opeenvolgende forecasturen waarin `solar_kwh >= home_consumption_kwh`.
- Het resterende deel van het actuele uur wordt proportioneel meegenomen.
- Beschikbare batterij-energie wordt berekend boven de absolute 5% SOC-ondergrens op basis van 7,2 kWh batterijcapaciteit.
- Softwarematige veiligheidsreserve toegevoegd als configureerbare integratie-optie van 0-30%; standaard 7%.
- Berekening van benodigde aanvullende netlading.
- Berekening van vrije/verhandelbare batterij-energie boven behoefte plus reserve.
- Diagnose-/redenstatus voor de energiebalans.

## Nieuwe sensoren
- `Dummy OS EMS Energiebehoefte status`
- `Dummy OS EMS Energiebehoefte tot bruikbare zon`
- `Dummy OS EMS Beschikbare batterij-energie`
- `Dummy OS EMS Veiligheidsreserve`
- `Dummy OS EMS Benodigde aanvullende netlading`
- `Dummy OS EMS Vrije verhandelbare batterij-energie`
- `Dummy OS EMS Eerste bruikbare solar`
- `Dummy OS EMS Energiebehoefte reden`

## Veiligheid / scope
- De nieuwe energiebalans is **uitsluitend observerend**.
- Alpha21 maakt op basis hiervan nog geen automatische plannen aan.
- De bestaande Scheduler, Safety Guard, Action Controller en Execution Controller zijn niet gewijzigd door deze rekenlaag.
- De vaste hardwaregrens van 5% SOC blijft leidend.

## Te valideren
- Controleer of het eerste bruikbare solar-uur logisch overeenkomt met Solcast en de woningforecast.
- Controleer of de energiebehoefte afneemt naarmate de tijd richting bruikbare zon vordert.
- Controleer of beschikbare batterij-energie overeenkomt met SOC en 7,2 kWh capaciteit.
- Beoordeel gedurende meerdere situaties of benodigde netlading en vrije/verhandelbare energie logisch reageren.

# 0.0.1-alpha.20

## Toegevoegd / gewijzigd
- Gecontroleerde retry-logica voor geplande laad- en ontlaadacties.
- `max_start_delay` wordt nu daadwerkelijk gebruikt als startvenster voor tijdelijke startproblemen.
- Bij tijdelijke Anker-/besturingsvertraging wordt een gepland plan niet direct definitief afgebroken.
- Retry-interval: 10 seconden, nooit langer dan de resterende startmarge.
- Tussen mislukte pogingen wordt de bestaande safe-stop gebruikt en het plan alleen binnen het geldige startvenster opnieuw op `pending` gezet.
- Ondersteunde tijdelijke retry-redenen omvatten onder andere:
  - externe modus nog niet tijdig beschikbaar;
  - `control_sources_missing`;
  - `not_in_external_mode`;
  - `observation_sources_missing`;
  - tijdelijk tegengestelde laad-/ontlaadflow;
  - tijdelijk niet-gereed Action Controller.
- Buiten het startvenster of bij een niet-tijdelijke fout wordt niet opnieuw geprobeerd.

## Ongewijzigd
- Maximale startvertraging blijft per plan instelbaar op 1-120 minuten.
- Minimale looptijd blijft 15 minuten.
- Laden en ontladen gebruiken dezelfde Scheduler → Safety Guard → Action Controller → Execution Controller-keten.
- Safe-stop blijft 0 W zetten en terugkeren naar `self_consumption`.

## Te valideren
- Een gepland plan waarbij de Anker-besturingsentiteiten bij de eerste startpoging nog niet beschikbaar zijn, maar binnen `max_start_delay` alsnog gereed komen.
- Een gepland plan waarbij een tegengestelde batterijflow tijdelijk actief is en later binnen het startvenster verdwijnt.
- Geen automatische start meer nadat `max_start_delay` is verstreken.

# 0.0.1-alpha.19

## Toegevoegd / gewijzigd
- Normale fysieke ontlaaduitvoering vrijgegeven via de bestaande Execution Controller.
- Directe ontlaadplannen kunnen via `anker_ems.start_plan_now` worden uitgevoerd.
- Geplande ontlaadplannen worden bij `startklaar` automatisch overgedragen van Scheduler naar Execution Controller.
- Ontladen gebruikt dezelfde veilige modusovergang als laden: `self_consumption` → `third_party_control` → besturing beschikbaar → Safety Guard → fysieke uitvoering.
- Runtime-monitoring controleert nu per actie de juiste richting en tegengestelde energiestroom.
- Ontladen stopt normaal bij doel-SOC, minimale hardware-SOC van 5% of maximale looptijd.
- Safe-stop blijft 0 W zetten en terugkeren naar `self_consumption`.
- Reëel maximaal ontlaadvermogen wordt in de Safety Guard/Execution Controller begrensd op 3000 W.
- Minimale maximale looptijd verlaagd van 30 minuten naar **15 minuten (0,25 uur)**.
- Stapgrootte voor maximale looptijd verlaagd naar 15 minuten.

## Validatiestatus
- Gepland laden: fysiek end-to-end bevestigd in alpha17.
- Gecontroleerde fysieke ontlaadtest: bevestigd in alpha18.
- Normale geplande ontlaaduitvoering: te valideren in alpha19.

# 0.0.1-alpha.18

## Toegevoegd
- Expliciete service `anker_ems.start_discharge_test` voor een gecontroleerde fysieke ontlaadtest.
- Ontlaadtest is begrensd op 100-500 W en 10-120 seconden.
- Test vereist expliciete `confirm: true`, een startklaar ontlaadplan, simulatiemodus en vooraf geactiveerde `third_party_control`.
- Safety Guard moet de gekozen ontlaadactie vrijgeven voordat de fysieke test kan starten.
- De test bewaakt richting, tegengesteld laadvermogen, SOC, doel-SOC, testduur en besturingsbeschikbaarheid.
- Bij 5% SOC of het ingestelde ontlaaddoel stopt de test automatisch.
- Safe-stop zet het setpoint terug naar 0 W en keert terug naar `self_consumption`.
- Fysieke testdiagnostiek bevat nu ook de actieve testactie.

## Bewust nog niet gewijzigd
- De normale Execution Controller voert ontlaadplannen nog niet automatisch uit.
- Geplande ontlaadacties worden nog niet automatisch gestart.
- Pas na een geslaagde gecontroleerde ontlaadtest wordt automatische ontlaaduitvoering vrijgegeven.

# Changelog

## 0.0.1-alpha.17

- Fixed scheduled manual charge plans stopping at `startklaar` while `self_consumption` was active.
- A user-scheduled charge plan now automatically hands off from the Scheduler to the existing Execution Controller when its start window opens.
- The Execution Controller performs the proven automatic mode transition to `third_party_control`, waits for the Anker control entities, rechecks Safety Guard/Action Controller, and then starts charging.
- `Nu starten` remains an explicit direct action and is unchanged.
- Scheduled physical discharge remains intentionally disabled until the separate controlled discharge path has been validated.
- Prevents duplicate auto-start tasks while coordinator refreshes occur during the mode transition.

## 0.0.1-alpha.16

- Hotfix for alpha15 service registration.
- Fixes Home Assistant startup error: `ServiceRegistry.async_register() got multiple values for argument 'schema'`.
- No intended functional changes to the alpha15 manual plan controls.


## 0.0.1-alpha.15

- Added explicit manual plan controls: schedule, start now, cancel, and stop all.
- Plan edits now become `concept` first and are not scheduler-eligible until the user explicitly schedules or starts them.
- Existing plan lifecycle, safe execution, Source Monitor, and simulation-first architecture remain intact.


## 0.0.1-alpha.15

- Added persistent plan lifecycle states for the three manual plan slots.
- A physically started plan now becomes `actief` and is no longer selectable by the Scheduler.
- A normally finished plan becomes `voltooid`.
- A manually stopped plan becomes `geannuleerd`.
- An emergency/error stop becomes `fout`.
- Completed/cancelled/error plans remain terminal across Home Assistant restarts.
- Editing any plan field resets its lifecycle to `pending`, making that edited plan eligible for scheduling again.
- Prevents an already executed direct plan from remaining `startklaar` and being selected again.

## 0.0.1-alpha.13

- Added persistent Source Monitor for Solcast, Stroomvoorspeller, EnergyZero price data and price forecast updates.
- Tracks Home Assistant report moments separately from actual content changes.
- Keeps seven days of recent monitor events for later planner-trigger analysis.
- Adds one diagnostic entity: `Dummy OS EMS Bronmonitor`.
- Does not trigger replanning yet; this version only measures when source data really changes.


## 0.0.1-alpha.12

- Added explicit plan execution state machine via `anker_ems.execute_selected_plan`.
- Added automatic transition from `self_consumption` to `third_party_control`.
- Waits for Anker control entities to become available before setting direction and power.
- Re-validates Safety Guard and Action Controller after entering external mode.
- Monitors target SOC, maximum runtime, mode, direction and unexpected discharge during execution.
- Added guaranteed safe-stop back to 0 W and `self_consumption`.
- Added persistent restart recovery for an interrupted execution.
- Added execution status, remaining-time and active entities.
- Physical discharge remains blocked pending a separate controlled discharge test.
- Automatic 72-hour planner execution remains disabled; starting an existing selected plan still requires explicit confirmation.

## 0.0.1-alpha.11

- Fixed the physical test auto-stop path after the first 300 W / 120 s live test showed the countdown could reach 0 while the test remained running.
- Replaced the primary delayed stop callback with a dedicated fail-safe task tied to the absolute stop time.
- Added idempotent stop locking to prevent concurrent watchdog/manual stop races.
- The UI now enters `stopping` before the zero-setpoint and return to `self_consumption` are executed.
- Manual stop and restart recovery remain available as independent safety paths.


## 0.0.1-alpha.10

- Added non-actuating Action Controller.
- Added Safety Guard for selected scheduler plans.
- Added safety checks for source availability, SOC, target SOC, power and conflicting battery flow.
- Added semantic desired command attributes for later device-specific execution.
- Added Safety Guard and Action Controller status/binary sensors.
- Physical Anker writes remain disabled; alpha 8 is still safe simulation/observe preparation.

## 0.0.1-alpha.7

- Added simulation-only Scheduler on top of the persistent Plan Store.
- Scheduler evaluates all three plan slots every coordinator refresh.
- Scheduled plans become `startklaar` only inside their configured start window.
- Plans that miss `start_time + max_start_delay` become `verlopen`.
- Direct plans become immediately eligible for simulated scheduling.
- Deterministic conflict handling selects only one slot; other ready slots become `geblokkeerd`.
- Added `Dummy OS EMS Scheduler status`.
- Added `Dummy OS EMS Scheduler geselecteerd plan`.
- Added `Dummy OS EMS Scheduler startklaar`.
- Plan status sensors now expose Scheduler runtime state.
- Persistent plans are re-evaluated after Home Assistant restart.
- No Home Assistant service calls and no physical Anker writes are performed.

## 0.0.1-alpha.6

- Added persistent Plan Store with three independent plan slots.
- Added per-slot action and execution-mode select entities.
- Added per-slot start datetime.
- Added per-slot power, target SOC, maximum runtime and maximum start-delay number entities.
- Added per-slot validation/status sensor.
- Plan values survive Home Assistant restarts.
- No scheduler execution and no physical Anker control yet.


## 0.0.1-alpha.5

### Forecast Sources
- Eerste Python-gebaseerde forecastlaag toegevoegd.
- Bestaande prijs-, woningverbruiks- en Solcast-bronnen worden ingelezen.
- 72 uur wordt intern genormaliseerd naar één uurmodel met `time`, `price`, `price_min`, `price_max`, `price_source`, `solar_kwh` en `home_consumption_kwh`.
- Bekende prijzen krijgen voorrang op prijsprognoses voor hetzelfde uur.
- Nieuwe sensor `Dummy OS EMS Forecast status` publiceert diagnose-attributen en de genormaliseerde forecast.
- Nieuwe sensor `Dummy OS EMS Forecast complete uren` toont hoeveel uren alle drie de hoofdbronnen bevatten.
- Nieuwe binary sensor `Dummy OS EMS Forecast bronnen beschikbaar`.
- Forecastbronnen zijn via de integratie-opties selecteerbaar; bestaande config-entry blijft behouden.
- Veilige update-listener toegevoegd zodat gewijzigde opties de integratie herladen.
- Geen plannerbeslissingen en geen fysieke write-calls toegevoegd.

## 0.0.1-alpha.4

### GitHub/HACS basis
- Repositorystructuur voorbereid voor `dummy-os-anker-ems`.
- HACS-manifest toegevoegd.
- Home Assistant minimumversie vastgelegd op 2026.7.0.
- GitHub Actions toegevoegd voor HACS-validatie en hassfest.
- Issue templates toegevoegd.
- Onafhankelijkheids- en aansprakelijkheidsstatement toegevoegd.
- Alpha 3 runtime als functionele basis behouden.
- Nog geen fysieke write-calls naar de Anker.

## 0.0.1-alpha.3
- `Bronnen beschikbaar` controleert alleen observatiebronnen.
- `Besturing beschikbaar` toegevoegd.
- Extra read-only diagnostische sensoren toegevoegd.
- Simulatiemodus blijft standaard actief.

## 0.0.1-alpha.1
- Eerste config flow.
- Eerste coordinator.
- Eerste read-only sensoren.

## 0.0.1-alpha.40.8 - Minimal Options Flow Recovery

- Rebuilt the Options Flow from the last known working alpha36.3 pattern.
- Removed all non-essential planner/forecast/monitor fields from the Options Flow for this validation release.
- Options now expose only electrical profile, charge/discharge limits, market-price architecture, market-price source, import/export markup and tariff resolution.
- Preserves existing hidden options when saving the minimal form.
- Reconfigure remains limited to setup-critical Anker entities.
- Existing planner, Recorder optimizations and Control Path Readiness behavior are unchanged.
