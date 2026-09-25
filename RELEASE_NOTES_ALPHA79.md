# Dummy OS EMS 0.0.1-alpha.79

## Physical self-consumption planner correction

This prerelease corrects the low-solar planning behavior where forecast demand
until the next usable solar block could be converted into a 100% reserve floor,
even though the physical Anker battery remained in `self_consumption` and would
continue supplying the home.

## Changed

- Energy Need now separates:
  - forecast household demand until usable solar;
  - stored battery energy required to cover that demand;
  - unavoidable direct grid import once the battery reaches its technical minimum;
  - the optional stored-energy amount that could be shifted to an earlier charge window.
- A requested planning reserve is no longer treated as physically enforceable in
  normal `self_consumption`.
- Plan72 projects normal household discharge down to the physical minimum SOC.
- Trade reservation can no longer suppress normal household discharge while the
  battery is in `self_consumption`.
- If later grid import is unavoidable, Planner Preview searches for an earlier
  charge window and selects it only when battery round-trip delivered energy is
  cheaper than buying that household energy directly later.
- The new explicit action purpose is `zelfconsumptie_bijladen`.
- Plan72 exposes `charge_from_grid_support_kwh` and a total support-charge
  diagnostic alongside existing safety and trade flows.
- The external-control reserve remains applicable to explicit third-party
  discharge actions; it is no longer used as a fictitious hold floor for normal
  self-consumption projection.

## Safety boundary

Unchanged:
- normal mode remains `self_consumption`;
- direct power control still requires the guarded `third_party_control` path;
- 0 W guard, Scheduler, Prestart, Safety, Final Revalidation and safe return
  remain authoritative;
- solar charging and normal household discharge are not converted into explicit
  third-party-control actions;
- support charging is a deliberate temporary charge action and therefore still
  passes the existing execution gates.

## Regression coverage

Alpha79 adds tests proving:
1. low solar plus demand above battery capacity does not create a fictitious
   100% discharge block;
2. with no cheaper charge window the projected battery is allowed to reach 5%;
3. a genuinely cheaper earlier window creates a limited support-charge action;
4. the Action Bridge promotes support charge but never normal household discharge.

## Upgrade note

After installation, allow the planner to refresh naturally and compare Plan72
with the physical battery. During low-solar periods the expected SOC line should
now follow normal self-consumption instead of remaining artificially pinned by a
calculated demand reserve.

### Version
`0.0.1-alpha.79`
