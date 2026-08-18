from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import AnkerEmsCoordinator
from .plan_store import AnkerEmsPlanStore
from .scheduler import AnkerEmsScheduler
from .safety_guard import AnkerEmsSafetyGuard
from .action_controller import AnkerEmsActionController

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    plan_store = AnkerEmsPlanStore(hass, entry.entry_id)
    await plan_store.async_load()

    scheduler = AnkerEmsScheduler(plan_store)
    safety_guard = AnkerEmsSafetyGuard()
    action_controller = AnkerEmsActionController()
    coordinator = AnkerEmsCoordinator(
        hass, entry, plan_store, scheduler, safety_guard, action_controller
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    def _plan_changed() -> None:
        hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(plan_store.add_listener(_plan_changed))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(
        "Dummy OS EMS loaded in %s mode",
        "simulation" if coordinator.simulation_mode else "observe",
    )
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
