# Dummy OS EMS

**Dummy OS EMS** is an experimental Home Assistant Energy Management System for the **Anker SOLIX Solarbank Max AC**.

> **Status:** experimental alpha  
> **Domain:** `anker_ems`  
> **Minimum Home Assistant:** 2026.7.0

The integration combines battery status, electricity prices, solar forecast, home-consumption forecast, safety limits and user choices into one local EMS layer. Planning, persistent plan storage, scheduling, safety validation and physical execution are intentionally separated so every transition can be validated independently.

## Control philosophy

Dummy OS EMS follows this order of priority:

1. Solar production serves the home first.
2. Remaining solar can charge the battery.
3. If own production is insufficient, only the necessary deficit may be charged from the grid at suitable cheap moments.
4. Stored energy is used later to avoid expensive grid import.
5. Only battery energy above home need, dynamic reserve and expected near-term need may be considered for trading.
6. Genuine excess may be exported when this is financially worthwhile.
7. Charging/discharging losses, the hardware minimum SOC, configured reserve and minimum profitability thresholds are respected.

The objective is maximum self-consumption and as close to zero on the meter as practical. Trading is secondary to household energy needs and safety.

## Functional architecture

The main control chain is:

`Config Flow -> Coordinator -> Forecast/Source Monitor -> Plan72 -> Automatic Plan Bridge -> Persistent Plan Store -> Scheduler -> Pre-Start/Safety Guard -> Final Revalidation -> Execution Controller -> Anker control entities`

Supporting modules provide source monitoring, energy-need calculation, planner previews, manual execution and diagnostic entities.

## Planning

The integration maintains a rolling 72-hour plan using:

- electricity-price data;
- home-consumption forecast;
- solar forecast;
- current battery SOC;
- dynamic reserve requirements;
- charge/discharge efficiency;
- configured charge/discharge power limits.

Plan72 distinguishes expected passive battery flows from explicit EMS actions. Solar surplus charging and normal discharge to the home can remain part of the battery's own `self_consumption` behaviour, while explicit grid safety charging or trading actions can be bridged into persistent plan slots.

The planner includes a configurable execution reserve buffer. A plan that cannot prove the required reserve remains blocked from unattended physical execution.

## Price architecture

Stroomvoorspeller can be used as the primary market-price source. Dummy OS EMS applies separate import and export markups so grid import and grid export can be valued independently.

Known day-ahead hourly prices take precedence over forecast prices. For the longer horizon the integration uses the most detailed timed Stroomvoorspeller forecast available. If Stroomvoorspeller only exposes a daily market estimate, Dummy OS EMS may use the configured hourly forecast source only to restore the intra-day price shape while keeping the Stroomvoorspeller daily market level authoritative. A daily flat estimate is retained only as a final fallback when no hourly shape is available.

The price layer is designed to support hourly and quarter-hour source data. The planner currently operates on hourly blocks; quarter-hour source values are safely aggregated until the dedicated quarter-hour planner is implemented.

## Persistent plan slots

Exactly three persistent plan slots are maintained.

- Manual plans always have priority over automatic planner writes.
- Automatic planner-owned plans can be reconciled while safely in the future.
- Planner-owned plans that have passed their complete Scheduler start window are released for reuse.
- Completed, cancelled, failed and empty slots are reusable.
- Active plans are never silently overwritten.

A user edit immediately claims a slot as manual so a rolling planner refresh cannot overwrite it.

## Scheduler and safety

The Scheduler evaluates start times, start windows and plan lifecycle state. Before any automatic action can progress, the safety chain rechecks current conditions including forecast readiness, planner validity, execution reserve, action direction, power limits, target SOC and manual overrides.

Anker control-path readiness is split into two stages:

- **pre-mode readiness:** the operating-mode path must be available and stable;
- **post-mode readiness:** direction and power-setpoint controls become mandatory only when `third_party_control` is active.

This avoids a circular dependency on controls that may be unavailable while the battery remains in `self_consumption`.

## Automatic execution status

Automatic planning, bridging, scheduling and shadow validation are under active development. The current alpha architecture keeps unattended non-zero physical automatic charge/discharge execution disabled until every safety and recovery path has been validated on live hardware.

Manual battery control remains separate from the automatic shadow path.

## Battery assumptions and limits

Current project defaults/assumptions include:

- battery capacity: **7.2 kWh**;
- hardware minimum SOC: **5%**;
- charge efficiency: **92%**;
- discharge efficiency: **92%**;
- round-trip efficiency: **84.64%**;
- execution reserve buffer: **2 percentage points**;
- persistent plan slots: **3**.

Charge and discharge limits are configured centrally. A dedicated electrical group can use higher configured limits than a shared group; the shared-group profile is intentionally conservative.

## Source integration

Dummy OS EMS does not replace the Anker Solix Home Assistant integration. It uses the existing Anker integration as the communication layer and adds planning, safety and orchestration above it.

Typical mapped inputs include:

- battery SOC and status;
- charge/discharge power;
- grid import/export power;
- Anker operating mode;
- charge/discharge direction;
- external power setpoint;
- market price source;
- home-consumption forecast;
- solar forecast.

Local entity IDs are selected through Config Flow / Options Flow rather than being hardcoded into the integration architecture.

## Home Assistant entities

Visible integration entities use the `Dummy OS EMS` prefix. Technical entity IDs and internal attributes use concise English naming. Dashboard labels can remain localized independently from the integration internals.

Large live Plan72 and forecast payloads are intentionally excluded from Recorder history where appropriate while remaining available live for dashboards and diagnostics.

## Installation

For local development/testing:

1. Copy `custom_components/anker_ems/` to `/config/custom_components/anker_ems/`.
2. Restart Home Assistant.
3. Add **Dummy OS EMS** through **Settings -> Devices & services**.
4. Map the required source and control entities.
5. Validate source and control availability before using manual physical control.

The repository is structured for HACS-compatible distribution during development.

## Safety rules

- Never run two physical battery controllers at the same time.
- Manual/user-modified plans override automatic planner plans.
- The hardware minimum SOC is never intentionally planned below.
- Invalid or unavailable critical sources block automatic progress.
- Planner write, Scheduler handoff, safety approval and physical execution are separate gates.
- Forecast data is never treated as proof that an action is safe at execution time.
- Live conditions are revalidated immediately before any future physical execution.
- Any physical-control failure must fail safe and return control to a known safe state.

## Roadmap

Main functional work still includes:

- recovery planning for unavoidable current-hour reserve shortfalls;
- live validation of post-mode Anker control readiness;
- controlled automatic physical charge/discharge tests after safety approval;
- true quarter-hour planning;
- Afwezigheidsmodus;
- plan-versus-actual evaluation;
- daily plan notification;
- multi-cycle optimization;
- further migration away from legacy YAML helpers;
- continued analysis of Anker connection stability and requested-versus-actual power.

## Development history

Release-specific changes are intentionally **not maintained in this README**.

Use:

- `CHANGELOG.md` for version-by-version changes;
- GitHub Releases for release notes and downloadable builds;
- the project handover documentation for detailed technical history and design decisions.
