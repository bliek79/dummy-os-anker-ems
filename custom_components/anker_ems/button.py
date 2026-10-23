"""Reset button for a finished EMS emergency (without rearming the battery)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import AnkerEmsCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnkerEmsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AnkerEmsEmergencyStatusReset(coordinator, entry)])


class AnkerEmsEmergencyStatusReset(
    CoordinatorEntity[AnkerEmsCoordinator], ButtonEntity,
):
    """Reset current emergency state only after safety validation."""

    _attr_name = "Dummy OS EMS Noodstop bevestigen"
    _attr_has_entity_name = False
    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator: AnkerEmsCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_execution_emergency_reset"
        self._attr_suggested_object_id = "dummy_os_ems_noodstop_bevestigen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Dummy OS",
            model="EMS",
        )

    async def async_press(self) -> None:
        await self.coordinator.execution.async_reset_emergency_status()
