from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import AnkerEmsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnkerEmsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AnkerEmsAutomaticExecutionArm(coordinator, entry)])


class AnkerEmsAutomaticExecutionArm(
    CoordinatorEntity[AnkerEmsCoordinator], RestoreEntity, SwitchEntity
):
    """Fail-safe arm switch for future automatic execution.

    Alpha51 is shadow-only: ON means the user has armed the chain for validation,
    but the integration still refuses every automatic non-zero physical command.
    """

    _attr_name = "Dummy OS EMS Automatische uitvoering"
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: AnkerEmsCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_automatic_execution_arm"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Dummy OS",
            model="EMS",
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.auto_execution_armed

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        armed = previous is not None and previous.state == "on"
        await self.coordinator.async_set_auto_execution_armed(armed)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_auto_execution_armed(True)

    async def async_turn_off(self, **kwargs) -> None:
        # Alpha51 has no automatic non-zero execution to stop; OFF therefore
        # immediately closes the future automatic gate without touching manual plans.
        await self.coordinator.async_set_auto_execution_armed(False)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        data = self.coordinator.data or {}
        return {
            "mode": "shadow_only",
            "technical_ready": data.get("auto_shadow_technical_ready", False),
            "shadow_status": data.get("auto_shadow_status"),
            "blockers": data.get("auto_shadow_blockers", []),
            "physical_execution_enabled": False,
        }
