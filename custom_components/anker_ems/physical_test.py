from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    TEST_DEFAULT_DURATION_S,
    TEST_DEFAULT_POWER_W,
    TEST_MAX_DURATION_S,
    TEST_MAX_POWER_W,
    TEST_MIN_DURATION_S,
    TEST_MIN_POWER_W,
)

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 1


class AnkerEmsPhysicalTestController:
    """Run a tightly bounded physical charge test.

    This controller is intentionally separate from the normal Action Controller.
    It can only be started through an explicit service action, only charges, and
    always attempts to return the battery to self_consumption when it stops.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.physical_test"
        )
        self._coordinator = None
        self._cancel_timer: Callable[[], None] | None = None
        self._cancel_monitor: Callable[[], None] | None = None
        self._state: dict[str, Any] = {
            "active": False,
            "status": "idle",
            "reason": "Geen fysieke test actief",
            "power_w": None,
            "duration_s": None,
            "started_at": None,
            "stop_at": None,
            "last_result": None,
        }

    def attach_coordinator(self, coordinator: Any) -> None:
        self._coordinator = coordinator

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            for key in self._state:
                if key in stored:
                    self._state[key] = stored[key]

    @property
    def data(self) -> dict[str, Any]:
        result = dict(self._state)
        result["remaining_s"] = self.remaining_seconds
        return result

    @property
    def remaining_seconds(self) -> int | None:
        if not self._state.get("active") or not self._state.get("stop_at"):
            return None
        stop_at = dt_util.parse_datetime(str(self._state["stop_at"]))
        if stop_at is None:
            return None
        if stop_at.tzinfo is None:
            stop_at = stop_at.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        return max(0, int((stop_at - dt_util.now()).total_seconds()))

    async def _async_save(self) -> None:
        await self._store.async_save(dict(self._state))

    def _entity_ids(self) -> tuple[str, str, str]:
        if self._coordinator is None:
            raise HomeAssistantError("Dummy OS EMS coordinator is niet beschikbaar")
        ids = self._coordinator.control_entity_ids
        mode = ids.get("operating_mode")
        direction = ids.get("action_direction")
        power = ids.get("power_setpoint")
        if not mode or not direction or not power:
            raise HomeAssistantError("Niet alle besturingsentiteiten zijn geconfigureerd")
        if not mode.startswith("select."):
            raise HomeAssistantError("Bedrijfsmodus moet een select-entiteit zijn")
        if not direction.startswith("select."):
            raise HomeAssistantError("Laad/ontlaadrichting moet een select-entiteit zijn")
        if not power.startswith("number."):
            raise HomeAssistantError("Vermogenssetpoint moet een number-entiteit zijn")
        return mode, direction, power

    async def async_recover_if_needed(self) -> None:
        """Fail safe after a Home Assistant restart during an active test."""
        if not self._state.get("active"):
            return
        _LOGGER.warning("Recovering interrupted Dummy OS EMS physical test")
        await self.async_stop("restart_recovery", emergency=True)

    async def async_start_charge_test(
        self,
        *,
        power_w: int = TEST_DEFAULT_POWER_W,
        duration_s: int = TEST_DEFAULT_DURATION_S,
    ) -> None:
        if self._coordinator is None:
            raise HomeAssistantError("Dummy OS EMS coordinator is niet beschikbaar")
        if self._state.get("active"):
            raise HomeAssistantError("Er is al een fysieke test actief")
        if not TEST_MIN_POWER_W <= power_w <= TEST_MAX_POWER_W:
            raise HomeAssistantError(
                f"Testvermogen moet tussen {TEST_MIN_POWER_W} en {TEST_MAX_POWER_W} W liggen"
            )
        if not TEST_MIN_DURATION_S <= duration_s <= TEST_MAX_DURATION_S:
            raise HomeAssistantError(
                f"Testduur moet tussen {TEST_MIN_DURATION_S} en {TEST_MAX_DURATION_S} seconden liggen"
            )

        await self._coordinator.async_refresh()
        data = self._coordinator.data

        # This alpha only permits an explicit test while the normal EMS remains
        # in simulation mode. It prevents accidental activation of the normal
        # controller path.
        if not data.get("simulation_mode"):
            raise HomeAssistantError("Fysieke test is alleen toegestaan terwijl EMS op simulation staat")
        if not data.get("scheduler_ready"):
            raise HomeAssistantError("Scheduler heeft geen startklaar plan")
        if data.get("controller_action") != "laden":
            raise HomeAssistantError("Alpha 10 ondersteunt uitsluitend een laadtest")
        if not data.get("safety_safe"):
            raise HomeAssistantError(
                f"Safety Guard blokkeert de test: {data.get('safety_reason') or 'onbekende reden'}"
            )
        if data.get("operating_mode") != "third_party_control":
            raise HomeAssistantError("Zet de batterij eerst op third_party_control")
        if data.get("action_direction") is None or data.get("power_setpoint_w") is None:
            raise HomeAssistantError("Besturingsbronnen zijn niet beschikbaar")
        if (data.get("discharge_power_w") or 0) > 100:
            raise HomeAssistantError("Ontlaadvermogen is actief; test wordt niet gestart")

        mode_entity, direction_entity, power_entity = self._entity_ids()
        now = dt_util.now()
        stop_at = now + timedelta(seconds=duration_s)
        self._state.update(
            {
                "active": True,
                "status": "starting",
                "reason": "Fysieke laadtest wordt gestart",
                "power_w": power_w,
                "duration_s": duration_s,
                "started_at": now.isoformat(),
                "stop_at": stop_at.isoformat(),
                "last_result": None,
            }
        )
        await self._async_save()

        try:
            # Direction first, power second. Operating mode is deliberately not
            # switched automatically in alpha 10; the user must arm it manually.
            await self.hass.services.async_call(
                "select",
                "select_option",
                {"option": "charge"},
                target={"entity_id": direction_entity},
                blocking=True,
            )
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"value": power_w},
                target={"entity_id": power_entity},
                blocking=True,
            )
        except Exception as err:
            _LOGGER.exception("Failed to start physical charge test")
            await self.async_stop(f"start_failed: {err}", emergency=True)
            raise HomeAssistantError(f"Start fysieke test mislukt: {err}") from err

        self._state.update(
            {
                "status": "running",
                "reason": f"Laadtest actief: {power_w} W gedurende maximaal {duration_s} s",
            }
        )
        await self._async_save()
        self._schedule_stop(duration_s)
        self._schedule_monitor()
        await self._coordinator.async_refresh()

    def _schedule_stop(self, duration_s: int) -> None:
        if self._cancel_timer is not None:
            self._cancel_timer()
        self._cancel_timer = async_call_later(
            self.hass,
            duration_s,
            lambda _now: self.hass.async_create_task(
                self.async_stop("test_duration_reached", emergency=False)
            ),
        )

    def _schedule_monitor(self) -> None:
        if self._cancel_monitor is not None:
            self._cancel_monitor()
        self._cancel_monitor = async_call_later(
            self.hass,
            5,
            lambda _now: self.hass.async_create_task(self._async_monitor_once()),
        )

    async def _async_monitor_once(self) -> None:
        if not self._state.get("active") or self._coordinator is None:
            return
        await self._coordinator.async_refresh()
        data = self._coordinator.data

        if data.get("operating_mode") != "third_party_control":
            await self.async_stop("operating_mode_changed", emergency=True)
            return
        if data.get("action_direction") != "charge":
            await self.async_stop("direction_changed", emergency=True)
            return
        if data.get("power_setpoint_w") is None:
            await self.async_stop("power_setpoint_unavailable", emergency=True)
            return
        if (data.get("discharge_power_w") or 0) > 100:
            await self.async_stop("unexpected_discharge_detected", emergency=True)
            return
        if not data.get("safety_safe"):
            await self.async_stop("safety_guard_became_unsafe", emergency=True)
            return

        target_soc = data.get("controller_target_soc")
        soc = data.get("soc")
        if target_soc is not None and soc is not None and soc >= target_soc:
            await self.async_stop("target_soc_reached", emergency=False)
            return

        if self.remaining_seconds == 0:
            await self.async_stop("test_duration_reached", emergency=False)
            return

        self._schedule_monitor()

    async def async_stop(self, reason: str, *, emergency: bool = False) -> None:
        """Stop the test and return the battery to self consumption."""
        if self._cancel_timer is not None:
            self._cancel_timer()
            self._cancel_timer = None
        if self._cancel_monitor is not None:
            self._cancel_monitor()
            self._cancel_monitor = None

        mode_entity = direction_entity = power_entity = None
        try:
            mode_entity, direction_entity, power_entity = self._entity_ids()
        except HomeAssistantError:
            pass

        errors: list[str] = []
        if power_entity:
            try:
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {"value": 0},
                    target={"entity_id": power_entity},
                    blocking=True,
                )
            except Exception as err:
                errors.append(f"power_zero_failed: {err}")

        # Give the device a brief moment to accept the zero setpoint before
        # handing control back to its own self-consumption logic.
        await asyncio.sleep(1)

        if mode_entity:
            try:
                await self.hass.services.async_call(
                    "select",
                    "select_option",
                    {"option": "self_consumption"},
                    target={"entity_id": mode_entity},
                    blocking=True,
                )
            except Exception as err:
                errors.append(f"self_consumption_failed: {err}")

        result = "emergency_stopped" if emergency else "completed"
        if errors:
            result = "stop_error"
            reason = f"{reason}; {'; '.join(errors)}"

        self._state.update(
            {
                "active": False,
                "status": result,
                "reason": reason,
                "last_result": result,
                "stop_at": dt_util.now().isoformat(),
            }
        )
        await self._async_save()
        if self._coordinator is not None:
            await self._coordinator.async_refresh()

    async def async_shutdown_stop(self) -> None:
        if self._state.get("active"):
            try:
                await self.async_stop("home_assistant_stop", emergency=True)
            except Exception:
                _LOGGER.exception("Could not stop physical test during Home Assistant shutdown")
