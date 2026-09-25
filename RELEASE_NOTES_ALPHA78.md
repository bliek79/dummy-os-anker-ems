# Dummy OS EMS 0.0.1-alpha.78

## Bridge Recorder payload fix

This prerelease fixes the Home Assistant Recorder overflow on the three Action Bridge entities while preserving the existing physical battery-control behavior.

### Problem
Alpha77 publishes one very large Action Bridge attribute contract on all three public bridge entities:
- `sensor.dummy_os_ems_bridge_status`
- `sensor.dummy_os_ems_bridge_candidates`
- `sensor.dummy_os_ems_bridge_slots`

The shared contract had grown to roughly 160 fields, including candidate arrays, slot previews and later Prestart/Safety/Final-Revalidation diagnostics. Home Assistant therefore repeatedly rejected attributes above its 16,384-byte Recorder limit.

### Changed
- Split the shared bridge attribute contract into three dedicated public contracts:
  - Bridge Status: compact status, gates and safety/execution summaries.
  - Bridge Candidates: candidate-specific data plus compact Prestart context.
  - Bridge Slots: slot-preview, Plan Store and Scheduler-handoff context.
- Candidate arrays are no longer copied onto Status or Slots.
- Slot-preview arrays are no longer copied onto Status or Candidates.
- Large live arrays such as `candidates`, `slot_preview`, `manual_slots` and suppressed-hour detail remain available live but are excluded from Recorder.
- Added a hard regression budget of 10 KiB for the Recorder-bound attributes of all three bridge entities.

### Unchanged
- Automatic Execution remains fully supported and may remain ON.
- `third_party_control` remains the intended guarded external-control mode during physical execution.
- Planner, Plan Store, Scheduler, Prestart, Safety, Final Revalidation, execution controller and safe-return policy are unchanged.
- The existing fast safety/monitor refresh cadence is unchanged.
- No Modbus write/read behavior is changed by this release.
- The Alpha77 legacy authority fence remains intact and authoritative.

### Live acceptance
After installation:
1. keep Automatic Execution in its normal enabled state;
2. observe normal coordinator refresh and, when naturally available, a Prestart/execution refresh phase;
3. confirm Recorder no longer reports >16,384-byte attributes for bridge_status, bridge_candidates or bridge_slots;
4. assess any remaining Modbus lock/no-response errors separately on the cleaner log.

### Version
`0.0.1-alpha.78`
