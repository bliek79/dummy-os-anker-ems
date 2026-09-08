# Dummy OS EMS 0.0.1-alpha.75

## Forecast -> EMS migration Step 2

This prerelease adds a shadow-only parallel comparison between the active Package-41 Home Forecast and Forecast -> Planner Contract v1.

### Added

- `forecast_parallel_compare.py`: pure comparison module that normalizes the legacy Package-41 forecast with the same hourly energy semantics used by the active EMS consumer path.
- Exact UTC-hour intersection only; no index matching, nearest-neighbour correction, interpolation, padding or missing-to-zero fallback.
- Compact Home Assistant diagnostic state: `sensor.dummy_os_ems_forecast_parallel_compare`.
- Comparison metrics over exactly matched timestamps only:
  - matched hour count and overlap coverage;
  - legacy/contract source windows and start offset;
  - legacy-only and contract-only hour counts;
  - matched legacy and contract energy totals;
  - total delta and percentage;
  - mean absolute and signed hourly delta;
  - maximum absolute hourly delta and timestamp;
  - deterministic SHA-256 comparison signature.
- Explicit legacy diagnostics for invalid rows, exact timestamp de-duplication and negative-value clamping that mirrors the existing active legacy consumer semantics.
- Runtime availability remains separate from structural Contract-v1 validity. A structurally valid contract may still be compared while runtime input is currently unavailable.
- Normal/normal is the only profile context accepted for a Step-2 content comparison. Vacation/away mapping remains deferred to Step 3.
- Isolated standard-library unit tests for exact 72-hour equality, shifted windows, timezone equivalence, sub-hourly summing, invalid data, negative clamping, runtime separation, structural blocking, profile gating and zero-reference percentage handling.

### Safety boundary

- The active Home Forecast remains `sensor.forecast_home_consumption_data`.
- Package 41 remains the active Plan72 reference and rollback source.
- No Step-2 value is inserted into coordinator data.
- Energy Need, Plan72, Bridge, Plan Store, Scheduler, Safety, Final Revalidation, Source Monitor and physical Execution are not changed by this release.
- `shadow_only=true`, `plan72_source=false`, `active_use_permitted=false`, `physical_execution_authority=false` and `published_pairs=false` remain explicit in the comparison diagnostic.
- No second 72-hour or paired-hour array is published to Home Assistant attributes.

### Live validation after installation

After installing `0.0.1-alpha.75` and restarting Home Assistant, verify:

1. `sensor.dummy_os_ems_forecast_parallel_compare` exists.
2. Current normal/normal context reports `profile_comparable=true`.
3. Exact overlap is at least 24 contiguous UTC hours for Step-2 completion.
4. Delta metrics are populated only from matched timestamps.
5. Forecast Status still uses `sensor.forecast_home_consumption_data` for Home Forecast.
6. Plan72 remains legacy-fed and unchanged by the comparator.
7. Source Monitor still follows only the existing `home_forecast` source.
8. No physical battery command or planner cutover is caused by the comparator.

Step 3 remains blocked until this prerelease is installed and the live parallel comparison has been validated.
