from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    NAME,
    CONF_SIMULATION_MODE,
    CONF_SOC_ENTITY,
    CONF_DEVICE_STATUS_ENTITY,
    CONF_CHARGE_POWER_ENTITY,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_GRID_IMPORT_POWER_ENTITY,
    CONF_GRID_EXPORT_POWER_ENTITY,
    CONF_OPERATING_MODE_ENTITY,
    CONF_ACTION_DIRECTION_ENTITY,
    CONF_POWER_SETPOINT_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


class AnkerEmsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            update_interval=timedelta(seconds=10),
            config_entry=entry,
        )
        self.entry = entry

    @property
    def simulation_mode(self) -> bool:
        return bool(self.entry.data.get(CONF_SIMULATION_MODE, True))

    def _state(self, key: str) -> Any:
        entity_id = self.entry.data.get(key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return None if state is None else state.state

    def _number(self, key: str) -> float | None:
        raw = self._state(key)
        if raw in (None, "unknown", "unavailable", "none", ""):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def _async_update_data(self) -> dict[str, Any]:
        return {
            "simulation_mode": self.simulation_mode,
            "soc": self._number(CONF_SOC_ENTITY),
            "device_status": self._state(CONF_DEVICE_STATUS_ENTITY),
            "charge_power_w": self._number(CONF_CHARGE_POWER_ENTITY),
            "discharge_power_w": self._number(CONF_DISCHARGE_POWER_ENTITY),
            "grid_import_power_w": self._number(CONF_GRID_IMPORT_POWER_ENTITY),
            "grid_export_power_w": self._number(CONF_GRID_EXPORT_POWER_ENTITY),
            "operating_mode": self._state(CONF_OPERATING_MODE_ENTITY),
            "action_direction": self._state(CONF_ACTION_DIRECTION_ENTITY),
            "power_setpoint_w": self._number(CONF_POWER_SETPOINT_ENTITY),
        }
