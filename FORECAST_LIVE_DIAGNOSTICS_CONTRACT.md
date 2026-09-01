# Forecast live diagnostics contract

This file fixes the entity-ID contract before live coordinator wiring, in line with the Dummy OS EMS naming rule.

## Exact entity IDs

The future live shadow diagnostics will use exactly these entity IDs:

- `sensor.do_ems_home_forecast_evaluation`
  - persistent forecast-versus-actual evaluation;
  - state: evaluation status;
  - attributes: points, MAE, bias, daily bias, totals, day-part groups and retained comparison rows.

- `sensor.do_ems_home_forecast_comparison`
  - external-versus-internal hourly shadow comparison;
  - state: comparison status;
  - attributes: matched hours, overlap, MAE, bias, totals, delta and per-hour rows for dashboard visualisation.

- `sensor.do_ems_home_forecast_transition`
  - combined transition/readiness diagnostics;
  - state: `learning`, `shadow`, `candidate` or `leading_ready`;
  - attributes: blockers, source decision, planner-adapter completeness and presence-profile readiness.

## Safety contract

These entities are diagnostics only. Creating or updating them must never:

- change the configured Home Forecast source;
- alter Energy Need input;
- alter Plan72 input;
- write automatic plan slots;
- arm or execute physical battery control.

The active source remains external until a later explicit migration step passes the readiness gates and is separately approved.

## Presence profile contract

Normal and absence history must remain logically separate before the internal forecast can become leading. Until the real absence source is explicitly configured, the diagnostic state must report `not_configured` and learning remains in the normal profile. No Home Assistant entity ID may be guessed for the absence source.
