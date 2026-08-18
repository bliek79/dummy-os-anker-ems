from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, PLAN_SLOT_COUNT
from .coordinator import AnkerEmsCoordinator


@dataclass(frozen=True, kw_only=True)
class AnkerEmsSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _forecast_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "horizon_hours": data.get("forecast_horizon_hours"),
        "price_hours": data.get("forecast_price_hours"),
        "home_hours": data.get("forecast_home_hours"),
        "solar_hours": data.get("forecast_solar_hours"),
        "complete_hours": data.get("forecast_complete_hours"),
        "missing_sources": data.get("forecast_missing_sources", []),
        "sources": data.get("forecast_sources", {}),
        "forecast": data.get("forecast", []),
    }


def _scheduler_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_slot": data.get("scheduler_selected_slot"),
        "selected_action": data.get("scheduler_selected_action"),
        "selected_execution_mode": data.get("scheduler_selected_execution_mode"),
        "selected_start_time": data.get("scheduler_selected_start_time"),
        "next_future_slot": data.get("scheduler_next_future_slot"),
        "next_future_start": data.get("scheduler_next_future_start"),
        "slots": data.get("scheduler_slots", {}),
        "physical_control": data.get("scheduler_physical_control", False),
    }


def _safety_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_slot": data.get("safety_selected_slot"),
        "reason": data.get("safety_reason"),
        "reasons": data.get("safety_reasons", []),
        "warnings": data.get("safety_warnings", []),
        "physical_control": data.get("safety_physical_control", False),
    }




def _physical_test_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "active": data.get("physical_test_active", False),
        "reason": data.get("physical_test_reason"),
        "power_w": data.get("physical_test_power_w"),
        "duration_s": data.get("physical_test_duration_s"),
        "remaining_s": data.get("physical_test_remaining_s"),
        "started_at": data.get("physical_test_started_at"),
        "stop_at": data.get("physical_test_stop_at"),
        "last_result": data.get("physical_test_last_result"),
        "test_limits": {"max_power_w": 500, "max_duration_s": 120, "charge_only": True},
    }

def _controller_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_slot": data.get("controller_selected_slot"),
        "action": data.get("controller_action"),
        "power_w": data.get("controller_power_w"),
        "target_soc": data.get("controller_target_soc"),
        "max_runtime_h": data.get("controller_max_runtime_h"),
        "execution_mode": data.get("controller_execution_mode"),
        "reason": data.get("controller_reason"),
        "desired_mode": data.get("controller_desired_mode"),
        "desired_direction": data.get("controller_desired_direction"),
        "desired_power_w": data.get("controller_desired_power_w"),
        "physical_control": data.get("controller_physical_control", False),
    }


SENSORS: tuple[AnkerEmsSensorDescription, ...] = (
    AnkerEmsSensorDescription(
        key="status",
        name="Dummy OS EMS Status",
        value_fn=lambda d: "simulation" if d.get("simulation_mode") else "observe",
    ),
    AnkerEmsSensorDescription(
        key="soc",
        name="Dummy OS EMS SOC",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("soc"),
    ),
    AnkerEmsSensorDescription(
        key="charge_power",
        name="Dummy OS EMS Laadvermogen",
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: d.get("charge_power_w"),
    ),
    AnkerEmsSensorDescription(
        key="discharge_power",
        name="Dummy OS EMS Ontlaadvermogen",
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: d.get("discharge_power_w"),
    ),
    AnkerEmsSensorDescription(
        key="operating_mode",
        name="Dummy OS EMS Bedrijfsmodus",
        value_fn=lambda d: d.get("operating_mode"),
    ),
    AnkerEmsSensorDescription(
        key="forecast_status",
        name="Dummy OS EMS Forecast status",
        value_fn=lambda d: d.get("forecast_status"),
        attrs_fn=_forecast_attrs,
    ),
    AnkerEmsSensorDescription(
        key="forecast_complete_hours",
        name="Dummy OS EMS Forecast complete uren",
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("forecast_complete_hours"),
    ),
    AnkerEmsSensorDescription(
        key="scheduler_status",
        name="Dummy OS EMS Scheduler status",
        value_fn=lambda d: d.get("scheduler_status"),
        attrs_fn=_scheduler_attrs,
    ),
    AnkerEmsSensorDescription(
        key="scheduler_selected_plan",
        name="Dummy OS EMS Scheduler geselecteerd plan",
        value_fn=lambda d: (
            f"plan_{d.get('scheduler_selected_slot')}"
            if d.get("scheduler_selected_slot") is not None
            else "geen"
        ),
        attrs_fn=_scheduler_attrs,
    ),
    AnkerEmsSensorDescription(
        key="safety_status",
        name="Dummy OS EMS Safety Guard status",
        value_fn=lambda d: d.get("safety_status"),
        attrs_fn=_safety_attrs,
    ),
    AnkerEmsSensorDescription(
        key="safety_reason",
        name="Dummy OS EMS Safety Guard reden",
        value_fn=lambda d: d.get("safety_reason"),
        attrs_fn=_safety_attrs,
    ),
    AnkerEmsSensorDescription(
        key="controller_status",
        name="Dummy OS EMS Action Controller status",
        value_fn=lambda d: d.get("controller_status"),
        attrs_fn=_controller_attrs,
    ),
    AnkerEmsSensorDescription(
        key="controller_action",
        name="Dummy OS EMS Action Controller actie",
        value_fn=lambda d: d.get("controller_action") or "geen",
        attrs_fn=_controller_attrs,
    ),
    AnkerEmsSensorDescription(
        key="physical_test_status",
        name="Dummy OS EMS Fysieke test status",
        value_fn=lambda d: d.get("physical_test_status") or "idle",
        attrs_fn=_physical_test_attrs,
    ),
    AnkerEmsSensorDescription(
        key="physical_test_remaining",
        name="Dummy OS EMS Fysieke test resterend",
        native_unit_of_measurement="s",
        value_fn=lambda d: d.get("physical_test_remaining_s"),
        attrs_fn=_physical_test_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AnkerEmsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AnkerEmsSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.extend(
        AnkerEmsPlanStatusSensor(coordinator, entry, slot)
        for slot in range(1, PLAN_SLOT_COUNT + 1)
    )
    async_add_entities(entities)


class AnkerEmsSensor(CoordinatorEntity[AnkerEmsCoordinator], SensorEntity):
    entity_description: AnkerEmsSensorDescription

    def __init__(
        self,
        coordinator: AnkerEmsCoordinator,
        entry: ConfigEntry,
        description: AnkerEmsSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Dummy OS",
            model="EMS",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


class AnkerEmsPlanStatusSensor(CoordinatorEntity[AnkerEmsCoordinator], SensorEntity):
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: AnkerEmsCoordinator,
        entry: ConfigEntry,
        slot: int,
    ) -> None:
        super().__init__(coordinator)
        self.plan_store = coordinator.plan_store
        self.slot = slot
        self._attr_name = f"Dummy OS EMS Plan {slot} Status"
        self._attr_unique_id = f"{entry.entry_id}_plan_{slot}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Dummy OS",
            model="EMS",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.plan_store.add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> str:
        slots = self.coordinator.data.get("scheduler_slots", {})
        detail = slots.get(self.slot) or slots.get(str(self.slot)) or {}
        return str(detail.get("status") or self.plan_store.plan_status(self.slot))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        plan = self.plan_store.get_plan(self.slot)
        slots = self.coordinator.data.get("scheduler_slots", {})
        scheduler_detail = slots.get(self.slot) or slots.get(str(self.slot)) or {}
        return {
            "slot": self.slot,
            "action": plan.get("action"),
            "execution_mode": plan.get("execution_mode"),
            "start_time": plan.get("start_time"),
            "power_w": plan.get("power_w"),
            "target_soc": plan.get("target_soc"),
            "max_runtime_h": plan.get("max_runtime_h"),
            "max_start_delay_min": plan.get("max_start_delay_min"),
            "persistent": True,
            "scheduler_selected": scheduler_detail.get("selected", False),
            "scheduler_start_window_end": scheduler_detail.get("start_window_end"),
            "physical_control": False,
            "safety_status": self.coordinator.data.get("safety_status"),
            "controller_status": self.coordinator.data.get("controller_status"),
        }
