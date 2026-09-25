from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

from .const import DEFAULT_BATTERY_CAPACITY_KWH, MIN_SOC_PERCENT

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
    charge_efficiency_percent: float,
    discharge_efficiency_percent: float,
    minimum_trade_margin: float,
    max_charge_power_w: int = 3500,
    max_discharge_power_w: int = 3500,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build an observational planner and financial trade preview.

    Alpha23 still creates no plans and performs no physical trading action.
    """
    now_utc = (now or dt_util.utcnow()).astimezone(dt_util.UTC)
    current_hour = now_utc.replace(minute=0, second=0, microsecond=0)

    charge_eff = max(0.50, min(1.00, float(charge_efficiency_percent) / 100.0))
    discharge_eff = max(0.50, min(1.00, float(discharge_efficiency_percent) / 100.0))
    roundtrip_eff = charge_eff * discharge_eff
    min_margin = max(0.0, float(minimum_trade_margin))

    valid = bool(energy_need.get("energy_need_valid"))
    need_kwh = _as_float(energy_need.get("energy_need_until_solar_kwh")) or 0.0
    reserve_kwh = _as_float(energy_need.get("energy_need_safety_reserve_kwh")) or 0.0
    additional_kwh = _as_float(energy_need.get("energy_need_additional_grid_charge_kwh"))
    tradable_kwh = _as_float(energy_need.get("energy_need_tradable_battery_kwh"))
    first_usable = _parse_time(energy_need.get("energy_need_first_usable_solar"))

    # Alpha79: this is the enforceable reserve for explicit external-control
    # discharge only. Forecast demand until usable solar is planning context and
    # must never become a fictitious self_consumption hold floor.
    required_min_soc = MIN_SOC_PERCENT + (
        reserve_kwh / DEFAULT_BATTERY_CAPACITY_KWH * 100.0
    )
    required_min_soc = max(float(MIN_SOC_PERCENT), min(100.0, required_min_soc))

    price_rows: list[dict[str, Any]] = []
    for raw in forecast:
        hour = _parse_time(raw.get("time"))
        import_price = _as_float(raw.get("import_price"))
        if import_price is None:
            import_price = _as_float(raw.get("price"))
        export_price = _as_float(raw.get("export_price"))
        if export_price is None:
            export_price = import_price
        if hour is None or import_price is None or export_price is None or hour < current_hour:
            continue
        price_rows.append(
            {
                "time": hour,
                "price": import_price,
                "import_price": import_price,
                "export_price": export_price,
                "price_source": raw.get("price_source"),
                "import_price_source": raw.get("import_price_source") or raw.get("price_source"),
                "export_price_source": raw.get("export_price_source") or raw.get("price_source"),
                "solar_kwh": _as_float(raw.get("solar_kwh")),
                "home_consumption_kwh": _as_float(raw.get("home_consumption_kwh")),
            }
        )
    price_rows.sort(key=lambda item: item["time"])

    prices = [row["import_price"] for row in price_rows]
    price_min = min(prices) if prices else None
    price_max = max(prices) if prices else None
    price_spread = (
        price_max - price_min if price_min is not None and price_max is not None else None
    )

    # Baseline physical self_consumption projection. Solar surplus charges the
    # battery, household deficit discharges it down to the technical minimum,
    # and only the remainder becomes unavoidable direct grid import.
    minimum_stored_kwh = (
        DEFAULT_BATTERY_CAPACITY_KWH * float(MIN_SOC_PERCENT) / 100.0
    )
    start_soc = (
        max(float(MIN_SOC_PERCENT), min(100.0, float(soc)))
        if soc is not None
        else float(MIN_SOC_PERCENT)
    )
    baseline_stored_kwh = DEFAULT_BATTERY_CAPACITY_KWH * start_soc / 100.0
    baseline_min_soc = start_soc
    baseline_grid_rows: list[dict[str, Any]] = []
    support_candidates: list[dict[str, Any]] = []

    for row in price_rows:
        if first_usable is not None and row["time"] >= first_usable:
            break

        fraction = 1.0
        if row["time"] == current_hour:
            elapsed = now_utc.minute / 60.0 + now_utc.second / 3600.0
            fraction = max(0.0, min(1.0, 1.0 - elapsed))

        solar = max(0.0, _as_float(row.get("solar_kwh")) or 0.0) * fraction
        home = max(0.0, _as_float(row.get("home_consumption_kwh")) or 0.0) * fraction
        solar_to_home = min(solar, home)
        solar_surplus = max(0.0, solar - solar_to_home)
        home_deficit = max(0.0, home - solar_to_home)

        charge_input_limit = max_charge_power_w / 1000.0 * fraction
        solar_charge_input = min(
            solar_surplus,
            charge_input_limit,
            max(0.0, DEFAULT_BATTERY_CAPACITY_KWH - baseline_stored_kwh) / charge_eff,
        )
        baseline_stored_kwh = min(
            DEFAULT_BATTERY_CAPACITY_KWH,
            baseline_stored_kwh + solar_charge_input * charge_eff,
        )

        # External support charging would happen after free solar but before
        # normal self_consumption household discharge in this hour.
        support_input_headroom = max(0.0, charge_input_limit - solar_charge_input)
        support_stored_headroom = min(
            support_input_headroom * charge_eff,
            max(0.0, DEFAULT_BATTERY_CAPACITY_KWH - baseline_stored_kwh),
        )
        if row["import_price"] is not None and support_stored_headroom > _MIN_ENERGY_KWH:
            support_candidates.append(
                {
                    "time": row["time"],
                    "price": row["import_price"],
                    "import_price": row["import_price"],
                    "export_price": row["export_price"],
                    "price_source": row["price_source"],
                    "remaining_stored_kwh": support_stored_headroom,
                }
            )

        available_output = max(
            0.0,
            (baseline_stored_kwh - minimum_stored_kwh) * discharge_eff,
        )
        discharge_output_limit = max_discharge_power_w / 1000.0 * fraction
        battery_to_home = min(home_deficit, discharge_output_limit, available_output)
        if battery_to_home > _MIN_ENERGY_KWH:
            baseline_stored_kwh -= battery_to_home / discharge_eff
            home_deficit -= battery_to_home

        grid_home = max(0.0, home_deficit)
        if grid_home > _MIN_ENERGY_KWH and row["import_price"] is not None:
            baseline_grid_rows.append(
                {
                    "time": row["time"],
                    "import_price": row["import_price"],
                    "grid_home_kwh": grid_home,
                }
            )
        baseline_min_soc = min(
            baseline_min_soc,
            baseline_stored_kwh / DEFAULT_BATTERY_CAPACITY_KWH * 100.0,
        )

    baseline_grid_import_kwh = sum(
        item["grid_home_kwh"] for item in baseline_grid_rows
    )
    first_min_soc_time = (
        baseline_grid_rows[0]["time"] if baseline_grid_rows else None
    )

    # Shift only genuinely unavoidable future grid import to earlier charge
    # windows when battery round-trip delivery is cheaper than buying that
    # future household energy directly. Otherwise self_consumption is allowed
    # to continue naturally down to the technical minimum.
    remaining_support_stored = max(additional_kwh or 0.0, 0.0)
    support_allocations: dict[str, dict[str, Any]] = {}
    support_savings_eur = 0.0
    for deficit in sorted(
        baseline_grid_rows,
        key=lambda item: (-item["import_price"], item["time"]),
    ):
        remaining_output = deficit["grid_home_kwh"]
        if remaining_output <= _MIN_ENERGY_KWH or remaining_support_stored <= _MIN_ENERGY_KWH:
            continue
        candidates = [
            item
            for item in support_candidates
            if item["time"] <= deficit["time"]
            and item["remaining_stored_kwh"] > _MIN_ENERGY_KWH
            and (
                item["import_price"] / (charge_eff * discharge_eff)
                < deficit["import_price"] - 1e-9
            )
        ]
        candidates.sort(
            key=lambda item: (
                item["import_price"] / (charge_eff * discharge_eff),
                item["time"],
            )
        )
        for candidate in candidates:
            if remaining_output <= _MIN_ENERGY_KWH or remaining_support_stored <= _MIN_ENERGY_KWH:
                break
            max_output = candidate["remaining_stored_kwh"] * discharge_eff
            shifted_output = min(
                remaining_output,
                max_output,
                remaining_support_stored * discharge_eff,
            )
            if shifted_output <= _MIN_ENERGY_KWH:
                continue
            stored_allocated = shifted_output / discharge_eff
            candidate["remaining_stored_kwh"] -= stored_allocated
            remaining_support_stored -= stored_allocated
            remaining_output -= shifted_output
            effective_cost = candidate["import_price"] / (charge_eff * discharge_eff)
            support_savings_eur += shifted_output * (
                deficit["import_price"] - effective_cost
            )
            key = candidate["time"].isoformat()
            allocation = support_allocations.setdefault(
                key,
                {
                    "time": key,
                    "price": candidate["import_price"],
                    "import_price": candidate["import_price"],
                    "export_price": candidate["export_price"],
                    "price_source": candidate["price_source"],
                    "candidate_battery_energy_kwh": 0.0,
                    "avoided_grid_kwh": 0.0,
                    "future_direct_import_price_max": deficit["import_price"],
                },
            )
            allocation["candidate_battery_energy_kwh"] += stored_allocated
            allocation["avoided_grid_kwh"] += shifted_output
            allocation["future_direct_import_price_max"] = max(
                allocation["future_direct_import_price_max"],
                deficit["import_price"],
            )

    selected_support_hours = sorted(
        (
            {
                **item,
                "candidate_battery_energy_kwh": round(
                    item["candidate_battery_energy_kwh"], 3
                ),
                "avoided_grid_kwh": round(item["avoided_grid_kwh"], 3),
                "future_direct_import_price_max": round(
                    item["future_direct_import_price_max"], 6
                ),
            }
            for item in support_allocations.values()
        ),
        key=lambda item: item["time"],
    )
    selected_support_stored_kwh = sum(
        item["candidate_battery_energy_kwh"] for item in selected_support_hours
    )
    support_charge_needed = bool(
        valid and additional_kwh is not None and additional_kwh > _MIN_ENERGY_KWH
    )
    support_charge_economic = selected_support_stored_kwh > _MIN_ENERGY_KWH
    support_schedule_covers_shortage = bool(
        not support_charge_needed or remaining_support_stored <= _MIN_ENERGY_KWH
    )

    # The legacy safety-charge contract no longer represents ordinary demand
    # coverage in self_consumption. Keep the fields for compatibility but empty;
    # explicit cheap support charging is published separately below.
    safety_charge_needed = False
    safety_schedule_sufficient = True
    selected_hours: list[dict[str, Any]] = []

    discharge_possible = bool(
        valid
        and tradable_kwh is not None
        and tradable_kwh > _MIN_ENERGY_KWH
        and soc is not None
        and float(soc) > required_min_soc
    )

    solar_charge_delay = bool(
        valid
        and not support_charge_needed
        and first_usable is not None
        and first_usable > now_utc
    )

    free_capacity_kwh = None
    if soc is not None:
        free_capacity_kwh = (
            DEFAULT_BATTERY_CAPACITY_KWH * max(0.0, 100.0 - float(soc)) / 100.0
        )

    # Financial pair search: buy in an earlier hour, use/sell in a later
    # more expensive hour. Cost is expressed per delivered kWh after both
    # charge and discharge losses.
    best_trade: dict[str, Any] | None = None
    for i, charge_row in enumerate(price_rows):
        effective_charge_cost = charge_row["import_price"] / roundtrip_eff
        for discharge_row in price_rows[i + 1:]:
            net_margin = discharge_row["export_price"] - effective_charge_cost
            if best_trade is None or net_margin > best_trade["net_margin"]:
                best_trade = {
                    "charge_time": charge_row["time"],
                    "charge_price": charge_row["import_price"],
                    "discharge_time": discharge_row["time"],
                    "discharge_price": discharge_row["export_price"],
                    "effective_charge_cost": effective_charge_cost,
                    "net_margin": net_margin,
                }

    trade_profitable = bool(
        best_trade is not None
        and best_trade["net_margin"] >= min_margin
        and not support_charge_needed
    )

    current_is_best_charge = bool(
        best_trade is not None and best_trade["charge_time"] == current_hour
    )
    current_is_best_discharge = bool(
        best_trade is not None and best_trade["discharge_time"] == current_hour
    )

    trade_charge_candidate = bool(
        valid
        and not support_charge_needed
        and free_capacity_kwh is not None
        and free_capacity_kwh > _MIN_ENERGY_KWH
        and trade_profitable
    )

    support_current = next(
        (
            item
            for item in selected_support_hours
            if _parse_time(item.get("time")) == current_hour
        ),
        None,
    )

    if not valid:
        decision = "wachten"
        reason = "Energiebalans is nog niet volledig geldig"
    elif support_charge_needed and support_current is not None:
        decision = "zelfconsumptie_bijladen"
        reason = (
            "Zonder ingreep ontstaat later netimport; dit uur kan die energie "
            "na laad- en ontlaadverlies goedkoper in de batterij worden gezet"
        )
    elif support_charge_needed and support_charge_economic:
        decision = "wachten"
        reason = (
            "Zelfconsumptie mag natuurlijk ontladen; een goedkoper laadvenster "
            "voor latere onvermijdelijke netimport ligt verderop"
        )
    elif support_charge_needed:
        decision = "geen_actie"
        reason = (
            "Zelfconsumptie mag tot minimum-SOC ontladen; er is geen eerder "
            "laadvenster dat na verliezen goedkoper is dan latere directe netimport"
        )
    elif current_is_best_discharge and discharge_possible and trade_profitable:
        decision = "ontladen"
        reason = (
            "Huidig uur is financieel beste ontlaaduur en energie boven reserve "
            "is beschikbaar"
        )
    elif current_is_best_charge and trade_charge_candidate and not solar_charge_delay:
        decision = "handelsladen"
        reason = (
            "Huidig uur is financieel beste laaduur en verwachte netto marge "
            "overschrijdt de ingestelde minimum handelsmarge"
        )
    elif solar_charge_delay:
        decision = "wachten"
        reason = (
            "Voldoende batterijreserve tot bruikbare zon; netladen nu uitstellen"
        )
    elif trade_profitable:
        decision = "wachten"
        reason = (
            "Financieel rendabele handelscombinatie gevonden; beste laad- of "
            "ontlaaduur ligt later"
        )
    else:
        decision = "geen_actie"
        reason = (
            "Geen veiligheidslading nodig en geen handelscombinatie voldoet aan "
            "de ingestelde netto handelsmarge"
        )

    cheapest_preview = sorted(price_rows, key=lambda item: (item["import_price"], item["time"]))[:6]
    cheapest_preview = [
        {
            "time": row["time"].isoformat(),
            "price": row["import_price"],
            "import_price": row["import_price"],
            "export_price": row["export_price"],
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
        "planner_preview_support_charge_needed": support_charge_needed,
        "planner_preview_support_charge_economic": support_charge_economic,
        "planner_preview_support_charge_kwh": round(selected_support_stored_kwh, 3),
        "planner_preview_support_charge_hours": selected_support_hours,
        "planner_preview_support_charge_hour_count": len(selected_support_hours),
        "planner_preview_support_schedule_covers_shortage": support_schedule_covers_shortage,
        "planner_preview_support_remaining_stored_kwh": round(max(remaining_support_stored, 0.0), 3),
        "planner_preview_support_expected_savings_eur": round(support_savings_eur, 4),
        "planner_preview_baseline_grid_import_kwh": round(baseline_grid_import_kwh, 3),
        "planner_preview_baseline_min_soc_percent": round(baseline_min_soc, 1),
        "planner_preview_baseline_first_min_soc_time": (
            first_min_soc_time.isoformat() if first_min_soc_time is not None else None
        ),
        "planner_preview_reserve_enforceable_in_self_consumption": False,
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
        "planner_preview_charge_efficiency_percent": round(charge_eff * 100.0, 1),
        "planner_preview_discharge_efficiency_percent": round(discharge_eff * 100.0, 1),
        "planner_preview_roundtrip_efficiency_percent": round(roundtrip_eff * 100.0, 1),
        "planner_preview_minimum_trade_margin": round(min_margin, 4),
        "planner_preview_trade_profitable": trade_profitable,
        "planner_preview_best_charge_time": (
            best_trade["charge_time"].isoformat() if best_trade else None
        ),
        "planner_preview_best_charge_price": (
            round(best_trade["charge_price"], 6) if best_trade else None
        ),
        "planner_preview_best_discharge_time": (
            best_trade["discharge_time"].isoformat() if best_trade else None
        ),
        "planner_preview_best_discharge_price": (
            round(best_trade["discharge_price"], 6) if best_trade else None
        ),
        "planner_preview_effective_charge_cost": (
            round(best_trade["effective_charge_cost"], 6) if best_trade else None
        ),
        "planner_preview_expected_trade_margin": (
            round(best_trade["net_margin"], 6) if best_trade else None
        ),
        "planner_preview_replan_reason": "periodieke_observatieve_herberekening",
        "planner_preview_observational_only": True,
        "planner_preview_trading_execution_enabled": False,
        "planner_preview_losses_included": True,
        "planner_preview_assumed_max_charge_power_w": int(max_charge_power_w),
        "planner_preview_note": (
            "Alpha79 projecteert normale self_consumption fysiek: woningontlading "
            "mag tot minimum-SOC doorlopen. Alleen latere onvermijdelijke netimport "
            "wordt naar een eerder laadvenster verschoven wanneer dat na verliezen "
            "goedkoper is. De reserve blijft context voor expliciete control-acties."
        ),
    }
