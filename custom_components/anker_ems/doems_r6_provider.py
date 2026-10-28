"""Read-only DOEMS R6 publication adapter for the existing Alpha84 coordinator.

No automatic registration, plan-store writes, physical commands or authority transfer.
"""
from __future__ import annotations

from typing import Any


def read_doems_r6_publication(hass: Any) -> dict[str, Any]:
    """Collect current, individually witnessed automatic R6 plans; fail closed."""
    runtimes = hass.data.get("doems", {})
    if not isinstance(runtimes, dict) or len(runtimes) != 1:
        raise ValueError("Exactly one DOEMS runtime required")
    runtime = next(iter(runtimes.values()))
    if not isinstance(runtime, dict):
        raise ValueError("DOEMS runtime unavailable")
    bridge = runtime.get("r6_slot_bridge")
    planner = runtime.get("planner")
    store = runtime.get("manual_plan_store")
    if bridge is None or planner is None or store is None:
        raise ValueError("DOEMS R6 components unavailable")
    if not isinstance(getattr(bridge, "last_result", None), dict) or bridge.last_result.get("status") != "ready":
        raise ValueError("DOEMS R6 publication not ready")
    generation = getattr(planner, "_generation", None)
    if type(generation) is not int or generation < 0:
        raise ValueError("DOEMS generation unavailable")

    proposals: dict[int, dict[str, Any]] = {}
    for slot in (1, 2, 3):
        plan = store.get_plan(slot)
        if not isinstance(plan, dict):
            raise ValueError("DOEMS slot unavailable")
        if plan.get("origin") != "automatic_72h_planner":
            continue  # Manual-owned slots must never be copied as automatic.
        proof = bridge.verified_published_candidate(plan)
        if not isinstance(proof, dict):
            raise ValueError(f"DOEMS slot {slot} lacks current R6 witness")
        proposals[slot] = proof
    return {"generation": generation, "proposals": proposals}
