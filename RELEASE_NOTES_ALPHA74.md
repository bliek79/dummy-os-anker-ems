# Dummy OS EMS 0.0.1-alpha.74

## Forecast -> EMS Step 1: contract shadow adapter

This pre-release adds the first isolated consumer for the canonical Dummy OS Forecast -> Planner contract.

### Added

- New `forecast_contract_adapter.py` that reads and independently validates `sensor.do_energy_forecast_planner_contract`.
- Hard checks for contract/schema/profile versions, supported profiles, 15-minute/288-slot native architecture, 60-minute/72-hour planner projection, four populated quarters per hour, contiguous aware timestamps, non-negative finite `energy_kwh`, no padding, no second forecast architecture and no physical execution authority.
- Exact normalization of contract `hours[].energy_kwh` to internal hourly `home_consumption_kwh` rows without re-aggregation or zero fabrication.
- Separate structural readiness and runtime-operational diagnostics.
- Compact SHA-256 consumer signature for meaningful contract-content changes.
- Compact Home Assistant shadow state: `sensor.dummy_os_ems_forecast_contract_shadow`.
- Isolated unit tests for valid, runtime-blocked and malformed contract payloads.

### Safety / migration scope

- Shadow only: the contract is **not** connected to Energy Need, Plan72, Bridge, Scheduler, Safety or Execution.
- The active Plan72 Home Forecast remains `sensor.forecast_home_consumption_data`.
- Source Monitor and planner refresh token remain unchanged in Step 1, so Forecast-contract updates cannot trigger a Plan72 refresh.
- No physical control behavior is changed.
- Package 41 remains active and available for comparison/rollback.

### Live validation after install

Verify `sensor.dummy_os_ems_forecast_contract_shadow` together with the unchanged legacy Forecast Status and Plan72 sensors. The shadow state should expose structural readiness, runtime status, profile, planner window, 72-hour count, total/min/max energy, compact blockers and consumer signature without publishing a second 72-hour attribute array.
