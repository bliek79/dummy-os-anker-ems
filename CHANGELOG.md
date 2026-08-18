# Changelog

## 0.0.1-alpha.9

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
