# Dummy OS EMS 0.0.1-alpha.77

## Step 5C legacy physical authority fence foundation

This prerelease adds the legacy-controller half of the DOEMS Step 5C authority-transfer design while keeping `anker_ems` as the only physical battery controller.

### Added
- A persistent `AnkerEmsLegacyAuthorityFence` with states `open`, `closing` and `closed`.
- A monotonic legacy authority generation and in-flight write accounting.
- Central dispatch fencing immediately before physical Home Assistant service calls.
- `closing` permits only safe-return writes: power setpoint 0 W and operating mode `self_consumption`.
- `closed` blocks automatic, manual, physical-test, callback and service-driven physical writes.
- Restart during `closing` restores fail-closed as `closed`.
- Read-only `Dummy OS EMS Legacy Authority` diagnostics for Step 5C observation.

### Automatic Execution
The existing Automatic Execution switch is unchanged in meaning:
- ON permits fully guarded automatic planner execution.
- OFF disarms automatic execution and returns the controller to manual operation.
- OFF is not physical authority release.

Automatic Execution cannot be armed while the legacy physical authority fence is not open.

### Physical write coverage
Known physical writes in:
- `execution.py`
- `physical_test.py`
- the `stop_all` safe-return path

are routed through the authority fence.

### Safety boundary
- The fence defaults to OPEN in this release so installed Alpha76 behaviour is preserved after upgrade.
- No automatic authority transfer is started.
- No DOEMS authority is granted.
- There is no new user-facing fence close/open service in this release.
- This release is the disarmed 5C-B prerequisite only.
- 5C-C live quiesce/no-owner validation remains a separate explicitly approved step.

### Version
`0.0.1-alpha.77`
