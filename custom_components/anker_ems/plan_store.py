from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLAN_SLOT_COUNT

STORAGE_VERSION = 1

DEFAULT_PLAN: dict[str, Any] = {
    "action": "geen",
    "execution_mode": "direct",
    "start_time": None,
    "power_w": 100,
    "target_soc": 80,
    "max_runtime_h": 2.0,
    "max_start_delay_min": 15,
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
        if key not in DEFAULT_PLAN:
            raise ValueError(f"Unknown plan field: {key}")

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            value = value.isoformat()

        self._plans[slot][key] = value
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
        start_time = plan.get("start_time")
        power = plan.get("power_w")
        target_soc = plan.get("target_soc")
        runtime = plan.get("max_runtime_h")
        delay = plan.get("max_start_delay_min")

        if action == "geen":
            return "leeg"
        if action not in {"laden", "ontladen"}:
            return "ongeldig"
        if execution_mode not in {"direct", "gepland"}:
            return "ongeldig"
        if not isinstance(power, (int, float)) or not 100 <= float(power) <= 3500:
            return "ongeldig"
        if not isinstance(target_soc, (int, float)) or not 5 <= float(target_soc) <= 100:
            return "ongeldig"
        if not isinstance(runtime, (int, float)) or not 0.5 <= float(runtime) <= 12:
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
