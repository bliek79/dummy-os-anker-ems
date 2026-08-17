from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import AnkerEmsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnkerEmsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AnkerEmsSourcesAvailable(coordinator, entry),
            AnkerEmsControlAvailable(coordinator, entry),
        ]
    )


class _AnkerEmsBinarySensorBase(
    CoordinatorEntity[AnkerEmsCoordinator],
    BinarySensorEntity,
):
    def __init__(self, coordinator: AnkerEmsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Dummy OS",
            model="EMS",
        )


class AnkerEmsSourcesAvailable(_AnkerEmsBinarySensorBase):
    _attr_name = "Dummy OS EMS Bronnen beschikbaar"

    def __init__(self, coordinator: AnkerEmsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sources_available"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data

        required_observation_sources = (
            data.get("soc"),
            data.get("device_status"),
            data.get("charge_power_w"),
            data.get("discharge_power_w"),
            data.get("operating_mode"),
        )

        return all(value is not None for value in required_observation_sources)


class AnkerEmsControlAvailable(_AnkerEmsBinarySensorBase):
    _attr_name = "Dummy OS EMS Besturing beschikbaar"

    def __init__(self, coordinator: AnkerEmsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_control_available"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data

        required_control_sources = (
            data.get("operating_mode"),
            data.get("action_direction"),
            data.get("power_setpoint_w"),
        )

        return all(value is not None for value in required_control_sources)
