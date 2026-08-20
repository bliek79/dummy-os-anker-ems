from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_STORAGE_VERSION = 1
_EXTERNAL_MODE = "third_party_control"
_SELF_MODE = "self_consumption"
_MODE_WAIT_SECONDS = 20
_MONITOR_INTERVAL_SECONDS = 5


class AnkerEmsExecutionController:
    """Execute a scheduler-selected plan with an explicit user confirmation.

    Alpha 12 introduces the real execution state machine and automatic mode
    transition. It does not yet auto-trigger from the scheduler: a user/service
    call must explicitly start the selected plan. Charging is physically
    enabled; discharging remains blocked until a separate controlled discharge
    test has been validated.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.execution"
        )
        self._coordinator = None
        self._stop_task: asyncio.Task[None] | None = None
        self._cancel_monitor: Callable[[], None] | None = None
        self._stop_lock = asyncio.Lock()
        self._state: dict[str, Any] = {
            "active": False,
            "status": "idle",
            "reason": "Geen EMS-uitvoering actief",
            "slot": None,
            "action": None,
            "power_w": None,
            "target_soc": None,
            "max_runtime_h": None,
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

    async def _wait_for_external_controls(self) -> None:
        """Wait until external mode and its dependent control entities are live."""
        if self._coordinator is None:
            raise HomeAssistantError("Dummy OS EMS coordinator is niet beschikbaar")
        deadline = dt_util.now() + timedelta(seconds=_MODE_WAIT_SECONDS)
        while dt_util.now() < deadline:
            await self._coordinator.async_refresh()
            data = self._coordinator.data
            if (
                data.get("operating_mode") == _EXTERNAL_MODE
                and data.get("action_direction") is not None
                and data.get("power_setpoint_w") is not None
            ):
                return
            await asyncio.sleep(1)
        raise HomeAssistantError(
            "Externe modus werd niet tijdig beschikbaar of besturingsbronnen bleven unavailable"
        )

    async def async_recover_if_needed(self) -> None:
        if not self._state.get("active"):
            return
        _LOGGER.warning("Recovering interrupted Dummy OS EMS execution")
        await self.async_stop("restart_recovery", emergency=True)

    def evaluate_automatic_handoff(self, data: dict[str, Any]) -> dict[str, Any]:
        """Evaluate Safety Guard -> Execution Controller handoff without actuating.

        The observer handoff deliberately stops before any Home Assistant service call. The
        method mirrors the final prerequisites the Execution Controller will
        require later, so the complete automatic chain can be observed before
        physical execution is enabled.
        """
        slot = data.get("auto_safety_handoff_selected_slot")
        slots = data.get("scheduler_slots", {}) or {}
        detail = slots.get(slot) or slots.get(str(slot)) or {}
        origin = str(detail.get("origin") or "manual")

        base = {
            "auto_execution_handoff_enabled": True,
            "auto_execution_handoff_required": False,
            "auto_execution_handoff_ready": False,
            "auto_execution_handoff_status": "not_required",
            "auto_execution_handoff_reason": "Geen door Safety Guard goedgekeurde automatische actie",
            "auto_execution_handoff_reasons": [],
            "auto_execution_handoff_warnings": [],
            "auto_execution_handoff_selected_slot": None,
            "auto_execution_handoff_planner_identity": None,
            "auto_execution_handoff_action": None,
            "auto_execution_handoff_power_w": None,
            "auto_execution_handoff_target_soc": None,
            "auto_execution_handoff_max_runtime_h": None,
            "auto_execution_handoff_safety_safe": bool(data.get("auto_safety_handoff_safe")),
            "auto_execution_handoff_control_path_configured": bool(data.get("control_path_configured")),
            "auto_execution_handoff_controller_idle": not bool(data.get("execution_active")),
            "auto_execution_handoff_physical_test_idle": not bool(data.get("physical_test_active")),
            "auto_execution_handoff_final_revalidation_required": True,
            "auto_execution_handoff_execution_permitted": False,
            "auto_execution_handoff_physical_control": False,
        }

        if (
            slot is None
            or data.get("auto_safety_handoff_required") is not True
            or origin != "automatic_72h_planner"
        ):
            return base

        reasons: list[str] = []
        warnings: list[str] = []
        action = detail.get("action")
        try:
            power_w = int(float(detail.get("power_w") or 0))
        except (TypeError, ValueError):
            power_w = 0
        try:
            target_soc = float(detail.get("target_soc") or 0)
        except (TypeError, ValueError):
            target_soc = 0.0
        try:
            max_runtime_h = float(detail.get("max_runtime_h") or 0)
        except (TypeError, ValueError):
            max_runtime_h = 0.0
        planner_identity = detail.get("planner_identity")

        if data.get("auto_safety_handoff_safe") is not True:
            reasons.append("safety_handoff_not_safe")
        if data.get("auto_prestart_safe") is not True:
            reasons.append("prestart_not_safe")
        if data.get("auto_prestart_current_identity_match") is not True:
            reasons.append("planner_identity_mismatch")
        if not planner_identity:
            reasons.append("planner_identity_missing")
        if action not in {"laden", "ontladen"}:
            reasons.append("invalid_action")

        max_power = int(data.get("max_discharge_power_w") or 800) if action == "ontladen" else int(data.get("max_charge_power_w") or 800)
        if not 100 <= power_w <= max_power:
            reasons.append("invalid_power")
        if not 5 <= target_soc <= 100:
            reasons.append("invalid_target_soc")
        if not 0.25 <= max_runtime_h <= 12:
            reasons.append("invalid_runtime")
        if not data.get("control_path_configured"):
            reasons.append("control_path_not_configured")
        if data.get("physical_test_active"):
            reasons.append("physical_test_active")
        if data.get("execution_active"):
            reasons.append("execution_already_active")

        # The actual mode switch and final post-mode revalidation remain future
        # execution-stage responsibilities. They are warnings here, not blockers.
        if data.get("operating_mode") != _EXTERNAL_MODE:
            warnings.append("external_mode_switch_required")
        if data.get("auto_prestart_current_signature_match") is not True:
            warnings.append("planner_revision_changed")

        ready = len(reasons) == 0
        return {
            "auto_execution_handoff_enabled": True,
            "auto_execution_handoff_required": True,
            "auto_execution_handoff_ready": ready,
            "auto_execution_handoff_status": "ready_observe" if ready else "blocked",
            "auto_execution_handoff_reason": (
                "Execution Controller handoff is gereed voor finale live revalidatie; fysieke uitvoering blijft uit"
                if ready
                else ", ".join(reasons)
            ),
            "auto_execution_handoff_reasons": reasons,
            "auto_execution_handoff_warnings": warnings,
            "auto_execution_handoff_selected_slot": slot,
            "auto_execution_handoff_planner_identity": planner_identity,
            "auto_execution_handoff_action": action,
            "auto_execution_handoff_power_w": power_w,
            "auto_execution_handoff_target_soc": target_soc,
            "auto_execution_handoff_max_runtime_h": max_runtime_h,
            "auto_execution_handoff_safety_safe": bool(data.get("auto_safety_handoff_safe")),
            "auto_execution_handoff_control_path_configured": bool(data.get("control_path_configured")),
            "auto_execution_handoff_controller_idle": not bool(data.get("execution_active")),
            "auto_execution_handoff_physical_test_idle": not bool(data.get("physical_test_active")),
            "auto_execution_handoff_final_revalidation_required": True,
            "auto_execution_handoff_execution_permitted": False,
            "auto_execution_handoff_physical_control": False,
        }

    def evaluate_final_revalidation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Perform the last non-actuating live validation before a future mode switch.

        Alpha38 keeps physical execution disabled. This gate mirrors the exact
        conditions that must still be true immediately before the Execution
        Controller may switch the battery to external control in a later
        release. It is intentionally evaluated from the latest coordinator
        snapshot and never calls Home Assistant services.
        """
        slot = data.get("auto_execution_handoff_selected_slot")
        slots = data.get("scheduler_slots", {}) or {}
        detail = slots.get(slot) or slots.get(str(slot)) or {}
        origin = str(detail.get("origin") or "manual")

        base = {
            "auto_final_revalidation_enabled": True,
            "auto_final_revalidation_required": False,
            "auto_final_revalidation_safe": False,
            "auto_final_revalidation_status": "not_required",
            "auto_final_revalidation_reason": "Geen Execution Controller handoff gereed voor finale live validatie",
            "auto_final_revalidation_reasons": [],
            "auto_final_revalidation_warnings": [],
            "auto_final_revalidation_checks": [],
            "auto_final_revalidation_selected_slot": None,
            "auto_final_revalidation_planner_identity": None,
            "auto_final_revalidation_planner_signature": None,
            "auto_final_revalidation_checked_at": dt_util.now().isoformat(),
            "auto_final_revalidation_action": None,
            "auto_final_revalidation_power_w": None,
            "auto_final_revalidation_target_soc": None,
            "auto_final_revalidation_current_soc": self._number_value(data.get("soc")),
            "auto_final_revalidation_execution_reserve_soc": data.get("auto_prestart_execution_reserve_soc"),
            "auto_final_revalidation_control_path_configured": bool(data.get("control_path_configured")),
            "auto_final_revalidation_controller_idle": not bool(data.get("execution_active")),
            "auto_final_revalidation_physical_test_idle": not bool(data.get("physical_test_active")),
            "auto_final_revalidation_mode_switch_required": data.get("operating_mode") != _EXTERNAL_MODE,
            "auto_final_revalidation_execution_permitted": False,
            "auto_final_revalidation_physical_control": False,
        }

        if (
            slot is None
            or data.get("auto_execution_handoff_required") is not True
            or data.get("auto_execution_handoff_ready") is not True
            or origin != "automatic_72h_planner"
        ):
            return base

        reasons: list[str] = []
        warnings: list[str] = []
        checks: list[dict[str, Any]] = []

        def add_check(name: str, passed: bool, detail_text: str, *, warning_only: bool = False) -> None:
            severity = "ok" if passed else ("warning" if warning_only else "blocker")
            checks.append({"check": name, "passed": passed, "severity": severity, "detail": detail_text})
            if not passed:
                (warnings if warning_only else reasons).append(name)

        action = detail.get("action")
        power_w = self._number_value(detail.get("power_w"))
        target_soc = self._number_value(detail.get("target_soc"))
        soc = self._number_value(data.get("soc"))
        charge_power = self._number_value(data.get("charge_power_w"))
        discharge_power = self._number_value(data.get("discharge_power_w"))
        planner_identity = detail.get("planner_identity")
        planner_signature = detail.get("planner_signature")
        reserve_soc = self._number_value(data.get("auto_prestart_execution_reserve_soc"))

        add_check("scheduler_ready", bool(data.get("scheduler_ready")), "Scheduler still has a start-ready plan")
        add_check("selected_slot_match", data.get("scheduler_selected_slot") == slot, f"Selected slot: {data.get('scheduler_selected_slot')}; expected: {slot}")
        add_check("automatic_origin", origin == "automatic_72h_planner", f"Origin: {origin}")
        add_check("prestart_safe", data.get("auto_prestart_safe") is True, "Authoritative pre-start gate safe")
        add_check("safety_handoff_safe", data.get("auto_safety_handoff_safe") is True, "Safety Guard handoff safe")
        add_check("execution_handoff_ready", data.get("auto_execution_handoff_ready") is True, "Execution handoff ready")
        add_check("planner_identity_match", data.get("auto_prestart_current_identity_match") is True and planner_identity == data.get("auto_execution_handoff_planner_identity"), "Planner identity unchanged")
        add_check("planner_signature_match", data.get("auto_prestart_current_signature_match") is True, "Planner revision unchanged", warning_only=True)
        add_check("forecast_ready", data.get("forecast_ready") is True, "Forecast sources ready")
        add_check("execution_buffer_safe", data.get("auto_plan_72h_execution_buffer_safe") is True, "Execution buffer safe")
        add_check("control_path_configured", bool(data.get("control_path_configured")), "Control path configured")
        add_check("controller_idle", not bool(data.get("execution_active")), "Execution Controller idle")
        add_check("physical_test_idle", not bool(data.get("physical_test_active")), "Physical test idle")
        add_check("action_valid", action in {"laden", "ontladen"}, f"Action: {action}")

        max_power = int(data.get("max_discharge_power_w") or 800) if action == "ontladen" else int(data.get("max_charge_power_w") or 800)
        add_check("power_valid", power_w is not None and 100 <= power_w <= max_power, f"Power: {power_w} W; allowed 100-{max_power} W")
        add_check("soc_valid", soc is not None and 0 <= soc <= 100, f"Current SOC: {soc}%")
        add_check("target_soc_valid", target_soc is not None and 5 <= target_soc <= 100, f"Target SOC: {target_soc}%")

        direction_ok = False
        if soc is not None and target_soc is not None:
            if action == "laden":
                direction_ok = soc < target_soc
            elif action == "ontladen":
                direction_ok = soc > target_soc
        add_check("target_direction_valid", direction_ok, "Current SOC still requires the planned action")

        reserve_ok = True
        if action == "ontladen":
            reserve_ok = soc is not None and reserve_soc is not None and soc > reserve_soc
        add_check("execution_reserve_available", reserve_ok, f"Execution reserve: {reserve_soc}%")

        conflicting_power = (
            charge_power is not None
            and discharge_power is not None
            and charge_power > 100
            and discharge_power > 100
        )
        add_check("no_conflicting_battery_power", not conflicting_power, f"Charge: {charge_power} W; discharge: {discharge_power} W")

        if data.get("operating_mode") != _EXTERNAL_MODE:
            warnings.append("external_mode_switch_required")
            checks.append({
                "check": "external_mode_ready",
                "passed": False,
                "severity": "warning",
                "detail": "Battery is not yet in third_party_control; future Execution Controller must switch mode after this gate",
            })
        else:
            checks.append({
                "check": "external_mode_ready",
                "passed": True,
                "severity": "ok",
                "detail": "Battery already in third_party_control",
            })

        safe = not reasons
        return {
            **base,
            "auto_final_revalidation_required": True,
            "auto_final_revalidation_safe": safe,
            "auto_final_revalidation_status": "ready_observe" if safe else "blocked",
            "auto_final_revalidation_reason": (
                "Finale live revalidatie akkoord; toekomstige mode-switch mag pas in een latere release worden vrijgegeven"
                if safe
                else ", ".join(reasons)
            ),
            "auto_final_revalidation_reasons": reasons,
            "auto_final_revalidation_warnings": warnings,
            "auto_final_revalidation_checks": checks,
            "auto_final_revalidation_selected_slot": slot,
            "auto_final_revalidation_planner_identity": planner_identity,
            "auto_final_revalidation_planner_signature": planner_signature,
            "auto_final_revalidation_checked_at": dt_util.now().isoformat(),
            "auto_final_revalidation_action": action,
            "auto_final_revalidation_power_w": int(power_w) if power_w is not None else None,
            "auto_final_revalidation_target_soc": target_soc,
            "auto_final_revalidation_current_soc": soc,
            "auto_final_revalidation_execution_reserve_soc": reserve_soc,
            "auto_final_revalidation_control_path_configured": bool(data.get("control_path_configured")),
            "auto_final_revalidation_controller_idle": not bool(data.get("execution_active")),
            "auto_final_revalidation_physical_test_idle": not bool(data.get("physical_test_active")),
            "auto_final_revalidation_mode_switch_required": data.get("operating_mode") != _EXTERNAL_MODE,
            "auto_final_revalidation_execution_permitted": False,
            "auto_final_revalidation_physical_control": False,
        }

    @staticmethod
    def _number_value(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_execute_selected_plan(self) -> None:
        if self._coordinator is None:
            raise HomeAssistantError("Dummy OS EMS coordinator is niet beschikbaar")
        if self._state.get("active"):
            raise HomeAssistantError("Er is al een EMS-uitvoering actief")
        if self._coordinator.physical_test.data.get("active"):
            raise HomeAssistantError("Er is nog een fysieke test actief")

        await self._coordinator.async_refresh()
        data = self._coordinator.data
        if not data.get("simulation_mode"):
            raise HomeAssistantError(
                "Alpha 12 verwacht dat de normale automatische planner nog in simulation staat"
            )
        if not data.get("scheduler_ready"):
            raise HomeAssistantError("Scheduler heeft geen startklaar plan")

        slot = data.get("scheduler_selected_slot")
        slots = data.get("scheduler_slots", {}) or {}
        detail = slots.get(slot) or slots.get(str(slot)) or {}
        action = detail.get("action")
        power_w = int(float(detail.get("power_w") or 0))
        target_soc = float(detail.get("target_soc") or 0)
        max_runtime_h = float(detail.get("max_runtime_h") or 0)
        soc = data.get("soc")

        if action not in {"laden", "ontladen"}:
            raise HomeAssistantError("Geselecteerd plan bevat geen ondersteunde batterijactie")
        max_power_w = int(data.get("max_discharge_power_w") or 800) if action == "ontladen" else int(data.get("max_charge_power_w") or 800)
        if not 100 <= power_w <= max_power_w:
            raise HomeAssistantError(
                f"Planvermogen valt buiten 100-{max_power_w} W voor {action}"
            )
        if not 5 <= target_soc <= 100:
            raise HomeAssistantError("Doel-SOC valt buiten 5-100%")
        if not 0.25 <= max_runtime_h <= 12:
            raise HomeAssistantError("Maximale looptijd valt buiten 0,25-12 uur")
        if soc is None:
            raise HomeAssistantError("SOC is niet beschikbaar")
        try:
            soc_value = float(soc)
        except (TypeError, ValueError) as err:
            raise HomeAssistantError("SOC is ongeldig") from err
        if action == "laden":
            if soc_value >= target_soc:
                raise HomeAssistantError("Laaddoel-SOC is al bereikt")
            if (data.get("discharge_power_w") or 0) > 100:
                raise HomeAssistantError("Batterij ontlaadt momenteel; laden wordt niet gestart")
        else:
            if soc_value <= 5:
                raise HomeAssistantError("Minimale SOC van 5% is bereikt")
            if soc_value <= target_soc:
                raise HomeAssistantError("Ontlaaddoel-SOC is al bereikt")
            if (data.get("charge_power_w") or 0) > 100:
                raise HomeAssistantError("Batterij laadt momenteel; ontladen wordt niet gestart")

        mode_entity, direction_entity, power_entity = self._entity_ids()
        now = dt_util.now()
        stop_at = now + timedelta(hours=max_runtime_h)
        self._state.update(
            {
                "active": True,
                "status": "arming_external_mode",
                "reason": "Externe modus wordt automatisch geactiveerd",
                "slot": slot,
                "action": action,
                "power_w": power_w,
                "target_soc": target_soc,
                "max_runtime_h": max_runtime_h,
                "started_at": now.isoformat(),
                "stop_at": stop_at.isoformat(),
                "last_result": None,
            }
        )
        await self._async_save()
        await self._coordinator.async_refresh()

        try:
            if data.get("operating_mode") != _EXTERNAL_MODE:
                await self.hass.services.async_call(
                    "select",
                    "select_option",
                    {"option": _EXTERNAL_MODE},
                    target={"entity_id": mode_entity},
                    blocking=True,
                )
            await self._wait_for_external_controls()

            # Re-evaluate the full safety/controller chain after the mode switch.
            await self._coordinator.async_refresh()
            armed = self._coordinator.data
            if not armed.get("safety_safe"):
                raise HomeAssistantError(
                    f"Safety Guard blokkeert uitvoering: {armed.get('safety_reason') or 'onbekende reden'}"
                )
            if not armed.get("controller_ready"):
                raise HomeAssistantError(
                    f"Action Controller niet gereed: {armed.get('controller_reason') or 'onbekende reden'}"
                )
            if armed.get("controller_action") != action:
                raise HomeAssistantError("Geselecteerde actie wijzigde tijdens het inschakelen")

            self._state.update(
                {
                    "status": "starting",
                    "reason": f"Plan {slot} wordt gestart: {power_w} W {action} tot {target_soc:.0f}%",
                }
            )
            await self._async_save()
            await self._coordinator.async_refresh()

            await self.hass.services.async_call(
                "select",
                "select_option",
                {"option": "charge" if action == "laden" else "discharge"},
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
            _LOGGER.exception("Failed to start Dummy OS EMS execution")
            await self.async_stop(f"start_failed: {err}", emergency=True)
            raise HomeAssistantError(f"EMS-uitvoering starten mislukt: {err}") from err

        self._state.update(
            {
                "status": "running",
                "reason": f"Plan {slot} actief: {action} met {power_w} W tot {target_soc:.0f}% of max {max_runtime_h:g} uur",
            }
        )
        await self._async_save()
        # The plan lifecycle is separate from the execution controller state.
        # Mark it active only after the physical command has been accepted, so
        # the scheduler can no longer select it a second time while it runs.
        await self._coordinator.plan_store.async_mark_lifecycle(
            int(slot), "actief", "execution_running"
        )
        self._schedule_stop(stop_at)
        self._schedule_monitor()
        await self._coordinator.async_refresh()

    def _schedule_stop(self, stop_at: datetime) -> None:
        if self._stop_task is not None and not self._stop_task.done():
            self._stop_task.cancel()
        self._stop_task = self.hass.async_create_task(
            self._async_auto_stop_at(stop_at),
            "Dummy OS EMS execution max-runtime stop",
        )

    async def _async_auto_stop_at(self, stop_at: datetime) -> None:
        try:
            delay = max(0.0, (stop_at - dt_util.now()).total_seconds())
            await asyncio.sleep(delay)
            if self._state.get("active"):
                await self.async_stop("max_runtime_reached", emergency=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Automatic EMS execution stop failed")
            self._state.update(
                {
                    "status": "stop_error",
                    "reason": "Automatische safe-stop kon niet worden uitgevoerd",
                    "last_result": "stop_error",
                }
            )
            await self._async_save()
            if self._coordinator is not None:
                await self._coordinator.async_refresh()

    def _schedule_monitor(self) -> None:
        if self._cancel_monitor is not None:
            self._cancel_monitor()
        self._cancel_monitor = async_call_later(
            self.hass,
            _MONITOR_INTERVAL_SECONDS,
            lambda _now: self.hass.async_create_task(self._async_monitor_once()),
        )

    async def _async_monitor_once(self) -> None:
        if not self._state.get("active") or self._coordinator is None:
            return
        await self._coordinator.async_refresh()
        data = self._coordinator.data

        if data.get("operating_mode") != _EXTERNAL_MODE:
            await self.async_stop("operating_mode_changed", emergency=True)
            return

        action = self._state.get("action")
        expected_direction = "charge" if action == "laden" else "discharge"
        if data.get("action_direction") != expected_direction:
            await self.async_stop("direction_changed", emergency=True)
            return
        if data.get("power_setpoint_w") is None:
            await self.async_stop("power_setpoint_unavailable", emergency=True)
            return
        if action == "laden" and (data.get("discharge_power_w") or 0) > 100:
            await self.async_stop("unexpected_discharge_detected", emergency=True)
            return
        if action == "ontladen" and (data.get("charge_power_w") or 0) > 100:
            await self.async_stop("unexpected_charge_detected", emergency=True)
            return

        # Reaching the planned target is a normal completion condition.
        soc = data.get("soc")
        target_soc = self._state.get("target_soc")
        if soc is None:
            await self.async_stop("soc_unavailable", emergency=True)
            return
        try:
            soc_value = float(soc)
        except (TypeError, ValueError):
            await self.async_stop("invalid_soc", emergency=True)
            return
        if not 0 <= soc_value <= 100:
            await self.async_stop("invalid_soc", emergency=True)
            return
        if data.get("device_status") is None:
            await self.async_stop("device_status_unavailable", emergency=True)
            return
        if data.get("charge_power_w") is None or data.get("discharge_power_w") is None:
            await self.async_stop("battery_power_source_unavailable", emergency=True)
            return
        if action == "laden" and target_soc is not None and soc_value >= float(target_soc):
            await self.async_stop("target_soc_reached", emergency=False)
            return
        if action == "ontladen":
            if soc_value <= 5:
                await self.async_stop("minimum_soc_reached", emergency=False)
                return
            if target_soc is not None and soc_value <= float(target_soc):
                await self.async_stop("target_soc_reached", emergency=False)
                return

        # Do not reuse the pre-start Safety Guard while a plan is active.
        # The Safety Guard intentionally requires a scheduler-selected
        # start-ready plan; an active lifecycle plan is deliberately removed
        # from scheduler selection to prevent duplicate execution. Runtime
        # safety is therefore enforced here directly against the live sources.
        if self.remaining_seconds == 0:
            await self.async_stop("max_runtime_reached", emergency=False)
            return

        self._schedule_monitor()

    async def async_stop(self, reason: str, *, emergency: bool = False) -> None:
        async with self._stop_lock:
            slot = self._state.get("slot")
            if not self._state.get("active") and self._state.get("status") not in {
                "arming_external_mode",
                "starting",
                "running",
                "stopping",
            }:
                return

            current_task = asyncio.current_task()
            if (
                self._stop_task is not None
                and self._stop_task is not current_task
                and not self._stop_task.done()
            ):
                self._stop_task.cancel()
            if self._stop_task is not current_task:
                self._stop_task = None
            if self._cancel_monitor is not None:
                self._cancel_monitor()
                self._cancel_monitor = None

            self._state.update(
                {"status": "stopping", "reason": f"Safe-stop actief: {reason}"}
            )
            await self._async_save()
            if self._coordinator is not None:
                await self._coordinator.async_refresh()

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

            await asyncio.sleep(1)
            if mode_entity:
                try:
                    await self.hass.services.async_call(
                        "select",
                        "select_option",
                        {"option": _SELF_MODE},
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

            if self._coordinator is not None and slot is not None:
                if result == "completed":
                    lifecycle = "geannuleerd" if reason == "manual_stop" else "voltooid"
                else:
                    lifecycle = "fout"
                await self._coordinator.plan_store.async_mark_lifecycle(
                    int(slot), lifecycle, reason
                )

            if self._coordinator is not None:
                await self._coordinator.async_refresh()
            if self._stop_task is current_task:
                self._stop_task = None

    async def async_shutdown_stop(self) -> None:
        if self._state.get("active"):
            try:
                await self.async_stop("home_assistant_stop", emergency=True)
            except Exception:
                _LOGGER.exception("Could not stop EMS execution during Home Assistant shutdown")
