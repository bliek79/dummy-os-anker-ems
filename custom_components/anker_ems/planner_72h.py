from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import DEFAULT_BATTERY_CAPACITY_KWH, MIN_SOC_PERCENT

MAX_CHARGE_POWER_W = 3500
MAX_DISCHARGE_POWER_W = 3000
_MIN_ENERGY_KWH = 0.01


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed.astimezone(dt_util.UTC)


def _hour_fraction(hour: datetime, now_utc: datetime) -> float:
    current_hour = now_utc.replace(minute=0, second=0, microsecond=0)
    if hour != current_hour:
        return 1.0
    elapsed = now_utc.minute / 60.0 + now_utc.second / 3600.0
    return max(0.0, min(1.0, 1.0 - elapsed))


def build_72h_plan_preview(
    forecast: list[dict[str, Any]],
    energy_need: dict[str, Any],
    planner_preview: dict[str, Any],
    soc: float | None,
    charge_efficiency_percent: float,
    discharge_efficiency_percent: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a sequential 72-hour battery plan preview.

    Alpha24 is observational only:
    - no plans are written to the three manual slots;
    - no Scheduler call is made;
    - no physical battery command is executed.
    """
    now_utc = (now or dt_util.utcnow()).astimezone(dt_util.UTC)
    current_hour = now_utc.replace(minute=0, second=0, microsecond=0)

    charge_eff = max(0.50, min(1.00, float(charge_efficiency_percent) / 100.0))
    discharge_eff = max(0.50, min(1.00, float(discharge_efficiency_percent) / 100.0))

    if soc is None:
        return {
            "auto_plan_72h_status": "waiting_for_soc",
            "auto_plan_72h_valid": False,
            "auto_plan_72h_reason": "Geen geldige SOC beschikbaar",
            "auto_plan_72h_plan": [],
            "auto_plan_72h_count": 0,
            "auto_plan_72h_observational_only": True,
        }

    rows: list[dict[str, Any]] = []
    for raw in forecast:
        hour = _parse_time(raw.get("time"))
        if hour is None or hour < current_hour:
            continue
        rows.append(
            {
                "time": hour,
                "price": _as_float(raw.get("price")),
                "price_source": raw.get("price_source"),
                "solar_kwh": max(0.0, _as_float(raw.get("solar_kwh")) or 0.0),
                "home_kwh": max(0.0, _as_float(raw.get("home_consumption_kwh")) or 0.0),
            }
        )
    rows.sort(key=lambda item: item["time"])
    rows = rows[:72]

    if not rows:
        return {
            "auto_plan_72h_status": "waiting_for_forecast",
            "auto_plan_72h_valid": False,
            "auto_plan_72h_reason": "Geen bruikbare forecasturen beschikbaar",
            "auto_plan_72h_plan": [],
            "auto_plan_72h_count": 0,
            "auto_plan_72h_observational_only": True,
        }

    capacity = DEFAULT_BATTERY_CAPACITY_KWH
    start_soc = max(float(MIN_SOC_PERCENT), min(100.0, float(soc)))
    stored_kwh = capacity * start_soc / 100.0

    reserve_kwh = _as_float(energy_need.get("energy_need_safety_reserve_kwh")) or 0.0
    reserve_floor_kwh = capacity * float(MIN_SOC_PERCENT) / 100.0 + reserve_kwh
    reserve_floor_kwh = min(capacity, max(capacity * float(MIN_SOC_PERCENT) / 100.0, reserve_floor_kwh))

    safety_hours_raw = planner_preview.get("planner_preview_safety_charge_hours") or []
    safety_by_time: dict[str, float] = {}
    for item in safety_hours_raw:
        if not isinstance(item, dict):
            continue
        t = _parse_time(item.get("time"))
        if t is None:
            continue
        wanted = _as_float(item.get("candidate_battery_energy_kwh"))
        if wanted is None:
            wanted = _as_float(item.get("candidate_energy_kwh"))
        if wanted is not None and wanted > 0:
            safety_by_time[t.isoformat()] = wanted

    trade_profitable = bool(planner_preview.get("planner_preview_trade_profitable"))
    best_charge_time = _parse_time(planner_preview.get("planner_preview_best_charge_time"))
    best_discharge_time = _parse_time(planner_preview.get("planner_preview_best_discharge_time"))

    plan: list[dict[str, Any]] = []
    total_solar_charge = 0.0
    total_grid_safety_charge = 0.0
    total_grid_trade_charge = 0.0
    total_home_discharge = 0.0
    total_grid_trade_discharge = 0.0
    total_grid_import_for_home = 0.0
    total_solar_export = 0.0
    min_soc_seen = start_soc
    max_soc_seen = start_soc

    trade_charge_stored = 0.0

    for row in rows:
        hour = row["time"]
        fraction = _hour_fraction(hour, now_utc)
        charge_input_limit = MAX_CHARGE_POWER_W / 1000.0 * fraction
        discharge_output_limit = MAX_DISCHARGE_POWER_W / 1000.0 * fraction

        solar = row["solar_kwh"] * fraction
        home = row["home_kwh"] * fraction

        solar_to_home = min(solar, home)
        solar_surplus = max(0.0, solar - solar_to_home)
        home_deficit = max(0.0, home - solar_to_home)

        solar_charge_input = 0.0
        grid_safety_input = 0.0
        grid_trade_input = 0.0
        discharge_to_home = 0.0
        discharge_to_grid = 0.0
        grid_home = 0.0
        solar_export = 0.0

        # 1) Solar surplus charges first.
        available_charge_input = charge_input_limit
        if solar_surplus > _MIN_ENERGY_KWH and stored_kwh < capacity - _MIN_ENERGY_KWH:
            max_input_by_capacity = (capacity - stored_kwh) / charge_eff
            solar_charge_input = min(solar_surplus, available_charge_input, max_input_by_capacity)
            stored_added = solar_charge_input * charge_eff
            stored_kwh += stored_added
            available_charge_input -= solar_charge_input
            solar_surplus -= solar_charge_input

        solar_export = max(0.0, solar_surplus)

        # 2) Required safety grid charge has priority over trade.
        safety_target_stored = safety_by_time.get(hour.isoformat(), 0.0)
        if safety_target_stored > _MIN_ENERGY_KWH and stored_kwh < capacity - _MIN_ENERGY_KWH:
            max_input_by_capacity = (capacity - stored_kwh) / charge_eff
            requested_input = safety_target_stored / charge_eff
            grid_safety_input = min(requested_input, available_charge_input, max_input_by_capacity)
            stored_kwh += grid_safety_input * charge_eff
            available_charge_input -= grid_safety_input

        # 3) One observer-only trade charge at alpha23's best buy hour.
        if (
            trade_profitable
            and best_charge_time is not None
            and hour == best_charge_time
            and available_charge_input > _MIN_ENERGY_KWH
            and stored_kwh < capacity - _MIN_ENERGY_KWH
        ):
            max_input_by_capacity = (capacity - stored_kwh) / charge_eff
            grid_trade_input = min(available_charge_input, max_input_by_capacity)
            stored_added = grid_trade_input * charge_eff
            stored_kwh += stored_added
            trade_charge_stored += stored_added

        # 4) Home deficit can use battery only above operational reserve.
        available_stored_above_reserve = max(0.0, stored_kwh - reserve_floor_kwh)
        max_output_from_storage = available_stored_above_reserve * discharge_eff
        discharge_to_home = min(home_deficit, discharge_output_limit, max_output_from_storage)
        if discharge_to_home > _MIN_ENERGY_KWH:
            stored_kwh -= discharge_to_home / discharge_eff
            home_deficit -= discharge_to_home

        grid_home = max(0.0, home_deficit)

        # 5) Observer-only trade discharge at alpha23's best sell hour.
        if (
            trade_profitable
            and best_discharge_time is not None
            and hour == best_discharge_time
        ):
            remaining_output_limit = max(0.0, discharge_output_limit - discharge_to_home)
            available_stored_above_reserve = max(0.0, stored_kwh - reserve_floor_kwh)
            # Only energy that is genuinely above the reserve can be traded.
            max_trade_output = available_stored_above_reserve * discharge_eff
            discharge_to_grid = min(remaining_output_limit, max_trade_output)
            if discharge_to_grid > _MIN_ENERGY_KWH:
                stored_kwh -= discharge_to_grid / discharge_eff

        stored_kwh = max(capacity * float(MIN_SOC_PERCENT) / 100.0, min(capacity, stored_kwh))
        soc_start = plan[-1]["soc_end"] if plan else start_soc
        soc_end = stored_kwh / capacity * 100.0
        min_soc_seen = min(min_soc_seen, soc_end)
        max_soc_seen = max(max_soc_seen, soc_end)

        action_parts: list[str] = []
        if grid_safety_input > _MIN_ENERGY_KWH:
            action_parts.append("veiligheidsladen")
        if grid_trade_input > _MIN_ENERGY_KWH:
            action_parts.append("handelsladen")
        if solar_charge_input > _MIN_ENERGY_KWH:
            action_parts.append("zonneladen")
        if discharge_to_home > _MIN_ENERGY_KWH:
            action_parts.append("woning_ontladen")
        if discharge_to_grid > _MIN_ENERGY_KWH:
            action_parts.append("handel_ontladen")
        if not action_parts:
            action_parts.append("geen_actie")

        total_solar_charge += solar_charge_input
        total_grid_safety_charge += grid_safety_input
        total_grid_trade_charge += grid_trade_input
        total_home_discharge += discharge_to_home
        total_grid_trade_discharge += discharge_to_grid
        total_grid_import_for_home += grid_home
        total_solar_export += solar_export

        plan.append(
            {
                "time": hour.isoformat(),
                "price": row["price"],
                "price_source": row["price_source"],
                "solar_kwh": round(solar, 3),
                "home_consumption_kwh": round(home, 3),
                "solar_to_home_kwh": round(solar_to_home, 3),
                "charge_from_solar_kwh": round(solar_charge_input, 3),
                "charge_from_grid_safety_kwh": round(grid_safety_input, 3),
                "charge_from_grid_trade_kwh": round(grid_trade_input, 3),
                "charge_from_grid_kwh": round(grid_safety_input + grid_trade_input, 3),
                "discharge_to_home_kwh": round(discharge_to_home, 3),
                "discharge_to_grid_kwh": round(discharge_to_grid, 3),
                "grid_import_for_home_kwh": round(grid_home, 3),
                "solar_export_kwh": round(solar_export, 3),
                "soc_start": round(float(soc_start), 1),
                "soc_end": round(soc_end, 1),
                "reserve_floor_soc": round(reserve_floor_kwh / capacity * 100.0, 1),
                "action": "+".join(action_parts),
                "observational_only": True,
            }
        )

    end_soc = plan[-1]["soc_end"] if plan else start_soc

    return {
        "auto_plan_72h_status": "ready",
        "auto_plan_72h_valid": True,
        "auto_plan_72h_reason": (
            "72-uurs planpreview berekend; veiligheidslading heeft voorrang, "
            "daarna solar, woningdekking en observerende handel"
        ),
        "auto_plan_72h_plan": plan,
        "auto_plan_72h_count": len(plan),
        "auto_plan_72h_start": plan[0]["time"] if plan else None,
        "auto_plan_72h_end": plan[-1]["time"] if plan else None,
        "auto_plan_72h_start_soc": round(start_soc, 1),
        "auto_plan_72h_end_soc": round(float(end_soc), 1),
        "auto_plan_72h_min_soc": round(min_soc_seen, 1),
        "auto_plan_72h_max_soc": round(max_soc_seen, 1),
        "auto_plan_72h_reserve_floor_soc": round(reserve_floor_kwh / capacity * 100.0, 1),
        "auto_plan_72h_solar_charge_kwh": round(total_solar_charge, 3),
        "auto_plan_72h_grid_safety_charge_kwh": round(total_grid_safety_charge, 3),
        "auto_plan_72h_grid_trade_charge_kwh": round(total_grid_trade_charge, 3),
        "auto_plan_72h_home_discharge_kwh": round(total_home_discharge, 3),
        "auto_plan_72h_grid_trade_discharge_kwh": round(total_grid_trade_discharge, 3),
        "auto_plan_72h_grid_import_for_home_kwh": round(total_grid_import_for_home, 3),
        "auto_plan_72h_solar_export_kwh": round(total_solar_export, 3),
        "auto_plan_72h_trade_charge_stored_kwh": round(trade_charge_stored, 3),
        "auto_plan_72h_charge_efficiency_percent": round(charge_eff * 100.0, 1),
        "auto_plan_72h_discharge_efficiency_percent": round(discharge_eff * 100.0, 1),
        "auto_plan_72h_observational_only": True,
        "auto_plan_72h_execution_enabled": False,
        "auto_plan_72h_note": (
            "Alpha24 publiceert één doorlopende 72-uurs preview. Er worden geen "
            "planslots gevuld en geen fysieke commando's uitgevoerd."
        ),
    }
