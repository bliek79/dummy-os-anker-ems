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


def _auto_plan_72h_summary_attrs(data: dict[str, Any]) -> dict[str, Any]:
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
        "execution_buffer_percent": data.get("auto_plan_72h_execution_buffer_percent"),
        "max_charge_power_w": data.get("auto_plan_72h_max_charge_power_w"),
        "max_discharge_power_w": data.get("auto_plan_72h_max_discharge_power_w"),
        "execution_reserve_floor_soc": data.get("auto_plan_72h_execution_reserve_floor_soc"),
        "execution_reserve_min_soc": data.get("auto_plan_72h_execution_reserve_min_soc"),
        "execution_reserve_max_soc": data.get("auto_plan_72h_execution_reserve_max_soc"),
        "min_execution_headroom_soc": data.get("auto_plan_72h_min_execution_headroom_soc"),
        "execution_buffer_breach_hours": data.get("auto_plan_72h_execution_buffer_breach_hours"),
        "execution_buffer_safe": data.get("auto_plan_72h_execution_buffer_safe", False),
        "solar_horizon_complete": data.get("auto_plan_72h_solar_horizon_complete"),
        "solar_horizon_incomplete_hours": data.get("auto_plan_72h_solar_horizon_incomplete_hours"),
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
        "refresh_policy": data.get("auto_plan_72h_refresh_policy"),
        "refresh_cached": data.get("auto_plan_72h_refresh_cached", False),
        "refresh_reason": data.get("auto_plan_72h_refresh_reason"),
        "last_refreshed_at": data.get("auto_plan_72h_last_refreshed_at"),
        "refresh_count_today": data.get("auto_plan_72h_refresh_count_today", 0),
        "periodic_window": data.get("auto_plan_72h_periodic_window"),
        "periodic_max_per_hour": data.get("auto_plan_72h_periodic_max_per_hour", 1),
        "event_refresh_enabled": data.get("auto_plan_72h_event_refresh_enabled", True),
        "price_architecture_enabled": data.get("price_architecture_enabled", False),
        "price_architecture_source": data.get("price_architecture_source"),
        "price_architecture_market_rows": data.get("price_architecture_market_rows"),
        "import_markup_per_kwh": data.get("price_architecture_import_markup_per_kwh"),
        "export_markup_per_kwh": data.get("price_architecture_export_markup_per_kwh"),
        "tariff_resolution_requested": data.get("price_architecture_requested_resolution"),
        "tariff_resolution_effective": data.get("price_architecture_effective_resolution"),
        "quarter_hour_ready": data.get("price_architecture_quarter_hour_ready", False),
        "note": data.get("auto_plan_72h_note"),
    }


def _auto_plan_72h_chart_attrs(data: dict[str, Any]) -> dict[str, Any]:
    attrs = _auto_plan_72h_summary_attrs(data)
    attrs["plan"] = data.get("auto_plan_72h_plan", [])
    return attrs


def _auto_bridge_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": data.get("auto_bridge_valid", False),
        "reason": data.get("auto_bridge_reason"),
        "candidate_count": data.get("auto_bridge_candidate_count"),
        "slot_preview_count": data.get("auto_bridge_slot_preview_count"),
        "overflow_count": data.get("auto_bridge_overflow_count"),
        "invalid_candidate_count": data.get("auto_bridge_invalid_candidate_count"),
        "rolling_window": data.get("auto_bridge_rolling_window", True),
        "electrical_profile": data.get("electrical_profile"),
        "max_charge_power_w": data.get("max_charge_power_w"),
        "max_discharge_power_w": data.get("max_discharge_power_w"),
        "slot_capacity": data.get("auto_bridge_slot_capacity"),
        "available_manual_slots": data.get("auto_bridge_available_manual_slots"),
        "manual_slot_conflict": data.get("auto_bridge_manual_slot_conflict", False),
        "manual_slot_conflict_count": data.get("auto_bridge_manual_slot_conflict_count"),
        "manual_slots": data.get("auto_bridge_manual_slots", []),
        "candidates": data.get("auto_bridge_candidates", []),
        "slot_preview": data.get("auto_bridge_slot_preview", []),
        "plan_store_write_enabled": data.get("auto_bridge_plan_store_write_enabled", False),
        "plan_store_write_gate_open": data.get("auto_bridge_plan_store_write_gate_open", False),
        "plan_store_write_changed": data.get("auto_bridge_plan_store_write_changed", False),
        "plan_store_written_slots": data.get("auto_bridge_plan_store_written_slots", []),
        "plan_store_cleared_slots": data.get("auto_bridge_plan_store_cleared_slots", []),
        "plan_store_skipped_slots": data.get("auto_bridge_plan_store_skipped_slots", []),
        "scheduler_handoff_enabled": data.get("auto_bridge_scheduler_handoff_enabled", False),
        "scheduler_handoff_gate_open": data.get("auto_bridge_scheduler_handoff_gate_open", False),
        "scheduler_handoff_changed": data.get("auto_bridge_scheduler_handoff_changed", False),
        "scheduler_handoff_slots": data.get("auto_bridge_scheduler_handoff_slots", []),
        "scheduler_handoff_skipped_slots": data.get("auto_bridge_scheduler_handoff_skipped_slots", []),
        "prestart_enabled": data.get("auto_prestart_enabled", False),
        "prestart_required": data.get("auto_prestart_required", False),
        "prestart_safe": data.get("auto_prestart_safe", False),
        "prestart_status": data.get("auto_prestart_status"),
        "prestart_reason": data.get("auto_prestart_reason"),
        "prestart_reasons": data.get("auto_prestart_reasons", []),
        "prestart_warnings": data.get("auto_prestart_warnings", []),
        "prestart_selected_slot": data.get("auto_prestart_selected_slot"),
        "prestart_planner_identity": data.get("auto_prestart_planner_identity"),
        "prestart_identity_match": data.get("auto_prestart_current_identity_match", False),
        "prestart_signature_match": data.get("auto_prestart_current_signature_match", False),
        "prestart_current_soc": data.get("auto_prestart_current_soc"),
        "prestart_target_soc": data.get("auto_prestart_target_soc"),
        "prestart_execution_reserve_soc": data.get("auto_prestart_execution_reserve_soc"),
        "prestart_diagnostic_enabled": data.get("auto_prestart_diagnostic_enabled", False),
        "prestart_diagnostic_status": data.get("auto_prestart_diagnostic_status"),
        "prestart_diagnostic_safe": data.get("auto_prestart_diagnostic_safe", False),
        "prestart_diagnostic_slot": data.get("auto_prestart_diagnostic_slot"),
        "prestart_diagnostic_planner_identity": data.get("auto_prestart_diagnostic_planner_identity"),
        "prestart_diagnostic_start_time": data.get("auto_prestart_diagnostic_start_time"),
        "prestart_diagnostic_minutes_to_start": data.get("auto_prestart_diagnostic_minutes_to_start"),
        "prestart_diagnostic_phase": data.get("auto_prestart_diagnostic_phase"),
        "prestart_diagnostic_authoritative": data.get("auto_prestart_diagnostic_authoritative", False),
        "prestart_diagnostic_live_soc_enforced": data.get("auto_prestart_diagnostic_live_soc_enforced", False),
        "prestart_diagnostic_decision_window_min": data.get("auto_prestart_diagnostic_decision_window_min"),
        "prestart_diagnostic_action": data.get("auto_prestart_diagnostic_action"),
        "prestart_diagnostic_power_w": data.get("auto_prestart_diagnostic_power_w"),
        "prestart_diagnostic_current_soc": data.get("auto_prestart_diagnostic_current_soc"),
        "prestart_diagnostic_target_soc": data.get("auto_prestart_diagnostic_target_soc"),
        "prestart_diagnostic_execution_reserve_soc": data.get("auto_prestart_diagnostic_execution_reserve_soc"),
        "prestart_diagnostic_identity_match": data.get("auto_prestart_diagnostic_identity_match", False),
        "prestart_diagnostic_signature_match": data.get("auto_prestart_diagnostic_signature_match", False),
        "prestart_diagnostic_blockers": data.get("auto_prestart_diagnostic_blockers", []),
        "prestart_diagnostic_warnings": data.get("auto_prestart_diagnostic_warnings", []),
        "prestart_diagnostic_checks": data.get("auto_prestart_diagnostic_checks", []),
        "prestart_test_matrix": data.get("auto_prestart_test_matrix", []),
        "safety_handoff_enabled": data.get("auto_safety_handoff_enabled", False),
        "safety_handoff_required": data.get("auto_safety_handoff_required", False),
        "safety_handoff_safe": data.get("auto_safety_handoff_safe", False),
        "safety_handoff_status": data.get("auto_safety_handoff_status"),
        "safety_handoff_reason": data.get("auto_safety_handoff_reason"),
        "safety_handoff_reasons": data.get("auto_safety_handoff_reasons", []),
        "safety_handoff_warnings": data.get("auto_safety_handoff_warnings", []),
        "safety_handoff_selected_slot": data.get("auto_safety_handoff_selected_slot"),
        "safety_handoff_planner_identity": data.get("auto_safety_handoff_planner_identity"),
        "safety_handoff_prestart_safe": data.get("auto_safety_handoff_prestart_safe", False),
        "safety_handoff_control_path_configured": data.get("auto_safety_handoff_control_path_configured", False),
        "safety_handoff_execution_permitted": data.get("auto_safety_handoff_execution_permitted", False),
        "safety_handoff_physical_control": data.get("auto_safety_handoff_physical_control", False),
        "safety_handoff_max_charge_power_w": data.get("auto_safety_handoff_max_charge_power_w"),
        "safety_handoff_max_discharge_power_w": data.get("auto_safety_handoff_max_discharge_power_w"),
        "execution_handoff_enabled": data.get("auto_execution_handoff_enabled", False),
        "execution_handoff_required": data.get("auto_execution_handoff_required", False),
        "execution_handoff_ready": data.get("auto_execution_handoff_ready", False),
        "execution_handoff_status": data.get("auto_execution_handoff_status"),
        "execution_handoff_reason": data.get("auto_execution_handoff_reason"),
        "execution_handoff_reasons": data.get("auto_execution_handoff_reasons", []),
        "execution_handoff_warnings": data.get("auto_execution_handoff_warnings", []),
        "execution_handoff_selected_slot": data.get("auto_execution_handoff_selected_slot"),
        "execution_handoff_planner_identity": data.get("auto_execution_handoff_planner_identity"),
        "execution_handoff_action": data.get("auto_execution_handoff_action"),
        "execution_handoff_power_w": data.get("auto_execution_handoff_power_w"),
        "execution_handoff_target_soc": data.get("auto_execution_handoff_target_soc"),
        "execution_handoff_max_runtime_h": data.get("auto_execution_handoff_max_runtime_h"),
        "execution_handoff_safety_safe": data.get("auto_execution_handoff_safety_safe", False),
        "execution_handoff_control_path_configured": data.get("auto_execution_handoff_control_path_configured", False),
        "execution_handoff_controller_idle": data.get("auto_execution_handoff_controller_idle", False),
        "execution_handoff_physical_test_idle": data.get("auto_execution_handoff_physical_test_idle", False),
        "execution_handoff_final_revalidation_required": data.get("auto_execution_handoff_final_revalidation_required", True),
        "execution_handoff_execution_permitted": data.get("auto_execution_handoff_execution_permitted", False),
        "execution_handoff_physical_control": data.get("auto_execution_handoff_physical_control", False),
        "final_revalidation_enabled": data.get("auto_final_revalidation_enabled", False),
        "final_revalidation_required": data.get("auto_final_revalidation_required", False),
        "final_revalidation_safe": data.get("auto_final_revalidation_safe", False),
        "final_revalidation_status": data.get("auto_final_revalidation_status"),
        "final_revalidation_reason": data.get("auto_final_revalidation_reason"),
        "final_revalidation_reasons": data.get("auto_final_revalidation_reasons", []),
        "final_revalidation_warnings": data.get("auto_final_revalidation_warnings", []),
        "final_revalidation_checks": data.get("auto_final_revalidation_checks", []),
        "final_revalidation_selected_slot": data.get("auto_final_revalidation_selected_slot"),
        "final_revalidation_planner_identity": data.get("auto_final_revalidation_planner_identity"),
        "final_revalidation_planner_signature": data.get("auto_final_revalidation_planner_signature"),
        "final_revalidation_checked_at": data.get("auto_final_revalidation_checked_at"),
        "final_revalidation_action": data.get("auto_final_revalidation_action"),
        "final_revalidation_power_w": data.get("auto_final_revalidation_power_w"),
        "final_revalidation_target_soc": data.get("auto_final_revalidation_target_soc"),
        "final_revalidation_current_soc": data.get("auto_final_revalidation_current_soc"),
        "final_revalidation_execution_reserve_soc": data.get("auto_final_revalidation_execution_reserve_soc"),
        "final_revalidation_control_path_configured": data.get("auto_final_revalidation_control_path_configured", False),
        "final_revalidation_controller_idle": data.get("auto_final_revalidation_controller_idle", False),
        "final_revalidation_physical_test_idle": data.get("auto_final_revalidation_physical_test_idle", False),
        "final_revalidation_mode_switch_required": data.get("auto_final_revalidation_mode_switch_required", False),
        "final_revalidation_execution_permitted": data.get("auto_final_revalidation_execution_permitted", False),
        "final_revalidation_physical_control": data.get("auto_final_revalidation_physical_control", False),
        "mode_switch_preview_enabled": data.get("auto_mode_switch_preview_enabled", False),
        "mode_switch_preview_required": data.get("auto_mode_switch_preview_required", False),
        "mode_switch_preview_ready": data.get("auto_mode_switch_preview_ready", False),
        "mode_switch_preview_status": data.get("auto_mode_switch_preview_status"),
        "mode_switch_preview_reason": data.get("auto_mode_switch_preview_reason"),
        "mode_switch_preview_blockers": data.get("auto_mode_switch_preview_blockers", []),
        "mode_switch_preview_steps": data.get("auto_mode_switch_preview_steps", []),
        "mode_switch_preview_current_mode": data.get("auto_mode_switch_preview_current_mode"),
        "mode_switch_preview_power_setpoint_w": data.get("auto_mode_switch_preview_power_setpoint_w"),
        "mode_switch_preview_zero_power_guard_required": data.get("auto_mode_switch_preview_zero_power_guard_required", True),
        "mode_switch_preview_post_mode_revalidation_required": data.get("auto_mode_switch_preview_post_mode_revalidation_required", True),
        "mode_switch_preview_safe_return_required": data.get("auto_mode_switch_preview_safe_return_required", True),
        "mode_switch_preview_execution_permitted": data.get("auto_mode_switch_preview_execution_permitted", False),
        "mode_switch_preview_physical_control": data.get("auto_mode_switch_preview_physical_control", False),
        "mode_switch_live_active": data.get("execution_auto_mode_switch_active", False),
        "mode_switch_live_status": data.get("execution_auto_mode_switch_status"),
        "mode_switch_live_reason": data.get("execution_auto_mode_switch_reason"),
        "mode_switch_live_identity": data.get("execution_auto_mode_switch_identity"),
        "mode_switch_live_started_at": data.get("execution_auto_mode_switch_started_at"),
        "mode_switch_live_completed_at": data.get("execution_auto_mode_switch_completed_at"),
        "mode_switch_live_last_identity": data.get("execution_auto_mode_switch_last_identity"),
        "mode_switch_live_last_result": data.get("execution_auto_mode_switch_last_result"),
        "mode_switch_live_physical_scope": "zero_power_mode_switch_safe_return_only",
        "mode_switch_live_direction_power_enabled": False,
        "execution_enabled": data.get("auto_bridge_execution_enabled", False),
        "observational_only": data.get("auto_bridge_observational_only", True),
        "note": data.get("auto_bridge_note"),
    }


def _auto_bridge_slot_attrs(data: dict[str, Any], index: int) -> dict[str, Any]:
    preview = data.get("auto_bridge_slot_preview") or []
    item = preview[index] if index < len(preview) else None
    return {
        "slot_preview": item,
        "preview_index": index + 1,
        "candidate_count": data.get("auto_bridge_candidate_count"),
        "overflow_count": data.get("auto_bridge_overflow_count"),
        "plan_store_write_enabled": data.get("auto_bridge_plan_store_write_enabled", False),
        "scheduler_handoff_enabled": data.get("auto_bridge_scheduler_handoff_enabled", False),
        "scheduler_handoff_gate_open": data.get("auto_bridge_scheduler_handoff_gate_open", False),
        "scheduler_handoff_changed": data.get("auto_bridge_scheduler_handoff_changed", False),
        "scheduler_handoff_slots": data.get("auto_bridge_scheduler_handoff_slots", []),
        "scheduler_handoff_skipped_slots": data.get("auto_bridge_scheduler_handoff_skipped_slots", []),
        "execution_enabled": data.get("auto_bridge_execution_enabled", False),
        "observational_only": True,
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
        name='Dummy OS EMS Status',
        value_fn=lambda d: "simulation" if d.get("simulation_mode") else "observe",
    ),
    AnkerEmsSensorDescription(
        key="soc",
        name='Dummy OS EMS SOC',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("soc"),
    ),
    AnkerEmsSensorDescription(
        key="charge_power",
        name='Dummy OS EMS Charge Power',
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: d.get("charge_power_w"),
    ),
    AnkerEmsSensorDescription(
        key="discharge_power",
        name='Dummy OS EMS Discharge Power',
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: d.get("discharge_power_w"),
    ),
    AnkerEmsSensorDescription(
        key="operating_mode",
        name='Dummy OS EMS Operating Mode',
        value_fn=lambda d: d.get("operating_mode"),
    ),
    AnkerEmsSensorDescription(
        key="forecast_status",
        name='Dummy OS EMS Forecast Status',
        value_fn=lambda d: d.get("forecast_status"),
        attrs_fn=_forecast_attrs,
    ),
    AnkerEmsSensorDescription(
        key="forecast_complete_hours",
        name='Dummy OS EMS Forecast Hours',
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("forecast_complete_hours"),
    ),
    AnkerEmsSensorDescription(
        key="energy_need_status",
        name='Dummy OS EMS Energy Need Status',
        value_fn=lambda d: d.get("energy_need_status"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="energy_need_until_solar",
        name='Dummy OS EMS Energy Need To Solar',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_until_solar_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="available_battery_energy",
        name='Dummy OS EMS Available Battery Energy',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_available_battery_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="safety_reserve",
        name='Dummy OS EMS Safety Reserve',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_safety_reserve_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="additional_grid_charge_needed",
        name='Dummy OS EMS Grid Charge Need',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_additional_grid_charge_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="tradable_battery_energy",
        name='Dummy OS EMS Tradable Battery Energy',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("energy_need_tradable_battery_kwh"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="first_usable_solar",
        name='Dummy OS EMS Next Usable Solar',
        value_fn=lambda d: d.get("energy_need_first_usable_solar") or "onbekend",
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="energy_need_reason",
        name='Dummy OS EMS Energy Need Reason',
        value_fn=lambda d: d.get("energy_need_reason"),
        attrs_fn=_energy_need_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_preview_status",
        name='Dummy OS EMS Preview Status',
        value_fn=lambda d: d.get("planner_preview_status"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_decision",
        name='Dummy OS EMS Preview Decision',
        value_fn=lambda d: d.get("planner_preview_decision"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_reason",
        name='Dummy OS EMS Preview Reason',
        value_fn=lambda d: d.get("planner_preview_reason"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_required_min_soc",
        name='Dummy OS EMS Required SOC',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("planner_preview_required_min_soc"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_energy_above_reserve",
        name='Dummy OS EMS Energy Above Reserve',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("planner_preview_energy_above_reserve_kwh"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_safety_charge",
        name='Dummy OS EMS Safety Charge',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("planner_preview_safety_charge_kwh"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_cheapest_required_charge_hours",
        name='Dummy OS EMS Required Charge Hours',
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("planner_preview_safety_charge_hour_count"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_price_spread",
        name='Dummy OS EMS Price Spread',
        value_fn=lambda d: d.get("planner_preview_price_spread"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_replan_reason",
        name='Dummy OS EMS Replan Reason',
        value_fn=lambda d: d.get("planner_preview_replan_reason"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_roundtrip_efficiency",
        name='Dummy OS EMS Roundtrip Efficiency',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("planner_preview_roundtrip_efficiency_percent"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_effective_charge_cost",
        name='Dummy OS EMS Effective Charge Cost',
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_effective_charge_cost"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_expected_trade_margin",
        name='Dummy OS EMS Expected Trade Margin',
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_expected_trade_margin"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_minimum_trade_margin",
        name='Dummy OS EMS Minimum Trade Margin',
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_minimum_trade_margin"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_charge_time",
        name='Dummy OS EMS Best Charge Time',
        value_fn=lambda d: d.get("planner_preview_best_charge_time") or "onbekend",
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_charge_price",
        name='Dummy OS EMS Best Charge Price',
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_best_charge_price"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_discharge_time",
        name='Dummy OS EMS Best Discharge Time',
        value_fn=lambda d: d.get("planner_preview_best_discharge_time") or "onbekend",
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="planner_best_discharge_price",
        name='Dummy OS EMS Best Discharge Price',
        native_unit_of_measurement="€/kWh",
        value_fn=lambda d: d.get("planner_preview_best_discharge_price"),
        attrs_fn=_planner_preview_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_bridge_status",
        name='Dummy OS EMS Action Bridge Status',
        value_fn=lambda d: d.get("auto_bridge_status"),
        attrs_fn=_auto_bridge_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_bridge_candidate_count",
        name='Dummy OS EMS Action Candidates',
        value_fn=lambda d: d.get("auto_bridge_candidate_count"),
        attrs_fn=_auto_bridge_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_bridge_slot_preview_count",
        name='Dummy OS EMS Action Slot Preview',
        value_fn=lambda d: d.get("auto_bridge_slot_preview_count"),
        attrs_fn=_auto_bridge_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_bridge_slot_1",
        name='Dummy OS EMS Plan Proposal 1',
        value_fn=lambda d: ((d.get("auto_bridge_slot_preview") or [{}])[0].get("purpose") if len(d.get("auto_bridge_slot_preview") or []) > 0 else "geen"),
        attrs_fn=lambda d: _auto_bridge_slot_attrs(d, 0),
    ),
    AnkerEmsSensorDescription(
        key="auto_bridge_slot_2",
        name='Dummy OS EMS Plan Proposal 2',
        value_fn=lambda d: ((d.get("auto_bridge_slot_preview") or [{}, {}])[1].get("purpose") if len(d.get("auto_bridge_slot_preview") or []) > 1 else "geen"),
        attrs_fn=lambda d: _auto_bridge_slot_attrs(d, 1),
    ),
    AnkerEmsSensorDescription(
        key="auto_bridge_slot_3",
        name='Dummy OS EMS Plan Proposal 3',
        value_fn=lambda d: ((d.get("auto_bridge_slot_preview") or [{}, {}, {}])[2].get("purpose") if len(d.get("auto_bridge_slot_preview") or []) > 2 else "geen"),
        attrs_fn=lambda d: _auto_bridge_slot_attrs(d, 2),
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_status",
        name='Dummy OS EMS Plan72 Status',
        value_fn=lambda d: d.get("auto_plan_72h_status"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_hours",
        name='Dummy OS EMS Plan72 Hours',
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("auto_plan_72h_count"),
        attrs_fn=_auto_plan_72h_chart_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_end_soc",
        name='Dummy OS EMS Plan72 End SOC',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_end_soc"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_min_soc",
        name='Dummy OS EMS Plan72 Minimum SOC',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_min_soc"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_dynamic_reserve_now",
        name='Dummy OS EMS Plan72 Reserve',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_reserve_floor_soc"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_dynamic_reserve_max",
        name='Dummy OS EMS Plan72 Maximum Reserve',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_dynamic_reserve_max_soc"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_execution_reserve_now",
        name='Dummy OS EMS Plan72 Execution Reserve',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_execution_reserve_floor_soc"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_execution_headroom_min",
        name='Dummy OS EMS Plan72 Execution Margin',
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("auto_plan_72h_min_execution_headroom_soc"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_execution_buffer_breach_hours",
        name='Dummy OS EMS Plan72 Buffer Breach',
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("auto_plan_72h_execution_buffer_breach_hours"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_solar_horizon_status",
        name='Dummy OS EMS Plan72 Solar Horizon',
        value_fn=lambda d: (
            "volledig"
            if d.get("auto_plan_72h_solar_horizon_complete")
            else "onvolledig"
        ),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_solar_horizon_incomplete_hours",
        name='Dummy OS EMS Plan72 Missing Solar Hours',
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("auto_plan_72h_solar_horizon_incomplete_hours"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_solar_charge",
        name='Dummy OS EMS Plan72 Solar Charge',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_solar_charge_kwh"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_grid_safety_charge",
        name='Dummy OS EMS Plan72 Safety Charge',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_grid_safety_charge_kwh"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_grid_trade_charge",
        name='Dummy OS EMS Plan72 Trade Charge',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_grid_trade_charge_kwh"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_home_discharge",
        name='Dummy OS EMS Plan72 Home Discharge',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_home_discharge_kwh"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="auto_plan_72h_grid_trade_discharge",
        name='Dummy OS EMS Plan72 Grid Discharge',
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda d: d.get("auto_plan_72h_grid_trade_discharge_kwh"),
        attrs_fn=_auto_plan_72h_summary_attrs,
    ),
    AnkerEmsSensorDescription(
        key="source_monitor",
        name='Dummy OS EMS Source Monitor',
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.get("source_monitor_status") or "recording",
        attrs_fn=_source_monitor_attrs,
    ),
    AnkerEmsSensorDescription(
        key="scheduler_status",
        name='Dummy OS EMS Scheduler Status',
        value_fn=lambda d: d.get("scheduler_status"),
        attrs_fn=_scheduler_attrs,
    ),
    AnkerEmsSensorDescription(
        key="scheduler_selected_plan",
        name='Dummy OS EMS Scheduler Plan',
        value_fn=lambda d: (
            f"plan_{d.get('scheduler_selected_slot')}"
            if d.get("scheduler_selected_slot") is not None
            else "geen"
        ),
        attrs_fn=_scheduler_attrs,
    ),
    AnkerEmsSensorDescription(
        key="safety_status",
        name='Dummy OS EMS Safety Status',
        value_fn=lambda d: d.get("safety_status"),
        attrs_fn=_safety_attrs,
    ),
    AnkerEmsSensorDescription(
        key="safety_reason",
        name='Dummy OS EMS Safety Reason',
        value_fn=lambda d: d.get("safety_reason"),
        attrs_fn=_safety_attrs,
    ),
    AnkerEmsSensorDescription(
        key="controller_status",
        name='Dummy OS EMS Controller Status',
        value_fn=lambda d: d.get("controller_status"),
        attrs_fn=_controller_attrs,
    ),
    AnkerEmsSensorDescription(
        key="controller_action",
        name='Dummy OS EMS Controller Action',
        value_fn=lambda d: d.get("controller_action") or "geen",
        attrs_fn=_controller_attrs,
    ),
    AnkerEmsSensorDescription(
        key="physical_test_status",
        name='Dummy OS EMS Physical Test Status',
        value_fn=lambda d: d.get("physical_test_status") or "idle",
        attrs_fn=_physical_test_attrs,
    ),
    AnkerEmsSensorDescription(
        key="physical_test_remaining",
        name='Dummy OS EMS Physical Test Remaining',
        native_unit_of_measurement="s",
        value_fn=lambda d: d.get("physical_test_remaining_s"),
        attrs_fn=_physical_test_attrs,
    ),
    AnkerEmsSensorDescription(
        key="execution_status",
        name='Dummy OS EMS Execution Status',
        value_fn=lambda d: d.get("execution_status") or "idle",
        attrs_fn=_execution_attrs,
    ),
    AnkerEmsSensorDescription(
        key="execution_remaining",
        name='Dummy OS EMS Execution Remaining',
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
    _unrecorded_attributes = frozenset({"plan"})

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
            "origin": plan.get("origin", "manual"),
            "purpose": plan.get("purpose"),
            "planner_generated_at": plan.get("planner_generated_at"),
            "planner_signature": plan.get("planner_signature"),
            "persistent": True,
            "scheduler_selected": scheduler_detail.get("selected", False),
            "scheduler_start_window_end": scheduler_detail.get("start_window_end"),
            "physical_control": False,
            "safety_status": self.coordinator.data.get("safety_status"),
            "controller_status": self.coordinator.data.get("controller_status"),
        }
