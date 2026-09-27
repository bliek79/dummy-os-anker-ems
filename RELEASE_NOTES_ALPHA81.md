# Dummy OS EMS 0.0.1-alpha.81

## Multi-rate Planner Runtime

This prerelease candidate changes planner orchestration only. The Alpha80
Cheapest Energy Safety Planner remains the policy baseline.

### Why
Alpha80 still evaluated Energy Need and Planner Preview synchronously in the
10-second coordinator cycle. Cheapest-energy safety planning therefore remained
coupled to Home Assistant's fast live/safety path even though final Plan72 was
cached separately.

### Runtime correction
- Keeps the coordinator fast path at 10 seconds for live SOC, control-path,
  Source Monitor, Plan Store/Scheduler lifecycle, Pre-Start, Safety Guard,
  Final Revalidation and guarded physical execution.
- Moves Energy Need + Planner Preview + Plan72 into one atomic cached planner
  bundle.
- Recomputes the heavy bundle on native 15-minute boundaries plus explicit
  source/recovery/start-critical events.
- Runs the complete Alpha80 bundle in Home Assistant's executor, outside the
  event loop.
- Uses a deterministic native-quarter input signature to suppress duplicate
  heavy work.
- Uses single-flight planning with a generation fence; stale results are
  discarded rather than published.
- Keeps the previous valid bundle while a newer generation computes.
- Adds compact runtime diagnostics for planner generation, compute count,
  stale discards, same-signature skips, cycle/signature and worker errors.

### Alpha80 policy freeze
The following policy files are intentionally unchanged:
- energy_need.py
- planner_preview.py
- planner_72h.py

Their exact SHA-256 values are enforced by the Alpha81 regression suite and CI.

### Policy and safety unchanged
Alpha81 does not change:
- 5% technical minimum SOC;
- +7% software reserve;
- 12% planning target;
- solar-first behavior;
- cheapest technically reachable safety charging;
- bridge energy only when required to safely reach a cheaper later window;
- charging up to 100% when forecast demand requires it;
- trade priority below household safety;
- Plan Store, Scheduler, Pre-Start, Safety Guard, Final Revalidation,
  authority fence, 0 W guard or safe-return behavior.

No new charge category is introduced.

### Release gate
This branch and its CI are validation-only. There is deliberately no automatic
Alpha81 publish job. Merge and prerelease publication remain separate explicit
user gates.
