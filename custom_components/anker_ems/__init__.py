from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_START_CHARGE_TEST,
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
)
from .coordinator import AnkerEmsCoordinator
from .plan_store import AnkerEmsPlanStore
from .scheduler import AnkerEmsScheduler
from .safety_guard import AnkerEmsSafetyGuard
from .action_controller import AnkerEmsActionController
from .physical_test import AnkerEmsPhysicalTestController
from .execution import AnkerEmsExecutionController
from .source_monitor import AnkerEmsSourceMonitor

_LOGGER = logging.getLogger(__name__)


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

    @callback
    def _shutdown(_event) -> None:
        hass.async_create_task(physical_test.async_shutdown_stop())
        hass.async_create_task(execution.async_shutdown_stop())

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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
