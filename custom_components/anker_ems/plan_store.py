from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLAN_SLOT_COUNT

STORAGE_VERSION = 1

CONTROL_FIELDS = {
    "action",
    "execution_mode",
    "start_time",
    "power_w",
    "target_soc",
    "max_runtime_h",
    "max_start_delay_min",
}

DEFAULT_PLAN: dict[str, Any] = {
    "action": "geen",
    "execution_mode": "direct",
    "start_time": None,
    "power_w": 100,
    "target_soc": 80,
    "max_runtime_h": 2.0,
    "max_start_delay_min": 15,
    "lifecycle_status": "concept",
    "lifecycle_reason": None,
    "lifecycle_updated_at": None,
    "origin": "manual",
    "purpose": None,
    "planner_generated_at": None,
    "planner_signature": None,
}


class AnkerEmsPlanStore:
    """Persistent storage for the three independent EMS plan slots."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.plans",
        )
        self._plans: dict[int, dict[str, Any]] = {
            slot: deepcopy(DEFAULT_PLAN) for slot in range(1, PLAN_SLOT_COUNT + 1)
        }
        self._listeners: set[Callable[[], None]] = set()

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return

        raw_plans = stored.get("plans", {})
        if not isinstance(raw_plans, dict):
            return

        for slot in range(1, PLAN_SLOT_COUNT + 1):
            raw = raw_plans.get(str(slot))
            if not isinstance(raw, dict):
                continue
            merged = deepcopy(DEFAULT_PLAN)
            for key in DEFAULT_PLAN:
                if key in raw:
                    merged[key] = raw[key]
            self._plans[slot] = merged

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(callback)

        def remove_listener() -> None:
            self._listeners.discard(callback)

        return remove_listener

    def get_plan(self, slot: int) -> dict[str, Any]:
        return deepcopy(self._plans[slot])

    def get_value(self, slot: int, key: str) -> Any:
        return self._plans[slot].get(key)

    async def async_set_value(self, slot: int, key: str, value: Any) -> None:
        if slot not in self._plans:
            raise ValueError(f"Unknown plan slot: {slot}")
        if key not in CONTROL_FIELDS:
            raise ValueError(f"Unknown plan field: {key}")

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            value = value.isoformat()

        self._plans[slot][key] = value
        # Entity edits are explicit user edits. They immediately claim the slot
        # from the automatic planner so a later rolling refresh cannot overwrite
        # a value the user has just changed.
        self._plans[slot]["origin"] = "manual"
        self._plans[slot]["purpose"] = None
        self._plans[slot]["planner_generated_at"] = None
        self._plans[slot]["planner_signature"] = None
        # Any user edit makes a terminal/active plan eligible for a fresh
        # lifecycle. This prevents completed plans from silently becoming
        # start-ready again until the user actually changes the plan.
        self._plans[slot]["lifecycle_status"] = "concept"
        self._plans[slot]["lifecycle_reason"] = "plan_changed"
        self._plans[slot]["lifecycle_updated_at"] = dt_util.now().isoformat()
        await self._async_save()
        self._notify_listeners()


    async def async_sync_automatic_plans(
        self, desired: dict[int, dict[str, Any]]
    ) -> dict[str, Any]:
        """Atomically sync observer-approved planner proposals into free slots.

        Alpha30 first stores generated plans as ``concept``. A separate guarded
        handoff may then promote matching automatic concepts to ``pending``.
        Existing non-terminal manual plans are never overwritten.
        """
        changed_slots: list[int] = []
        written_slots: list[int] = []
        cleared_slots: list[int] = []
        skipped_slots: list[int] = []
        now_iso = dt_util.now().isoformat()

        def terminal(plan: dict[str, Any]) -> bool:
            action = plan.get("action")
            status = str(plan.get("lifecycle_status") or "").lower()
            return action in (None, "geen") or status in {"geannuleerd", "voltooid", "fout"}

        for slot in range(1, PLAN_SLOT_COUNT + 1):
            current = self._plans[slot]
            proposal = desired.get(slot)
            current_origin = str(current.get("origin") or "manual")
            current_lifecycle = str(current.get("lifecycle_status") or "").lower()
            reusable = (
                (current_origin == "automatic_72h_planner" and current_lifecycle == "concept")
                or terminal(current)
            )

            if proposal is not None:
                if not reusable:
                    skipped_slots.append(slot)
                    continue

                new_plan = deepcopy(DEFAULT_PLAN)
                for key in CONTROL_FIELDS:
                    if key in proposal:
                        new_plan[key] = proposal[key]
                new_plan["lifecycle_status"] = "concept"
                new_plan["lifecycle_reason"] = "automatic_preview_written_no_handoff"
                new_plan["lifecycle_updated_at"] = now_iso
                new_plan["origin"] = "automatic_72h_planner"
                new_plan["purpose"] = proposal.get("purpose")
                new_plan["planner_generated_at"] = now_iso
                new_plan["planner_signature"] = proposal.get("planner_signature")

                # Do not write persistent storage every coordinator poll. The
                # bridge signature changes only when the actual planner proposal
                # changes materially (source hours, purpose, target or energy).
                if (
                    current_origin == "automatic_72h_planner"
                    and current.get("planner_signature") == new_plan.get("planner_signature")
                ):
                    continue

                comparable_current = deepcopy(current)
                # Generated-at/lifecycle timestamps are metadata, not plan identity.
                for key in ("planner_generated_at", "lifecycle_updated_at"):
                    comparable_current[key] = None
                comparable_new = deepcopy(new_plan)
                for key in ("planner_generated_at", "lifecycle_updated_at"):
                    comparable_new[key] = None

                if comparable_current != comparable_new:
                    self._plans[slot] = new_plan
                    changed_slots.append(slot)
                    written_slots.append(slot)
                continue

            # Only clear stale planner-owned concepts. Manual slots are untouched.
            if (
                current_origin == "automatic_72h_planner"
                and current_lifecycle == "concept"
            ):
                already_cleared = (
                    current.get("action") in (None, "geen")
                    and current.get("planner_signature") is None
                    and current.get("purpose") is None
                    and current.get("lifecycle_reason") == "automatic_preview_cleared"
                )
                if not already_cleared:
                    empty = deepcopy(DEFAULT_PLAN)
                    empty["lifecycle_status"] = "concept"
                    empty["lifecycle_reason"] = "automatic_preview_cleared"
                    empty["lifecycle_updated_at"] = now_iso
                    self._plans[slot] = empty
                    changed_slots.append(slot)
                    cleared_slots.append(slot)

        if changed_slots:
            await self._async_save()
            self._notify_listeners()

        return {
            "changed": bool(changed_slots),
            "changed_slots": changed_slots,
            "written_slots": written_slots,
            "cleared_slots": cleared_slots,
            "skipped_slots": skipped_slots,
        }

    async def async_handoff_automatic_plans(
        self, allowed: dict[int, str]
    ) -> dict[str, Any]:
        """Promote matching planner-owned concepts to Scheduler-visible pending.

        The caller must already have passed planner, forecast and execution-buffer
        gates. A slot is promoted only when it is still planner-owned, still a
        concept, and its persistent planner signature exactly matches the current
        bridge proposal. This makes the handoff deterministic and prevents stale
        or user-edited plans from entering the Scheduler.
        """
        handed_off: list[int] = []
        skipped: list[int] = []
        now_iso = dt_util.now().isoformat()

        for slot, signature in allowed.items():
            if slot not in self._plans:
                skipped.append(slot)
                continue
            plan = self._plans[slot]
            if (
                plan.get("origin") != "automatic_72h_planner"
                or str(plan.get("lifecycle_status") or "").lower() != "concept"
                or not signature
                or plan.get("planner_signature") != signature
                or plan.get("action") not in {"laden", "ontladen"}
                or plan.get("execution_mode") != "gepland"
            ):
                skipped.append(slot)
                continue

            start_raw = plan.get("start_time")
            start = dt_util.parse_datetime(str(start_raw)) if start_raw else None
            if start is None:
                skipped.append(slot)
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            # Do not hand stale planner data to the Scheduler. A start inside
            # the configured start window may still be valid, including a plan
            # generated for the currently running hour.
            delay = float(plan.get("max_start_delay_min") or 0)
            if dt_util.now() > start + timedelta(minutes=delay):
                skipped.append(slot)
                continue

            plan["lifecycle_status"] = "pending"
            plan["lifecycle_reason"] = "automatic_scheduler_handoff"
            plan["lifecycle_updated_at"] = now_iso
            handed_off.append(slot)

        if handed_off:
            await self._async_save()
            self._notify_listeners()

        return {
            "changed": bool(handed_off),
            "handed_off_slots": handed_off,
            "skipped_slots": skipped,
        }

    async def async_mark_lifecycle(
        self, slot: int, status: str, reason: str | None = None
    ) -> None:
        if slot not in self._plans:
            raise ValueError(f"Unknown plan slot: {slot}")
        if status not in {
            "concept",
            "pending",
            "actief",
            "voltooid",
            "geannuleerd",
            "fout",
        }:
            raise ValueError(f"Unknown lifecycle status: {status}")

        self._plans[slot]["lifecycle_status"] = status
        self._plans[slot]["lifecycle_reason"] = reason
        self._plans[slot]["lifecycle_updated_at"] = dt_util.now().isoformat()
        await self._async_save()
        self._notify_listeners()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "plans": {
                    str(slot): deepcopy(plan)
                    for slot, plan in self._plans.items()
                }
            }
        )

    def _notify_listeners(self) -> None:
        for callback in tuple(self._listeners):
            callback()

    def plan_status(self, slot: int) -> str:
        plan = self._plans[slot]
        action = plan.get("action")
        execution_mode = plan.get("execution_mode")
        lifecycle_status = plan.get("lifecycle_status", "pending")

        if lifecycle_status in {"actief", "voltooid", "geannuleerd", "fout"}:
            return str(lifecycle_status)
        start_time = plan.get("start_time")
        power = plan.get("power_w")
        target_soc = plan.get("target_soc")
        runtime = plan.get("max_runtime_h")
        delay = plan.get("max_start_delay_min")

        if action == "geen":
            return "leeg"
        if lifecycle_status == "concept":
            return "concept"
        if action not in {"laden", "ontladen"}:
            return "ongeldig"
        if execution_mode not in {"direct", "gepland"}:
            return "ongeldig"
        if not isinstance(power, (int, float)) or not 100 <= float(power) <= 3500:
            return "ongeldig"
        if not isinstance(target_soc, (int, float)) or not 5 <= float(target_soc) <= 100:
            return "ongeldig"
        if not isinstance(runtime, (int, float)) or not 0.25 <= float(runtime) <= 12:
            return "ongeldig"
        if not isinstance(delay, (int, float)) or not 1 <= float(delay) <= 120:
            return "ongeldig"

        if execution_mode == "direct":
            return "direct_klaar"

        parsed = dt_util.parse_datetime(str(start_time)) if start_time else None
        if parsed is None:
            return "wacht_op_starttijd"
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if parsed < dt_util.now():
            return "starttijd_verstreken"
        return "gepland"
