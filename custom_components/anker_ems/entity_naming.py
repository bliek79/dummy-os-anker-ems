from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_SOC_ENTITY

_LOGGER = logging.getLogger(__name__)

# Alpha28 keeps unique IDs stable and migrates only entity_id object IDs.
# This preserves the entity registry identity while making technical entity IDs
# shorter and consistently English.
SENSOR_OBJECT_IDS = {'status': 'status', 'soc': 'soc', 'charge_power': 'charge_power', 'discharge_power': 'discharge_power', 'operating_mode': 'mode', 'forecast_status': 'forecast_status', 'forecast_complete_hours': 'forecast_hours', 'energy_need_status': 'need_status', 'energy_need_until_solar': 'need_to_solar', 'available_battery_energy': 'battery_available', 'safety_reserve': 'safety_reserve', 'additional_grid_charge_needed': 'grid_charge_need', 'tradable_battery_energy': 'battery_tradable', 'first_usable_solar': 'next_usable_solar', 'energy_need_reason': 'need_reason', 'planner_preview_status': 'preview_status', 'planner_decision': 'preview_decision', 'planner_reason': 'preview_reason', 'planner_required_min_soc': 'required_soc', 'planner_energy_above_reserve': 'energy_above_reserve', 'planner_safety_charge': 'safety_charge', 'planner_cheapest_required_charge_hours': 'charge_hours', 'planner_price_spread': 'price_spread', 'planner_replan_reason': 'replan_reason', 'planner_roundtrip_efficiency': 'roundtrip_efficiency', 'planner_effective_charge_cost': 'effective_charge_cost', 'planner_expected_trade_margin': 'trade_margin', 'planner_minimum_trade_margin': 'min_trade_margin', 'planner_best_charge_time': 'best_charge_time', 'planner_best_charge_price': 'best_charge_price', 'planner_best_discharge_time': 'best_discharge_time', 'planner_best_discharge_price': 'best_discharge_price', 'auto_bridge_status': 'bridge_status', 'auto_bridge_candidate_count': 'bridge_candidates', 'auto_bridge_slot_preview_count': 'bridge_slots', 'auto_bridge_slot_1': 'proposal_1', 'auto_bridge_slot_2': 'proposal_2', 'auto_bridge_slot_3': 'proposal_3', 'auto_plan_72h_status': 'plan72_status', 'auto_plan_72h_hours': 'plan72_hours', 'auto_plan_72h_end_soc': 'plan72_end_soc', 'auto_plan_72h_min_soc': 'plan72_min_soc', 'auto_plan_72h_dynamic_reserve_now': 'plan72_reserve', 'auto_plan_72h_dynamic_reserve_max': 'plan72_reserve_max', 'auto_plan_72h_execution_reserve_now': 'plan72_exec_reserve', 'auto_plan_72h_execution_headroom_min': 'plan72_exec_margin', 'auto_plan_72h_execution_buffer_breach_hours': 'plan72_buffer_breach', 'auto_plan_72h_solar_horizon_status': 'plan72_solar_horizon', 'auto_plan_72h_solar_horizon_incomplete_hours': 'plan72_solar_missing', 'auto_plan_72h_solar_charge': 'plan72_solar_charge', 'auto_plan_72h_grid_safety_charge': 'plan72_safety_charge', 'auto_plan_72h_grid_trade_charge': 'plan72_trade_charge', 'auto_plan_72h_home_discharge': 'plan72_home_discharge', 'auto_plan_72h_grid_trade_discharge': 'plan72_grid_discharge', 'source_monitor': 'source_monitor', 'scheduler_status': 'scheduler_status', 'scheduler_selected_plan': 'scheduler_plan', 'safety_status': 'safety_status', 'safety_reason': 'safety_reason', 'controller_status': 'controller_status', 'controller_action': 'controller_action', 'physical_test_status': 'test_status', 'physical_test_remaining': 'test_remaining', 'execution_status': 'execution_status', 'execution_remaining': 'execution_remaining', 'execution_audit': 'execution_audit', 'execution_evaluation': 'plan_vs_actual', 'automatic_execution_monitor': 'execution_monitor', 'automatic_execution_preflight': 'execution_preflight'}

BINARY_SENSOR_OBJECT_IDS = {'sources_available': 'sources_ok', 'control_available': 'control_ok', 'forecast_sources_available': 'forecast_ok', 'scheduler_ready': 'scheduler_ready', 'safety_safe': 'safety_safe', 'controller_ready': 'controller_ready', 'physical_test_active': 'test_active', 'execution_active': 'execution_active', 'planner_safety_charge_needed': 'safety_charge_needed', 'planner_trade_charge_candidate': 'trade_charge_candidate', 'planner_discharge_possible': 'discharge_possible', 'planner_solar_charge_delay': 'solar_charge_delay', 'planner_trade_profitable': 'trade_profitable', 'auto_plan_72h_valid': 'plan72_valid', 'auto_plan_72h_execution_buffer_safe': 'plan72_buffer_safe', 'auto_bridge_valid': 'bridge_valid'}

def _target_object_id(domain: str, suffix: str) -> str | None:
    if domain == "sensor":
        if suffix in SENSOR_OBJECT_IDS:
            return SENSOR_OBJECT_IDS[suffix]
        if suffix.startswith("plan_") and suffix.endswith("_status"):
            return suffix
    elif domain == "binary_sensor":
        return BINARY_SENSOR_OBJECT_IDS.get(suffix)
    elif domain == "number":
        for old, new in (
            ("_power_w", "_power"),
            ("_target_soc", "_target_soc"),
            ("_max_runtime_h", "_runtime"),
            ("_max_start_delay_min", "_start_delay"),
        ):
            if suffix.startswith("plan_") and suffix.endswith(old):
                return suffix[:-len(old)] + new
    elif domain == "select":
        if suffix.startswith("plan_") and suffix.endswith("_action"):
            return suffix
        if suffix.startswith("plan_") and suffix.endswith("_execution_mode"):
            return suffix[:-len("_execution_mode")] + "_mode"
    elif domain == "datetime":
        if suffix.startswith("plan_") and suffix.endswith("_start_time"):
            return suffix[:-len("_start_time")] + "_start"
    return None

async def async_migrate_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    migrated = 0
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = reg_entry.unique_id or ""
        if not unique_id.startswith(prefix):
            continue
        suffix = unique_id[len(prefix):]
        domain = reg_entry.entity_id.split(".", 1)[0]
        object_id = _target_object_id(domain, suffix)
        if not object_id:
            continue
        target = f"{domain}.dummy_os_ems_{object_id}"
        if reg_entry.entity_id == target:
            continue
        existing = registry.async_get(target)
        if existing is not None and existing.id != reg_entry.id:
            _LOGGER.warning(
                "Cannot migrate %s to %s because target entity_id already exists",
                reg_entry.entity_id,
                target,
            )
            continue
        old = reg_entry.entity_id
        registry.async_update_entity(old, new_entity_id=target)
        migrated += 1
        _LOGGER.info("Migrated Dummy OS EMS entity_id %s -> %s", old, target)
    if migrated:
        _LOGGER.info("Migrated %s Dummy OS EMS entity IDs to alpha28 naming", migrated)
    schedule_alpha63_startup_recovery(hass, entry)


async def _async_alpha63_startup_recovery(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recover Plan72 and stale automatic slots after Home Assistant startup."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        return

    # A planner-owned error from an execution interrupted by Home Assistant
    # shutdown is historical audit information, not a reason to lock a physical
    # plan slot after startup. Only expired automatic slots are reconciled;
    # manual plans are deliberately untouched.
    now = dt_util.now()
    for slot in range(1, 4):
        plan = coordinator.plan_store.get_plan(slot)
        if str(plan.get("origin") or "") != "automatic_72h_planner":
            continue
        if str(plan.get("lifecycle_status") or "").lower() != "fout":
            continue
        start_raw = plan.get("start_time")
        start = dt_util.parse_datetime(str(start_raw)) if start_raw else None
        if start is None:
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        try:
            delay_min = max(0.0, float(plan.get("max_start_delay_min", 0) or 0))
        except (TypeError, ValueError):
            delay_min = 0.0
        if now <= start + timedelta(minutes=delay_min):
            continue
        await coordinator.plan_store.async_mark_lifecycle(
            slot, "geannuleerd", "automatic_restart_error_reconciled"
        )

    # The first coordinator pass can occur before the SOC entity is restored.
    # If that pass cached waiting_for_soc, wait briefly for a valid numeric SOC
    # and invalidate only the Plan72 cache. The direct price forecast cache is
    # intentionally left untouched, preserving alpha60 rate limiting.
    soc_entity = coordinator._entity_id(CONF_SOC_ENTITY)
    for _ in range(24):
        state = hass.states.get(soc_entity) if soc_entity else None
        try:
            soc = float(state.state) if state is not None else None
        except (TypeError, ValueError):
            soc = None
        cached = coordinator._cached_72h_plan or {}
        waiting = (
            str(cached.get("auto_plan_72h_status") or "") == "waiting_for_soc"
            or (
                cached.get("auto_plan_72h_valid") is not True
                and int(cached.get("auto_plan_72h_count") or 0) == 0
            )
        )
        if soc is not None and waiting:
            coordinator._cached_72h_plan = None
            await coordinator.async_request_refresh()
            return
        if soc is not None:
            return
        await asyncio.sleep(5)


def schedule_alpha63_startup_recovery(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Schedule the one-shot alpha63 startup recovery task."""
    hass.async_create_task(
        _async_alpha63_startup_recovery(hass, entry),
        "Dummy OS EMS alpha63 startup recovery",
    )
