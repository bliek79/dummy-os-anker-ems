from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
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
        "action": data.get("physical_test_action"),
        "reason": data.get("physical_test_reason"),
        "power_w": data.get("physical_test_power_w"),
        "duration_s": data.get("physical_test_duration_s"),
        "remaining_s": data.get("physical_test_remaining_s"),
        "started_at": data.get("physical_test_started_at"),
        "stop_at": data.get("physical_test_stop_at"),
        "last_result": data.get("physical_test_last_result"),
        "test_limits": {"max_power_w": 500, "max_duration_s": 120, "charge_only": True},
    }



def _execution_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "active": data.get("execution_active", False),
        "reason": data.get("execution_reason"),
        "slot": data.get("execution_slot"),
        "action": data.get("execution_action"),
        "power_w": data.get("execution_power_w"),
        "target_soc": data.get("execution_target_soc"),
        "max_runtime_h": data.get("execution_max_runtime_h"),
        "remaining_s": data.get("execution_remaining_s"),
        "started_at": data.get("execution_started_at"),
        "stop_at": data.get("execution_stop_at"),
        "last_result": data.get("execution_last_result"),
        "automatic_mode_switch": True,
        "discharge_enabled": False,
    }


def _source_monitor_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "sources": data.get("source_monitor_sources", {}),
        "recent_events": data.get("source_monitor_recent_events", []),
        "recalculation_candidates_today": data.get("source_monitor_recalc_candidates_today", 0),
        "last_content_change": data.get("source_monitor_last_content_change"),
        "retention_days": data.get("source_monitor_retention_days", 7),
        "purpose": "observe source timing before event-driven planner activation",
    }


def _energy_need_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": data.get("energy_need_valid", False),
        "reason": data.get("energy_need_reason"),
        "first_usable_solar": data.get("energy_need_first_usable_solar"),
        "need_until_solar_kwh": data.get("energy_need_until_solar_kwh"),
        "available_battery_kwh": data.get("energy_need_available_battery_kwh"),
        "safety_reserve_percent": data.get("energy_need_safety_reserve_percent"),
        "safety_reserve_kwh": data.get("energy_need_safety_reserve_kwh"),
        "required_including_reserve_kwh": data.get("energy_need_required_including_reserve_kwh"),
        "additional_grid_charge_kwh": data.get("energy_need_additional_grid_charge_kwh"),
        "tradable_battery_kwh": data.get("energy_need_tradable_battery_kwh"),
        "contributing_hours": data.get("energy_need_contributing_hours"),
        "battery_capacity_kwh": data.get("energy_need_battery_capacity_kwh"),
        "min_soc_percent": data.get("energy_need_min_soc_percent"),
        "usable_solar_rule": data.get("energy_need_usable_solar_rule"),
        "observational_only": data.get("energy_need_observational_only", True),
    }

def _planner_preview_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": data.get("planner_preview_decision"),
        "reason": data.get("planner_preview_reason"),
        "required_min_soc": data.get("planner_preview_required_min_soc"),
        "energy_above_reserve_kwh": data.get("planner_preview_energy_above_reserve_kwh"),
        "safety_charge_needed": data.get("planner_preview_safety_charge_needed", False),
        "safety_charge_kwh": data.get("planner_preview_safety_charge_kwh"),
        "safety_charge_hours": data.get("planner_preview_safety_charge_hours", []),
        "safety_schedule_sufficient": data.get("planner_preview_safety_schedule_sufficient", False),
        "trade_charge_candidate": data.get("planner_preview_trade_charge_candidate", False),
        "discharge_possible": data.get("planner_preview_discharge_possible", False),
        "solar_charge_delay": data.get("planner_preview_solar_charge_delay", False),
        "first_usable_solar": data.get("planner_preview_first_usable_solar"),
        "price_min": data.get("planner_preview_price_min"),
        "price_max": data.get("planner_preview_price_max"),
        "price_spread": data.get("planner_preview_price_spread"),
        "cheapest_hours": data.get("planner_preview_cheapest_hours", []),
        "free_capacity_kwh": data.get("planner_preview_free_capacity_kwh"),
        "replan_reason": data.get("planner_preview_replan_reason"),
        "observational_only": data.get("planner_preview_observational_only", True),
        "trading_execution_enabled": data.get("planner_preview_trading_execution_enabled", False),
        "losses_included": data.get("planner_preview_losses_included", False),
        "assumed_max_charge_power_w": data.get("planner_preview_assumed_max_charge_power_w"),
        "charge_efficiency_percent": data.get("planner_preview_charge_efficiency_percent"),
        "discharge_efficiency_percent": data.get("planner_preview_discharge_efficiency_percent"),
        "roundtrip_efficiency_percent": data.get("planner_preview_roundtrip_efficiency_percent"),
        "minimum_trade_margin": data.get("planner_preview_minimum_trade_margin"),
        "trade_profitable": data.get("planner_preview_trade_profitable", False),
        "best_charge_time": data.get("planner_preview_best_charge_time"),
        "best_charge_price": data.get("planner_preview_best_charge_price"),
        "best_discharge_time": data.get("planner_preview_best_discharge_time"),
        "best_discharge_price": data.get("planner_preview_best_discharge_price"),
        "effective_charge_cost": data.get("planner_preview_effective_charge_cost"),
        "expected_trade_margin": data.get("planner_preview_expected_trade_margin"),
        "note": data.get("planner_preview_note"),
    }


def _auto_plan_72h_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": data.get("auto_plan_72h_valid", False),
        "reason": data.get("auto_plan_72h_reason"),
        "count": data.get("auto_plan_72h_count"),
        "start": data.get("auto_plan_72h_start"),
        "end": data.get("auto_plan_72h_end"),
        "start_soc": data.get("auto_plan_72h_start_soc"),
        "end_soc": data.get("auto_plan_72h_end_soc"),
        "min_soc": data.get("auto_plan_72h_min_soc"),
        "max_soc": data.get("auto_plan_72h_max_soc"),
        "reserve_floor_soc": data.get("auto_plan_72h_reserve_floor_soc"),
        "dynamic_reserve_min_soc": data.get("auto_plan_72h_dynamic_reserve_min_soc"),
        "dynamic_reserve_max_soc": data.get("auto_plan_72h_dynamic_reserve_max_soc"),
        "solar_charge_kwh": data.get("auto_plan_72h_solar_charge_kwh"),
        "grid_safety_charge_kwh": data.get("auto_plan_72h_grid_safety_charge_kwh"),
        "grid_trade_charge_kwh": data.get("auto_plan_72h_grid_trade_charge_kwh"),
        "home_discharge_kwh": data.get("auto_plan_72h_home_discharge_kwh"),
        "grid_trade_discharge_kwh": data.get("auto_plan_72h_grid_trade_discharge_kwh"),
        "grid_import_for_home_kwh": data.get("auto_plan_72h_grid_import_for_home_kwh"),
        "solar_export_kwh": data.get("auto_plan_72h_solar_export_kwh"),
        "charge_efficiency_percent": data.get("auto_plan_72h_charge_efficiency_percent"),
        "discharge_efficiency_percent": data.get("auto_plan_72h_discharge_efficiency_percent"),
        "observational_only": data.get("auto_plan_72h_observational_only", True),
        "execution_enabled": data.get("auto_plan_72h_execution_enabled", False),
        "plan": data.get("auto_plan_72h_plan", []),
        "note": data.get("auto_plan_72h_note"),
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
        key="energy_need_status",
        name="Dummy OS EMS Energiebehoefte status",
        value_fn=lambda d: d.get("energy_need_status"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="energy_need_until_solar",
        name="Dummy OS EMS Energiebehoefte tot bruikbare zon",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_until_solar_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="available_battery_energy",
        name="Dummy OS EMS Beschikbare batterij-energie",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_available_battery_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="safety_reserve",
        name="Dummy OS EMS Veiligheidsreserve",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_safety_reserve_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="additional_grid_charge_needed",
        name="Dummy OS EMS Benodigde aanvullende netlading",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_additional_grid_charge_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="tradable_battery_energy",
        name="Dummy OS EMS Vrije verhandelbare batterij-energie",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_tradable_battery_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="first_usable_solar",
        name="Dummy OS EMS Eerste bruikbare solar",
        value_fn=lambda d: d.get("energy_need_first_usable_solar") or "onbekend",
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="energy_need_reason",
        name="Dummy OS EMS Energiebehoefte reden",
        value_fn=lambda d: d.get("energy_need_reason"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_preview_status",
        name="Dummy OS EMS Planner preview status",
        value_fn=lambda d: d.get("planner_preview_status"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_decision",
        name="Dummy OS EMS Planner beslissing",
        value_fn=lambda d: d.get("planner_preview_decision"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_reason",
        name="Dummy OS EMS Planner reden",
        value_fn=lambda d: d.get("planner_preview_reason"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_required_min_soc",
        name="Dummy OS EMS Vereiste minimum-SOC",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("planner_preview_required_min_soc"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_energy_above_reserve",
        name="Dummy OS EMS Energie boven reserve",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("planner_preview_energy_above_reserve_kwh"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_safety_charge",
        name="Dummy OS EMS Veiligheidslading nodig",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("planner_preview_safety_charge_kwh"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_cheapest_required_charge_hours",
        name="Dummy OS EMS Goedkoopste benodigde laaduren",
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("planner_preview_safety_charge_hour_count"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_price_spread",
        name="Dummy OS EMS Planner prijsverschil",
        value_fn=lambda d: d.get("planner_preview_price_spread"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_replan_reason",
        name="Dummy OS EMS Herplan reden",
        value_fn=lambda d: d.get("planner_preview_replan_reason"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_roundtrip_efficiency",
        name="Dummy OS EMS Planner roundtrip rendement",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("planner_preview_roundtrip_efficiency_percent"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_effective_charge_cost",
        name="Dummy OS EMS Effectieve laadkost",
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_effective_charge_cost"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_expected_trade_margin",
        name="Dummy OS EMS Verwachte handelsmarge",
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_expected_trade_margin"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_minimum_trade_margin",
        name="Dummy OS EMS Minimale handelsmarge",
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_minimum_trade_margin"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_charge_time",
        name="Dummy OS EMS Beste handelslaaduur",
        value_fn=lambda d: d.get("planner_preview_best_charge_time") or "onbekend",
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_charge_price",
        name="Dummy OS EMS Beste handelslaadprijs",
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_best_charge_price"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_discharge_time",
        name="Dummy OS EMS Beste handelsontlaaduur",
        value_fn=lambda d: d.get("planner_preview_best_discharge_time") or "onbekend",
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_discharge_price",
        name="Dummy OS EMS Beste handelsontlaadprijs",
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_best_discharge_price"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_status",
        name="Dummy OS EMS Automatisch plan 72u status",
        value_fn=lambda d: d.get("auto_plan_72h_status"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_hours",
        name="Dummy OS EMS Automatisch plan 72u",
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("auto_plan_72h_count"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_end_soc",
        name="Dummy OS EMS Automatisch plan eind-SOC",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_end_soc"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_min_soc",
        name="Dummy OS EMS Automatisch plan minimum-SOC",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_min_soc"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_dynamic_reserve_now",
        name="Dummy OS EMS Automatisch plan dynamische reserve",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_reserve_floor_soc"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_dynamic_reserve_max",
        name="Dummy OS EMS Automatisch plan maximale reserve",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_dynamic_reserve_max_soc"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_solar_charge",
        name="Dummy OS EMS Automatisch plan zonnelading",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_solar_charge_kwh"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_grid_safety_charge",
        name="Dummy OS EMS Automatisch plan veiligheidslading",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_grid_safety_charge_kwh"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_grid_trade_charge",
        name="Dummy OS EMS Automatisch plan handelslading",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_grid_trade_charge_kwh"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_home_discharge",
        name="Dummy OS EMS Automatisch plan ontladen woning",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_home_discharge_kwh"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_grid_trade_discharge",
        name="Dummy OS EMS Automatisch plan ontladen net",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_grid_trade_discharge_kwh"),
        attrs_fn=_auto_plan_72h_attrs,
    ),
    AnkerEmsSensorDescription(
        key="source_monitor",
        name="Dummy OS EMS Bronmonitor",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("source_monitor_status") or "recording",
        attrs_fn=_source_monitor_attrs,
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
    AnkerEmsSensorDescription(
        key="execution_status",
        name="Dummy OS EMS Uitvoering status",
        value_fn=lambda d: d.get("execution_status") or "idle",
        attrs_fn=_execution_attrs,
    ),
    AnkerEmsSensorDescription(
        key="execution_remaining",
        name="Dummy OS EMS Uitvoering resterend",
        native_unit_of_measurement="s",
        value_fn=lambda d: d.get("execution_remaining_s"),
        attrs_fn=_execution_attrs,
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
            "lifecycle_status": plan.get("lifecycle_status", "pending"),
            "lifecycle_reason": plan.get("lifecycle_reason"),
            "lifecycle_updated_at": plan.get("lifecycle_updated_at"),
            "persistent": True,
            "scheduler_selected": scheduler_detail.get("selected", False),
            "scheduler_start_window_end": scheduler_detail.get("start_window_end"),
            "physical_control": False,
            "safety_status": self.coordinator.data.get("safety_status"),
            "controller_status": self.coordinator.data.get("controller_status"),
        }
