# Dummy OS EMS 0.0.1-alpha.76

## Forecast -> EMS migration Step 2 profile-gate fix

This prerelease fixes the live-discovered legacy profile-field mismatch in the Step-2 shadow-only parallel comparator.

### Fixed

- Recognize Package-41 top-level `operating_mode` in addition to the already supported `profile` and `mode` fields.
- Validate the `profile` of every exactly matched legacy UTC hour before content metrics are allowed.
- Require the live normal/normal comparison context to be explicit on both levels:
  - resolved legacy top-level profile is `normal`;
  - Contract v1 profile is `normal`;
  - every matched legacy hour has an explicit per-row profile and all are `normal`.
- Mixed, vacation, missing or otherwise non-normal matched-hour profile context remains blocked; nothing is silently assumed to be normal.
- Publish compact profile-gate diagnostics through the existing `sensor.dummy_os_ems_forecast_parallel_compare` state, including profile source, matched profile counts, explicit-profile hour count, missing-profile hour count and mixed-profile hour count.

### Unchanged safety boundary

- The active Home Forecast remains `sensor.forecast_home_consumption_data`.
- Package 41 remains the active Plan72 reference and rollback source.
- Forecast Contract v1 remains shadow-only.
- No comparator value is inserted into coordinator data.
- Energy Need, Plan72, Bridge, Plan Store, Scheduler, Safety, Final Revalidation, Source Monitor and physical Execution are unchanged.
- `shadow_only=true`, `plan72_source=false`, `active_use_permitted=false`, `physical_execution_authority=false` and `published_pairs=false` remain mandatory.

### Live validation after installation

After installing `0.0.1-alpha.76` and restarting Home Assistant, verify `sensor.dummy_os_ems_forecast_parallel_compare`:

1. `legacy_profile=normal` and `legacy_profile_source=operating_mode` for the current Package-41 normal context.
2. `profile_comparable=true` only when every matched legacy hour is explicitly `normal` and Contract v1 is `normal`.
3. The currently observed one-hour window shift remains an exact 71-hour contiguous UTC overlap when source windows are otherwise unchanged.
4. `legacy_matched_total_kwh`, `contract_matched_total_kwh`, total delta, MAE, signed bias and maximum absolute hourly delta become populated from matched timestamps only.
5. Contract runtime unavailability remains a warning separate from structural validity.
6. Forecast Status, Plan72 and Source Monitor remain on the legacy active path and no physical command is caused by this comparator.

Step 3 remains blocked until this fix is installed and live validated.