from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Any

from homeassistant.util import dt as dt_util

from .const import DEFAULT_BATTERY_CAPACITY_KWH, MIN_SOC_PERCENT

MAX_CHARGE_POWER_W = 3500
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


def build_planner_preview(
    forecast: list[dict[str, Any]],
    energy_need: dict[str, Any],
    soc: float | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build an observational decision preview without creating plans.

    Alpha22 intentionally keeps financial trading decisions non-executable.
    Safety charging can already be identified from the alpha21 energy balance.
    Price hours are ranked for observation, but charge/discharge losses and a
    required net-profit threshold are not yet part of the trading decision.
    """
    now_utc = (now or dt_util.utcnow()).astimezone(dt_util.UTC)
    current_hour = now_utc.replace(minute=0, second=0, microsecond=0)

    valid = bool(energy_need.get("energy_need_valid"))
    need_kwh = _as_float(energy_need.get("energy_need_until_solar_kwh")) or 0.0
    reserve_kwh = _as_float(energy_need.get("energy_need_safety_reserve_kwh")) or 0.0
    additional_kwh = _as_float(
        energy_need.get("energy_need_additional_grid_charge_kwh")
    )
    tradable_kwh = _as_float(energy_need.get("energy_need_tradable_battery_kwh"))
    first_usable = _parse_time(energy_need.get("energy_need_first_usable_solar"))

    required_min_soc = MIN_SOC_PERCENT + (
        (need_kwh + reserve_kwh) / DEFAULT_BATTERY_CAPACITY_KWH * 100.0
    )
    required_min_soc = max(float(MIN_SOC_PERCENT), min(100.0, required_min_soc))

    price_rows: list[dict[str, Any]] = []
    for raw in forecast:
        hour = _parse_time(raw.get("time"))
        price = _as_float(raw.get("price"))
        if hour is None or price is None or hour < current_hour:
            continue
        price_rows.append(
            {
                "time": hour,
                "price": price,
                "price_source": raw.get("price_source"),
                "solar_kwh": _as_float(raw.get("solar_kwh")),
                "home_consumption_kwh": _as_float(raw.get("home_consumption_kwh")),
            }
        )
    price_rows.sort(key=lambda item: item["time"])

    prices = [row["price"] for row in price_rows]
    price_min = min(prices) if prices else None
    price_max = max(prices) if prices else None
    price_spread = (
        price_max - price_min if price_min is not None and price_max is not None else None
    )

    # Safety charging must happen before usable solar returns. Rank available
    # hours by price and allocate only the energy deficit. A 3500 W maximum is
    # used solely to estimate how many hourly slots would be needed. Losses are
    # deliberately not applied yet, so these are candidate hours, not commands.
    safety_candidates = [
        row
        for row in price_rows
        if first_usable is None or row["time"] < first_usable
    ]
    safety_candidates.sort(key=lambda item: (item["price"], item["time"]))

    remaining = max(additional_kwh or 0.0, 0.0)
    selected_hours: list[dict[str, Any]] = []
    for row in safety_candidates:
        if remaining <= _MIN_ENERGY_KWH:
            break
        fraction = 1.0
        if row["time"] == current_hour:
            elapsed = now_utc.minute / 60.0 + now_utc.second / 3600.0
            fraction = max(0.0, min(1.0, 1.0 - elapsed))
        capacity_kwh = MAX_CHARGE_POWER_W / 1000.0 * fraction
        if capacity_kwh <= 0:
            continue
        allocated = min(remaining, capacity_kwh)
        selected_hours.append(
            {
                "time": row["time"].isoformat(),
                "price": row["price"],
                "price_source": row["price_source"],
                "max_slot_energy_kwh": round(capacity_kwh, 3),
                "candidate_energy_kwh": round(allocated, 3),
            }
        )
        remaining -= allocated

    safety_charge_needed = bool(
        valid and additional_kwh is not None and additional_kwh > _MIN_ENERGY_KWH
    )
    safety_schedule_sufficient = bool(
        not safety_charge_needed or remaining <= _MIN_ENERGY_KWH
    )
    discharge_possible = bool(
        valid
        and tradable_kwh is not None
        and tradable_kwh > _MIN_ENERGY_KWH
        and soc is not None
        and float(soc) > required_min_soc
    )

    solar_charge_delay = bool(
        valid
        and not safety_charge_needed
        and first_usable is not None
        and first_usable > now_utc
    )

    # Trading is only a candidate in alpha22. A positive price spread and free
    # battery capacity are observable facts, but actual profitability must wait
    # for explicit charge/discharge losses and a minimum net-margin model.
    free_capacity_kwh = None
    if soc is not None:
        free_capacity_kwh = DEFAULT_BATTERY_CAPACITY_KWH * max(0.0, 100.0 - float(soc)) / 100.0
    trade_charge_candidate = bool(
        valid
        and not safety_charge_needed
        and free_capacity_kwh is not None
        and free_capacity_kwh > _MIN_ENERGY_KWH
        and price_spread is not None
        and price_spread > 0
    )

    if not valid:
        decision = "wachten"
        reason = "Energiebalans is nog niet volledig geldig"
    elif safety_charge_needed:
        decision = "veiligheidsladen"
        if safety_schedule_sufficient:
            reason = (
                "Batterij-energie is onvoldoende voor behoefte plus reserve; "
                "goedkoopste kandidaat-laaduren zijn geselecteerd"
            )
        else:
            reason = (
                "Batterij-energie is onvoldoende en de beschikbare uren voor "
                "bruikbare zon lijken niet genoeg om het tekort volledig te laden"
            )
    elif solar_charge_delay:
        decision = "wachten"
        reason = (
            "Voldoende batterijreserve tot bruikbare zon; netladen nu uitstellen"
        )
    else:
        decision = "geen_actie"
        reason = (
            "Geen veiligheidslading nodig; handelsbeslissing blijft observerend "
            "tot verliezen en minimale netto marge zijn gemodelleerd"
        )

    cheapest_preview = sorted(price_rows, key=lambda item: (item["price"], item["time"]))[:6]
    cheapest_preview = [
        {
            "time": row["time"].isoformat(),
            "price": row["price"],
            "price_source": row["price_source"],
        }
        for row in cheapest_preview
    ]

    return {
        "planner_preview_status": "ready" if valid else "waiting_for_energy_balance",
        "planner_preview_decision": decision,
        "planner_preview_reason": reason,
        "planner_preview_required_min_soc": round(required_min_soc, 1),
        "planner_preview_energy_above_reserve_kwh": (
            round(tradable_kwh, 3) if tradable_kwh is not None else None
        ),
        "planner_preview_safety_charge_needed": safety_charge_needed,
        "planner_preview_safety_charge_kwh": (
            round(additional_kwh, 3) if additional_kwh is not None else None
        ),
        "planner_preview_safety_charge_hours": selected_hours,
        "planner_preview_safety_charge_hour_count": len(selected_hours),
        "planner_preview_safety_schedule_sufficient": safety_schedule_sufficient,
        "planner_preview_trade_charge_candidate": trade_charge_candidate,
        "planner_preview_discharge_possible": discharge_possible,
        "planner_preview_solar_charge_delay": solar_charge_delay,
        "planner_preview_first_usable_solar": (
            first_usable.isoformat() if first_usable is not None else None
        ),
        "planner_preview_price_min": price_min,
        "planner_preview_price_max": price_max,
        "planner_preview_price_spread": (
            round(price_spread, 6) if price_spread is not None else None
        ),
        "planner_preview_cheapest_hours": cheapest_preview,
        "planner_preview_free_capacity_kwh": (
            round(free_capacity_kwh, 3) if free_capacity_kwh is not None else None
        ),
        "planner_preview_replan_reason": "periodieke_observatieve_herberekening",
        "planner_preview_observational_only": True,
        "planner_preview_trading_execution_enabled": False,
        "planner_preview_losses_included": False,
        "planner_preview_assumed_max_charge_power_w": MAX_CHARGE_POWER_W,
        "planner_preview_note": (
            "Veiligheidslading is afgeleid uit alpha21. Handelsmogelijkheden zijn "
            "alleen kandidaten; verliezen en minimale netto handelsmarge volgen later."
        ),
    }
