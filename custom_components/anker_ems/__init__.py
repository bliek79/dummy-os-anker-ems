from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_START_CHARGE_TEST,
    SERVICE_STOP_PHYSICAL_TEST,
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

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_CHARGE_TEST,
        _start_charge_test,
        schema=vol.Schema(
            {
                vol.Required("confirm"): bool,
                vol.Optional(
                    "power_w", default=TEST_DEFAULT_POWER_W
                ): vol.All(vol.Coerce(int), vol.Range(min=TEST_MIN_POWER_W, max=TEST_MAX_POWER_W)),
                vol.Optional(
                    "duration_s", default=TEST_DEFAULT_DURATION_S
                ): vol.All(vol.Coerce(int), vol.Range(min=TEST_MIN_DURATION_S, max=TEST_MAX_DURATION_S)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_PHYSICAL_TEST,
        _stop_physical_test,
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

    coordinator = AnkerEmsCoordinator(
        hass,
        entry,
        plan_store,
        scheduler,
        safety_guard,
        action_controller,
        physical_test,
    )
    physical_test.attach_coordinator(coordinator)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # If Home Assistant restarted during a physical test, immediately attempt a
    # safe stop before exposing the integration as fully loaded.
    await physical_test.async_recover_if_needed()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    def _plan_changed() -> None:
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(plan_store.add_listener(_plan_changed))

    @callback
    def _shutdown(_event) -> None:
        hass.async_create_task(physical_test.async_shutdown_stop())

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

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
