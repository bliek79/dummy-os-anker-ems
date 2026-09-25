# Dummy OS EMS 0.0.1-alpha.80

## Cheapest Energy Safety Planner

This prerelease keeps the public planner surface compact and moves low-solar / winter coverage back into the existing `veiligheidsladen` contract.

### Core rule
Within the rolling 72-hour plan, the planner chooses the cheapest technically feasible way to keep forecast household demand covered while preserving the existing planning margin:
- 5% technical minimum SOC;
- +7% software reserve;
- 12% planning target in total.

Solar remains the first energy source. Expected solar is used before grid charging, and the first usable-solar block remains diagnostic context rather than the end of the economic calculation.

### Changed
- Low-solar planning remains valid even when no two-hour usable-solar block exists in the horizon.
- The safety planner simulates the full 72-hour SOC route.
- When the projected route would fall below the 12% planning target, the planner searches all technically feasible grid-charge hours before that deadline and chooses the cheapest one.
- If a later charge window is cheaper and the battery can safely reach it, the earlier more expensive window is skipped.
- If the later cheaper window cannot be reached safely, only the necessary bridge energy is bought earlier.
- A cheap window may charge up to 100% when later forecast demand requires that energy.
- Charge/discharge efficiency remains part of economic comparisons (default 92% / 92%).
- Normal `self_consumption` home discharge is projected physically down to the 5% device minimum; reserve intent does not fictitiously stop home discharge.
- Trade remains secondary to household safety coverage.

### Compactness guarantee
No new public sensor, charge stream or purpose is introduced.
The existing categories remain:
- `veiligheidsladen`
- `handelsladen`
- solar charging
- home discharge

The rejected `zelfconsumptie_bijladen` / `charge_from_grid_support_kwh` contract is not present.

### Safety boundary
Existing Plan Store, Scheduler, Prestart, Safety, Final Revalidation, authority fence, 0 W guard, `third_party_control`, power limits and safe-return behavior remain in place.

### Version
`0.0.1-alpha.80`
