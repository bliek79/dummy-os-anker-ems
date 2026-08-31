from __future__ import annotations

import asyncio
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_START_CHARGE_TEST,
    SERVICE_START_DISCHARGE_TEST,
    SERVICE_STOP_PHYSICAL_TEST,
    SERVICE_EXECUTE_SELECTED_PLAN,
    SERVICE_STOP_EXECUTION,
    SERVICE_SCHEDULE_PLAN,
    SERVICE_START_PLAN_NOW,
    SERVICE_CANCEL_PLAN,
    SERVICE_STOP_ALL,
    TEST_DEFAULT_DURATION_S,
    TEST_DEFAULT_POWER_W,
    TEST_MAX_DURATION_S,
    TEST_MAX_POWER_W,
    TEST_MIN_DURATION_S,
    TEST_MIN_POWER_W,
    CONF_ELECTRICAL_PROFILE,
    CONF_MAX_CHARGE_POWER_W,
    CONF_MAX_DISCHARGE_POWER_W,
    DEFAULT_ELECTRICAL_PROFILE,
    DEFAULT_SHARED_MAX_POWER_W,
)
from .coordinator import AnkerEmsCoordinator
from .plan_store import AnkerEmsPlanStore
from .scheduler import AnkerEmsScheduler
from .safety_guard import AnkerEmsSafetyGuard
from .action_controller import AnkerEmsActionController
from .physical_test import AnkerEmsPhysicalTestController
from .execution import AnkerEmsExecutionController
from .source_monitor import AnkerEmsSourceMonitor
from .entity_naming import async_migrate_entity_ids

_LOGGER = logging.getLogger(__name__)
_SCHEDULED_RETRY_SECONDS = 10

# Dummy OS EMS is configured exclusively through Config Flow.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate older Dummy OS EMS config entries to the current schema.

    Version 2 adds the central electrical profile and charge/discharge power
    limits. Existing installations fail safe to the shared-group profile at
    800 W until the user explicitly confirms different limits in Options Flow.
    All pre-existing config-entry data is preserved.
    """
    if config_entry.version > 2:
        _LOGGER.error(
            "Cannot migrate Dummy OS EMS config entry from future version %s",
            config_entry.version,
        )
        return False

    if config_entry.version == 1:
        new_data = dict(config_entry.data)
        new_data.setdefault(CONF_ELECTRICAL_PROFILE, DEFAULT_ELECTRICAL_PROFILE)
        new_data.setdefault(CONF_MAX_CHARGE_POWER_W, DEFAULT_SHARED_MAX_POWER_W)
        new_data.setdefault(CONF_MAX_DISCHARGE_POWER_W, DEFAULT_SHARED_MAX_POWER_W)

        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=2,
        )
        _LOGGER.info(
            "Migrated Dummy OS EMS config entry from version 1 to 2 with safe 800 W defaults"
        )

    return True


def _single_coordinator(hass: HomeAssistant) -> AnkerEmsCoordinator:
    entries = hass.data.get(DOMAIN, {})
    if len(entries) != 1:
        raise HomeAssistantError(
            "De fysieke test vereist precies één geladen Dummy OS EMS config-entry"
        )
    return next(iter(entries.values()))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async def _start_charge_test(call: ServiceCall) -> None:
        if call.data.get("confirm") is not True:
            raise HomeAssistantError("Bevestiging ontbreekt: zet confirm op true")
        coordinator = _single_coordinator(hass)
        await coordinator.physical_test.async_start_charge_test(
            power_w=int(call.data.get("power_w", TEST_DEFAULT_POWER_W)),
            duration_s=int(call.data.get("duration_s", TEST_DEFAULT_DURATION_S)),
        )

    async def _start_discharge_test(call: ServiceCall) -> None:
        if call.data.get("confirm") is not True:
            raise HomeAssistantError("Bevestiging ontbreekt: zet confirm op true")
        coordinator = _single_coordinator(hass)
        await coordinator.physical_test.async_start_discharge_test(
            power_w=int(call.data.get("power_w", TEST_DEFAULT_POWER_W)),
            duration_s=int(call.data.get("duration_s", TEST_DEFAULT_DURATION_S)),
        )

    async def _stop_physical_test(call: ServiceCall) -> None:
        coordinator = _single_coordinator(hass)
        await coordinator.physical_test.async_stop("manual_stop", emergency=False)

    async def _execute_selected_plan(call: ServiceCall) -> None:
        if call.data.get("confirm") is not True:
            raise HomeAssistantError("Bevestiging ontbreekt: zet confirm op true")
        coordinator = _single_coordinator(hass)
        await coordinator.execution.async_execute_selected_plan()

    async def _stop_execution(call: ServiceCall) -> None:
        coordinator = _single_coordinator(hass)
        await coordinator.execution.async_stop("manual_stop", emergency=False)


    def _slot_from_call(call: ServiceCall) -> int:
        slot = int(call.data.get("slot", 0))
        if slot not in {1, 2, 3}:
            raise HomeAssistantError("Planplaats moet 1, 2 of 3 zijn")
        return slot

    async def _schedule_plan(call: ServiceCall) -> None:
        coordinator = _single_coordinator(hass)
        slot = _slot_from_call(call)
        current = coordinator.plan_store.get_plan(slot)
        if current.get("action") == "geen":
            raise HomeAssistantError(f"Plan {slot} heeft nog geen actie")
        start_raw = current.get("start_time")
        start = dt_util.parse_datetime(str(start_raw)) if start_raw else None
        if start is None:
            raise HomeAssistantError(f"Plan {slot} heeft geen geldige starttijd")
        if start.tzinfo is None:
            start = start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if start <= dt_util.now():
            raise HomeAssistantError(f"Plan {slot} starttijd moet in de toekomst liggen")
        await coordinator.plan_store.async_set_value(slot, "execution_mode", "gepland")
        await coordinator.plan_store.async_mark_lifecycle(slot, "pending", "scheduled_by_user")
        await coordinator.async_refresh()

    async def _start_plan_now(call: ServiceCall) -> None:
        if call.data.get("confirm") is not True:
            raise HomeAssistantError("Bevestiging ontbreekt: zet confirm op true")
        coordinator = _single_coordinator(hass)
        slot = _slot_from_call(call)
        current = coordinator.plan_store.get_plan(slot)
        if current.get("action") == "geen":
            raise HomeAssistantError(f"Plan {slot} heeft nog geen actie")
        await coordinator.plan_store.async_set_value(slot, "execution_mode", "direct")
        await coordinator.plan_store.async_mark_lifecycle(slot, "pending", "start_now_by_user")
        await coordinator.async_refresh()
        data = coordinator.data
        if data.get("scheduler_selected_slot") != slot or not data.get("scheduler_ready"):
            raise HomeAssistantError(f"Plan {slot} is niet startklaar")
        await coordinator.execution.async_execute_selected_plan()

    async def _cancel_plan(call: ServiceCall) -> None:
        coordinator = _single_coordinator(hass)
        slot = _slot_from_call(call)
        execution = coordinator.execution.data
        if execution.get("active") and int(execution.get("slot") or 0) == slot:
            await coordinator.execution.async_stop("manual_stop", emergency=False)
            return
        await coordinator.plan_store.async_mark_lifecycle(slot, "geannuleerd", "manual_cancel")
        await coordinator.async_refresh()

    async def _stop_all(call: ServiceCall) -> None:
        coordinator = _single_coordinator(hass)
        errors: list[str] = []
        if coordinator.physical_test.data.get("active"):
            try:
                await coordinator.physical_test.async_stop("manual_stop", emergency=False)
            except Exception as err:
                errors.append(f"physical_test: {err}")
        if coordinator.execution.data.get("active"):
            try:
                await coordinator.execution.async_stop("manual_stop", emergency=False)
            except Exception as err:
                errors.append(f"execution: {err}")

        # Extra safe-return path for an externally controlled battery even when
        # no controller object currently considers itself active.
        ids = coordinator.control_entity_ids
        power_entity = ids.get("power_setpoint")
        mode_entity = ids.get("operating_mode")
        if power_entity:
            state = hass.states.get(power_entity)
            if state is not None and state.state not in {"unknown", "unavailable"}:
                try:
                    await hass.services.async_call(
                        "number", "set_value", {"value": 0},
                        target={"entity_id": power_entity}, blocking=True
                    )
                except Exception as err:
                    errors.append(f"power_zero: {err}")
        if mode_entity:
            state = hass.states.get(mode_entity)
            if state is not None and state.state not in {"unknown", "unavailable", "self_consumption"}:
                try:
                    await hass.services.async_call(
                        "select", "select_option", {"option": "self_consumption"},
                        target={"entity_id": mode_entity}, blocking=True
                    )
                except Exception as err:
                    errors.append(f"self_consumption: {err}")
        await coordinator.async_refresh()
        if errors:
            raise HomeAssistantError("Alles stoppen deels mislukt: " + "; ".join(errors))

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_CHARGE_TEST,
        _start_charge_test,
        schema=vol.Schema(
            {
                vol.Required("confirm"): bool,
                vol.Optional("power_w", default=TEST_DEFAULT_POWER_W): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=TEST_MIN_POWER_W, max=TEST_MAX_POWER_W),
                ),
                vol.Optional("duration_s", default=TEST_DEFAULT_DURATION_S): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=TEST_MIN_DURATION_S, max=TEST_MAX_DURATION_S),
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_DISCHARGE_TEST,
        _start_discharge_test,
        schema=vol.Schema(
            {
                vol.Required("confirm"): bool,
                vol.Optional("power_w", default=TEST_DEFAULT_POWER_W): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=TEST_MIN_POWER_W, max=TEST_MAX_POWER_W),
                ),
                vol.Optional("duration_s", default=TEST_DEFAULT_DURATION_S): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=TEST_MIN_DURATION_S, max=TEST_MAX_DURATION_S),
                ),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_PHYSICAL_TEST,
        _stop_physical_test,
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXECUTE_SELECTED_PLAN,
        _execute_selected_plan,
        schema=vol.Schema({vol.Required("confirm"): bool}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_EXECUTION,
        _stop_execution,
        schema=vol.Schema({}),
    )

    plan_slot_schema = vol.All(vol.Coerce(int), vol.Range(min=1, max=3))
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_PLAN,
        _schedule_plan,
        schema=vol.Schema({vol.Required("slot"): plan_slot_schema}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_PLAN_NOW,
        _start_plan_now,
        schema=vol.Schema(
            {
                vol.Required("slot"): plan_slot_schema,
                vol.Required("confirm"): bool,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_PLAN,
        _cancel_plan,
        schema=vol.Schema({vol.Required("slot"): plan_slot_schema}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_ALL,
        _stop_all,
        schema=vol.Schema({}),
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    plan_store = AnkerEmsPlanStore(hass, entry.entry_id)
    await plan_store.async_load()

    scheduler = AnkerEmsScheduler(plan_store)
    safety_guard = AnkerEmsSafetyGuard()
    action_controller = AnkerEmsActionController()
    physical_test = AnkerEmsPhysicalTestController(hass, entry.entry_id)
    await physical_test.async_load()
    execution = AnkerEmsExecutionController(hass, entry.entry_id)
    await execution.async_load()
    source_monitor = AnkerEmsSourceMonitor(hass, entry.entry_id)
    await source_monitor.async_load()

    coordinator = AnkerEmsCoordinator(
        hass,
        entry,
        plan_store,
        scheduler,
        safety_guard,
        action_controller,
        physical_test,
        execution,
        source_monitor,
    )
    physical_test.attach_coordinator(coordinator)
    execution.attach_coordinator(coordinator)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # If Home Assistant restarted during a physical test, immediately attempt a
    # safe stop before exposing the integration as fully loaded.
    await physical_test.async_recover_if_needed()
    await execution.async_recover_if_needed()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    def _plan_changed() -> None:
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(plan_store.add_listener(_plan_changed))

    # Alpha 19: user-scheduled charge and discharge plans are handed from the
    # Scheduler to the validated Execution Controller as soon as they become
    # start-ready.
    # That controller performs the safe sequence:
    # self_consumption -> third_party_control -> wait for controls -> recheck
    # safety -> execute -> safe stop.
    #
    # Direct plans remain explicit via start_plan_now. Both physical charge
    # and physical discharge paths have now been validated separately.
    scheduled_autostart_task = None

    @callback
    def _scheduler_execution_listener() -> None:
        nonlocal scheduled_autostart_task
        data = coordinator.data or {}

        if not data.get("scheduler_ready"):
            return
        if data.get("scheduler_selected_execution_mode") != "gepland":
            return
        if data.get("scheduler_selected_action") not in {"laden", "ontladen"}:
            return
        selected_slot = data.get("scheduler_selected_slot")
        selected_detail = (data.get("scheduler_slots", {}) or {}).get(selected_slot, {}) or {}
        if selected_detail.get("origin") == "automatic_72h_planner":
            # Automatic planner execution is still deliberately disabled.
            # Alpha36 only centralizes configurable power safety limits.
            return
        if execution.data.get("active") or physical_test.data.get("active"):
            return
        if scheduled_autostart_task is not None and not scheduled_autostart_task.done():
            return

        async def _async_start_scheduled_plan() -> None:
            nonlocal scheduled_autostart_task
            slot = data.get("scheduler_selected_slot")
            start_window_end_raw = (
                (data.get("scheduler_slots", {}) or {})
                .get(slot, {})
                .get("start_window_end")
            )
            start_window_end = (
                dt_util.parse_datetime(str(start_window_end_raw))
                if start_window_end_raw
                else None
            )
            if start_window_end is not None and start_window_end.tzinfo is None:
                start_window_end = start_window_end.replace(
                    tzinfo=dt_util.DEFAULT_TIME_ZONE
                )

            retryable_fragments = (
                "Externe modus werd niet tijdig beschikbaar",
                "control_sources_missing",
                "not_in_external_mode",
                "observation_sources_missing",
                "Batterij laadt momenteel; ontladen wordt niet gestart",
                "Batterij ontlaadt momenteel; laden wordt niet gestart",
                "Action Controller niet gereed",
            )

            try:
                while True:
                    try:
                        _LOGGER.info(
                            "Automatically starting scheduled Dummy OS EMS plan %s",
                            slot,
                        )
                        await execution.async_execute_selected_plan()
                        return
                    except HomeAssistantError as err:
                        message = str(err)
                        retryable = any(
                            fragment in message for fragment in retryable_fragments
                        )
                        now = dt_util.now()
                        within_window = (
                            start_window_end is not None and now < start_window_end
                        )

                        if not retryable or not within_window:
                            _LOGGER.warning(
                                "Scheduled Dummy OS EMS plan %s could not start: %s",
                                slot,
                                err,
                            )
                            return

                        # Execution may already have performed its safe-stop and
                        # marked the plan as fout. Re-arm only this scheduled plan
                        # while its user-configured start window is still open.
                        await coordinator.plan_store.async_mark_lifecycle(
                            int(slot),
                            "pending",
                            f"retry_wait: {message}",
                        )
                        await coordinator.async_refresh()

                        remaining = max(
                            0.0,
                            (start_window_end - dt_util.now()).total_seconds(),
                        )
                        delay = min(float(_SCHEDULED_RETRY_SECONDS), remaining)
                        if delay <= 0:
                            return

                        _LOGGER.info(
                            "Retrying scheduled Dummy OS EMS plan %s in %.0f seconds",
                            slot,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        await coordinator.async_refresh()

                        current = coordinator.data or {}
                        if (
                            current.get("scheduler_selected_slot") != slot
                            or not current.get("scheduler_ready")
                            or current.get("scheduler_selected_execution_mode") != "gepland"
                        ):
                            return
                    except Exception:
                        _LOGGER.exception(
                            "Unexpected error while automatically starting scheduled Dummy OS EMS plan %s",
                            slot,
                        )
                        return
            finally:
                scheduled_autostart_task = None

        scheduled_autostart_task = hass.async_create_task(
            _async_start_scheduled_plan(),
            "Dummy OS EMS scheduled plan auto-start",
        )

    entry.async_on_unload(coordinator.async_add_listener(_scheduler_execution_listener))

    # Alpha54: the restored Automatic Execution switch is now the explicit
    # physical arm. The coordinator listener starts exactly one automatic
    # Scheduler-selected planner action only when the complete gate reports
    # execution_permitted. The Execution Controller performs its own fresh
    # identity/safety checks again before and after entering third_party_control.
    automatic_execution_task = None

    @callback
    def _automatic_execution_listener() -> None:
        nonlocal automatic_execution_task
        data = coordinator.data or {}
        if data.get("auto_shadow_execution_permitted") is not True:
            return
        slot = data.get("auto_shadow_selected_slot")
        detail = ((data.get("scheduler_slots", {}) or {}).get(slot) or
                  (data.get("scheduler_slots", {}) or {}).get(str(slot)) or {})
        identity = detail.get("planner_identity")
        if not identity or detail.get("origin") != "automatic_72h_planner":
            return
        execution_data = execution.data
        if execution_data.get("active") or execution_data.get("auto_mode_switch_active"):
            return
        if physical_test.data.get("active"):
            return
        if automatic_execution_task is not None and not automatic_execution_task.done():
            return

        async def _run() -> None:
            nonlocal automatic_execution_task
            try:
                _LOGGER.info("Starting automatic physical EMS execution for %s", identity)
                await execution.async_execute_automatic_plan(identity)
            except HomeAssistantError as err:
                _LOGGER.warning("Automatic physical EMS execution blocked/failed: %s", err)
            except Exception:
                _LOGGER.exception("Unexpected automatic physical EMS execution error")
            finally:
                automatic_execution_task = None

        automatic_execution_task = hass.async_create_task(
            _run(), "Dummy OS EMS automatic physical execution"
        )

    entry.async_on_unload(coordinator.async_add_listener(_automatic_execution_listener))

    @callback
    def _shutdown(_event) -> None:
        hass.async_create_task(physical_test.async_shutdown_stop())
        hass.async_create_task(execution.async_shutdown_stop())

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown))

    # Migrate already-registered entities first, then run the same explicit
    # naming contract once more after platform setup so newly-created entities
    # cannot keep an automatically generated Home Assistant object ID.
    await async_migrate_entity_ids(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_migrate_entity_ids(hass, entry)
    _LOGGER.info(
        "Dummy OS EMS loaded in %s mode",
        "simulation" if coordinator.simulation_mode else "observe",
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: AnkerEmsCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None and coordinator.physical_test.data.get("active"):
        await coordinator.physical_test.async_stop("integration_unload", emergency=True)
    if coordinator is not None and coordinator.execution.data.get("active"):
        await coordinator.execution.async_stop("integration_unload", emergency=True)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
