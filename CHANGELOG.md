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
