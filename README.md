# Dummy OS EMS

**Dummy OS EMS** is a Home Assistant Energy Management System for the **Anker SOLIX Solarbank Max AC**.

> **Status:** experimental alpha  
> **Domain:** `anker_ems`  
> **Minimum Home Assistant:** 2026.7.0  
> **Current version:** `0.0.1-alpha.40.4`

The integration combines battery status, electricity prices, solar forecast, home-consumption forecast, safety limits and user choices into one local EMS layer. The architecture is deliberately split into planning, persistent plan storage, scheduling, safety validation and physical execution.

## Control philosophy

Dummy OS EMS follows this order of priority:

1. Solar production serves the home first.
2. Remaining solar can charge the battery.
3. If own production is insufficient, only the necessary deficit may be charged from the grid at suitable cheap moments.
4. Stored energy is used later to avoid expensive grid import.
5. Only battery energy above home need, dynamic reserve and expected near-term need may be used for trading.
6. Genuine excess may be exported when this is financially worthwhile.
7. Charging/discharging losses, Solar Charge Delay, the 5% hardware minimum SOC and a minimum profitability threshold are respected.

The objective is **maximum self-consumption / as close to zero on the meter as practical**, not trading for its own sake.

## Current functionality

The current alpha supports:

- Config Flow based source/control mapping without hardcoded local Anker entity IDs;
- normalized battery, grid, price, solar and home-consumption data;
- three persistent manual plan slots;
- manual direct and scheduled charge/discharge control;
- Scheduler, Safety Guard and Execution Controller;
- safe stop and return to `self_consumption`;
- 72-hour automatic planning;
- dynamic reserve and 5% hardware SOC floor;
- 2 percentage-point execution reserve buffer;
- deficit-driven grid charging and cheapest required charging hours;
- separate safety charging and trading charging;
- Solar Charge Delay;
- financial trade-margin logic with charge/discharge efficiency;
- Forward Reserve Precharge;
- Action Bridge from planner actions to plan slots;
- controlled automatic Plan Store writes;
- controlled Scheduler handoff;
- rolling pending-plan reconciliation using stable `planner_identity`;
- stale automatic-plan cleanup;
- pre-start safety validation;
- time-aware pre-start diagnostics and dry-run blocker tests;
- non-actuating Scheduler -> Safety Guard handoff for automatic start-ready plans;
- non-actuating Safety Guard -> Execution Controller handoff preview with final execution prerequisites;
- final live revalidation and explicit mode-switch transaction preview;
- controlled physical mode-switch validation for a fully approved automatic plan: 0 W guard -> `third_party_control` -> post-mode revalidation -> immediate safe return to `self_consumption`;
- centralized configurable charge/discharge power limits based on the electrical connection profile;
- optimized Plan72 refresh policy: hourly between 05:00 and 22:00 plus event-driven/start-critical refreshes; no periodic overnight refreshes;
- Recorder-safe live payload handling: the large Plan72 `plan` and Forecast Status `forecast` attributes are excluded from history while remaining available live to the dashboard/diagnostics.

**Automatic charge/discharge execution is still disabled.** Alpha40.4 retains the alpha40 physical scope and may only validate the operating-mode transition for a fully approved automatic plan. It never selects charge/discharge direction and never applies a non-zero automatic power setpoint.

## Pre-start safety model

The pre-start layer has two intentionally separate modes.

### Early diagnostic

The nearest future automatic pending plan is continuously inspected. This diagnostic is **informational and non-authoritative**.

Hard structural checks such as planner validity, forecast readiness, execution-buffer safety, Action Bridge validity, action validity, power limits and planner identity remain meaningful at all times.

Current SOC can change substantially before a future plan starts. Therefore, outside the live decision window, SOC direction and execution-reserve checks are exposed as **warnings**, not final blockers.

The current live-decision window is at least 15 minutes before the planned start, or wider when the plan start-delay setting requires it.

### Real pre-start gate

When the Scheduler actually selects an automatic plan as ready to start, the authoritative pre-start gate rechecks current conditions. At that point SOC direction and execution reserve are hard safety conditions.

The gate verifies at least:

- valid current 72-hour plan;
- ready forecast sources;
- safe execution buffer;
- valid Action Bridge candidates;
- stable planner identity;
- valid action and power;
- valid current SOC and target SOC;
- correct SOC direction for the requested charge/discharge action;
- sufficient reserve for discharge.

A changed planner revision can be reported as a warning while stable `planner_identity` remains the continuity key.

## Planner identity and revisions

Automatic pending plans use two separate values:

- `planner_identity`: stable identity of the planned action, based on action/purpose/start/end;
- `planner_signature`: current calculated revision, including changing values such as target SOC and expected energy.

This allows rolling forecasts to revise a future automatic plan without creating duplicate slots or falsely treating the planner's own plan as a manual conflict.

## Battery assumptions

Current default technical assumptions:

- battery capacity: **7.2 kWh**;
- hardware minimum SOC: **5%**;
- configurable maximum charging power;
- configurable maximum discharging power;
- dedicated-group preset: up to **3500 W charge / 3500 W discharge**;
- shared/non-dedicated-group safety preset: maximum **800 W charge / 800 W discharge**;
- charge efficiency: **92%**;
- discharge efficiency: **92%**;
- round-trip efficiency: **84.64%**;
- automatic execution reserve buffer: **2 percentage points**;
- manual plan slots: **3**.

These are integration defaults/project assumptions where applicable; configurable inputs remain selectable through the integration where implemented.

### Electrical connection and central power limits

Dummy OS EMS uses one central pair of power limits throughout the control chain:

- `max_charge_power_w`;
- `max_discharge_power_w`.

For a new installation, Config Flow asks whether the battery is on a dedicated electrical group. A dedicated group can be configured up to 3500 W for charge and discharge. A shared/non-dedicated group is fail-safe capped at 800 W for both directions. The same values can later be changed through Options Flow.

Existing entries upgraded from an older alpha without an explicit electrical profile fall back to the conservative shared-group limit of 800 W until the user confirms the installation profile in **Configure**.

The planner, Action Bridge, Scheduler, pre-start validator, Safety Guard and Execution Controller all use these same configured limits. A layer is not allowed to plan, approve or execute power above the configured value.

## Required and supported sources

### Home Assistant

Minimum supported version: **Home Assistant Core 2026.7.0**.

### Anker Solix integration

Dummy OS EMS uses the existing Anker Solix Home Assistant integration as the device communication layer. Dummy OS EMS does not replace that integration; it adds planning, safety and control logic above it.

During Config Flow the user maps functions such as:

- SOC;
- device status;
- charge power;
- discharge power;
- grid import/export power;
- operating mode;
- charge/discharge direction;
- power setpoint.

### Forecast sources

The 72-hour planner can use selectable Home Assistant sources for:

- known electricity prices;
- price forecast beyond known day-ahead hours;
- home-consumption forecast;
- solar forecast for today, tomorrow and day 3.

The current project uses EnergyZero-compatible price data and Solcast-compatible solar data, but local entity IDs are not hardcoded into the integration architecture.

## Architecture

The integration is split into the following functional layers:

`Config Flow -> Coordinator -> Planner -> Action Bridge -> Plan Store -> Scheduler -> Pre-Start/Safety -> Execution Controller -> Anker control entities`

Supporting modules include source monitoring, energy-need calculation, physical test tooling and Home Assistant entity platforms.

### Plan Store

Exactly three persistent plan slots are maintained. Manual actionable plans always have priority over automatic writes.

Automatic planner-owned plans can be reconciled while still safely in the future. Cancelled, completed, failed or empty slots can be reused. Due/start-ready automatic plans are protected from rolling forecast rewrites.

### Scheduler

The Scheduler manages lifecycle timing, start windows and selection of plans. Automatic planner plans can currently be handed to the Scheduler, but unattended physical execution is not yet enabled.

### Safety Guard and Execution Controller

The existing manual execution path has been physically validated for controlled charge/discharge, safe stop and return to `self_consumption`. The automatic planner path now reaches the Safety Guard and a non-actuating Execution Controller handoff preview after the authoritative pre-start gate. The preview validates the final controller-facing plan parameters and controller-idle/control-path prerequisites, but deliberately performs no mode switch, direction change, power setpoint or physical execution.

## Home Assistant entities

The integration currently creates **105 entities** across sensor, binary sensor, select, number and datetime platforms.

Technical entity IDs and friendly names use English naming. Dashboard labels may remain Dutch. Newly created visible integration names begin with **Dummy OS EMS**.

For planner/scheduler development, `sensor.dummy_os_ems_bridge_candidates` exposes the most detailed bridge, Plan Store, Scheduler, pre-start, Safety Guard and Execution Controller handoff diagnostics as attributes.

## Services

The integration contains services for manual plan management, direct controlled execution, stopping execution and physical test functions. Service definitions are documented by Home Assistant from `services.yaml` after installation.

Automatic planner execution does **not** currently call the physical execution path unattended.

## Installation

For local development/testing:

1. Copy `custom_components/anker_ems/` to `/config/custom_components/anker_ems/`.
2. Restart Home Assistant.
3. Add **Dummy OS EMS** through Settings -> Devices & services.
4. Map the required source and control entities in Config Flow.
5. Validate entity availability before enabling any physical test or manual execution.

The GitHub repository is intended to be HACS-compatible. During alpha development, GitHub Releases are used for explicit versioned test packages.

## Safety rules

- Never run two physical battery controllers at the same time.
- Manual/user-modified plans override automatic planner plans.
- The Anker 5% minimum SOC is never planned below.
- Invalid or unavailable critical sources must block automatic progress.
- Automatic planner writes, Scheduler handoff and physical execution are separate gates.
- A future forecast is not treated as proof that a battery action is safe at execution time.
- Live conditions are revalidated immediately before execution.
- Any future automatic execution must fail safe and return the battery to `self_consumption` when control cannot be proven safe.

## Roadmap

Current priorities are:

- live-validation of the real Scheduler-ready pre-start gate;
- live-validation of the automatic Scheduler -> Safety Guard handoff;
- automatic Safety Guard -> Execution Controller handoff;
- one-controller-at-a-time enforcement;
- safe abort/recovery during execution;
- first limited automatic physical charge/discharge tests;
- event-driven replanning;
- Afwezigheidsmodus;
- plan-versus-actual evaluation;
- daily plan notification;
- analysis of Anker connection drops and slow charging;
- eventual removal of temporary YAML/Jinja planner layers after functional parity.

A later evaluation will also determine whether extra battery capacity is financially worthwhile using real EMS history, utilization, avoided expensive import, trading value, losses and payback period.

## Development history

Release-specific development history is intentionally **not kept in this README**.

Use:

- `CHANGELOG.md` for version-by-version changes;
- GitHub Releases for release notes and downloadable test builds;
- the project handover documentation for full technical history and design decisions.

## License and disclaimer

See `LICENSE` and `NOTICE.md` in this repository. Dummy OS EMS is experimental software. Battery control can affect energy costs and equipment behaviour; validate configuration and safety limits before using physical control functions.

### Supplier-independent price foundation
Alpha40.4 retains the opt-in Stroomvoorspeller market-price layer with separate import/export markups. The hourly planner remains the effective resolution in this alpha; quarter-hour selection is stored for the next planner-resolution step. Legacy price sources remain available as fallback until live validation is complete.
