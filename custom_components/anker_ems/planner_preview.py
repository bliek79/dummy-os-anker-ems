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

    # The compact safety contract is the existing technical minimum plus the
    # configured software reserve. Forecast demand remains planning context and
    # must not become a fictitious self_consumption hold floor.
    required_min_soc = MIN_SOC_PERCENT + (
        reserve_kwh / DEFAULT_BATTERY_CAPACITY_KWH * 100.0
    )
    required_min_soc = max(float(MIN_SOC_PERCENT), min(100.0, required_min_soc))
    if soc is not None:
        tradable_kwh = max(
            0.0,
            DEFAULT_BATTERY_CAPACITY_KWH
            * (min(100.0, float(soc)) - required_min_soc)
            / 100.0,
        )

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

    # Alpha80 cheapest-energy safety planner.
    #
    # Solar remains first priority. Normal self_consumption is projected down to
    # the technical device minimum. Whenever that rolling projection would end
    # an hour below technical minimum + software reserve, the planner looks back
    # over all technically feasible charge windows up to that deadline and buys
    # the required stored energy in the cheapest window. The complete 72-hour
    # route is then recalculated and the process repeats. This allows a later,
    # cheaper window to beat an earlier cheap window when the battery can safely
    # reach it, and allows a cheap window to fill to 100% when that is required
    # to bridge a later expensive period.
    minimum_stored_kwh = (
        DEFAULT_BATTERY_CAPACITY_KWH * float(MIN_SOC_PERCENT) / 100.0
    )
    reserve_target_stored_kwh = min(
        DEFAULT_BATTERY_CAPACITY_KWH,
        minimum_stored_kwh + reserve_kwh,
    )
    start_soc = (
        max(float(MIN_SOC_PERCENT), min(100.0, float(soc)))
        if soc is not None
        else float(MIN_SOC_PERCENT)
    )
    start_stored_kwh = DEFAULT_BATTERY_CAPACITY_KWH * start_soc / 100.0

    def _fraction(hour: datetime) -> float:
        if hour != current_hour:
            return 1.0
        elapsed = now_utc.minute / 60.0 + now_utc.second / 3600.0
        return max(0.0, min(1.0, 1.0 - elapsed))

    def _simulate_safety(
        schedule_stored_kwh: dict[str, float],
    ) -> list[dict[str, Any]]:
        stored_kwh = start_stored_kwh
        trace: list[dict[str, Any]] = []
        for row in price_rows:
            fraction = _fraction(row["time"])
            solar = max(0.0, _as_float(row.get("solar_kwh")) or 0.0) * fraction
            home = max(0.0, _as_float(row.get("home_consumption_kwh")) or 0.0) * fraction
            solar_to_home = min(solar, home)
            solar_surplus = max(0.0, solar - solar_to_home)
            home_deficit = max(0.0, home - solar_to_home)

            charge_input_limit = max_charge_power_w / 1000.0 * fraction
            discharge_output_limit = max_discharge_power_w / 1000.0 * fraction

            solar_charge_input = min(
                solar_surplus,
                charge_input_limit,
                max(0.0, DEFAULT_BATTERY_CAPACITY_KWH - stored_kwh) / charge_eff,
            )
            stored_kwh = min(
                DEFAULT_BATTERY_CAPACITY_KWH,
                stored_kwh + solar_charge_input * charge_eff,
            )
            available_charge_input = max(0.0, charge_input_limit - solar_charge_input)

            maximum_safety_stored = min(
                available_charge_input * charge_eff,
                max(0.0, DEFAULT_BATTERY_CAPACITY_KWH - stored_kwh),
            )
            key = row["time"].isoformat()
            requested_safety_stored = max(
                0.0,
                _as_float(schedule_stored_kwh.get(key)) or 0.0,
            )
            actual_safety_stored = min(
                requested_safety_stored,
                maximum_safety_stored,
            )
            stored_kwh += actual_safety_stored

            available_output = max(
                0.0,
                (stored_kwh - minimum_stored_kwh) * discharge_eff,
            )
            battery_to_home = min(
                home_deficit,
                discharge_output_limit,
                available_output,
            )
            if battery_to_home > _MIN_ENERGY_KWH:
                stored_kwh -= battery_to_home / discharge_eff
                home_deficit -= battery_to_home

            grid_home = max(0.0, home_deficit)
            trace.append(
                {
                    "time": row["time"],
                    "import_price": row["import_price"],
                    "export_price": row["export_price"],
                    "price_source": row["price_source"],
                    "stored_end_kwh": stored_kwh,
                    "soc_end": stored_kwh / DEFAULT_BATTERY_CAPACITY_KWH * 100.0,
                    "grid_home_kwh": grid_home,
                    "solar_charge_input_kwh": solar_charge_input,
                    "maximum_safety_stored_kwh": maximum_safety_stored,
                    "actual_safety_stored_kwh": actual_safety_stored,
                    "remaining_safety_stored_headroom_kwh": max(
                        0.0,
                        maximum_safety_stored - actual_safety_stored,
                    ),
                }
            )
        return trace

    safety_schedule: dict[str, float] = {}
    initial_trace = _simulate_safety(safety_schedule)
    initial_breach_count = sum(
        1
        for item in initial_trace
        if item["stored_end_kwh"] < reserve_target_stored_kwh - _MIN_ENERGY_KWH
    )

    max_iterations = max(1, len(price_rows) * 4)
    for _ in range(max_iterations):
        trace = _simulate_safety(safety_schedule)
        breach_index = next(
            (
                index
                for index, item in enumerate(trace)
                if item["stored_end_kwh"]
                < reserve_target_stored_kwh - _MIN_ENERGY_KWH
            ),
            None,
        )
        if breach_index is None:
            break

        breach_stored = trace[breach_index]["stored_end_kwh"]
        required_improvement = reserve_target_stored_kwh - breach_stored
        candidates = [
            index
            for index, item in enumerate(trace[: breach_index + 1])
            if item["import_price"] is not None
            and item["remaining_safety_stored_headroom_kwh"] > _MIN_ENERGY_KWH
        ]
        # Same efficiency applies to every candidate, therefore import price is
        # sufficient for ordering. For equal prices prefer the latest window:
        # that preserves headroom for free solar and keeps the plan flexible.
        candidates.sort(
            key=lambda index: (
                trace[index]["import_price"],
                -trace[index]["time"].timestamp(),
            )
        )

        allocation_made = False
        for candidate_index in candidates:
            candidate = trace[candidate_index]
            maximum_add = candidate["remaining_safety_stored_headroom_kwh"]
            key = candidate["time"].isoformat()
            existing = safety_schedule.get(key, 0.0)

            trial_schedule = dict(safety_schedule)
            trial_schedule[key] = existing + maximum_add
            trial_trace = _simulate_safety(trial_schedule)
            maximum_improvement = (
                trial_trace[breach_index]["stored_end_kwh"] - breach_stored
            )
            if maximum_improvement <= _MIN_ENERGY_KWH:
                continue

            allocation = maximum_add
            if maximum_improvement > required_improvement + _MIN_ENERGY_KWH:
                low = 0.0
                high = maximum_add
                for _binary in range(18):
                    mid = (low + high) / 2.0
                    probe_schedule = dict(safety_schedule)
                    probe_schedule[key] = existing + mid
                    probe_trace = _simulate_safety(probe_schedule)
                    improvement = (
                        probe_trace[breach_index]["stored_end_kwh"] - breach_stored
                    )
                    if improvement >= required_improvement:
                        high = mid
                    else:
                        low = mid
                allocation = high

            if allocation <= _MIN_ENERGY_KWH:
                continue
            safety_schedule[key] = existing + allocation
            allocation_made = True
            break

        if not allocation_made:
            break

    final_trace = _simulate_safety(safety_schedule)
    final_breaches = [
        item
        for item in final_trace
        if item["stored_end_kwh"] < reserve_target_stored_kwh - _MIN_ENERGY_KWH
    ]
    selected_hours: list[dict[str, Any]] = []
    for item in final_trace:
        stored = item["actual_safety_stored_kwh"]
        if stored <= _MIN_ENERGY_KWH:
            continue
        selected_hours.append(
            {
                "time": item["time"].isoformat(),
                "price": item["import_price"],
                "import_price": item["import_price"],
                "export_price": item["export_price"],
                "price_source": item["price_source"],
                "max_battery_energy_kwh": round(
                    item["maximum_safety_stored_kwh"], 3
                ),
                "candidate_battery_energy_kwh": round(stored, 3),
                "effective_delivered_cost": round(
                    item["import_price"] / roundtrip_eff, 6
                ),
            }
        )

    selected_safety_stored_kwh = sum(
        item["actual_safety_stored_kwh"] for item in final_trace
    )
    safety_charge_needed = bool(initial_breach_count)
    safety_schedule_sufficient = not final_breaches
    safety_first_breach_time = next(
        (
            item["time"]
            for item in initial_trace
            if item["stored_end_kwh"]
            < reserve_target_stored_kwh - _MIN_ENERGY_KWH
        ),
        None,
    )
    current_safety_hour = next(
        (
            item
            for item in selected_hours
            if _parse_time(item.get("time")) == current_hour
        ),
        None,
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
        and not safety_charge_needed
    )

    current_is_best_charge = bool(
        best_trade is not None and best_trade["charge_time"] == current_hour
    )
    current_is_best_discharge = bool(
        best_trade is not None and best_trade["discharge_time"] == current_hour
    )

    trade_charge_candidate = bool(
        valid
        and not safety_charge_needed
        and free_capacity_kwh is not None
        and free_capacity_kwh > _MIN_ENERGY_KWH
        and trade_profitable
    )

    if not valid:
        decision = "wachten"
        reason = "Energiebalans is nog niet volledig geldig"
    elif safety_charge_needed:
        if current_safety_hour is not None:
            decision = "veiligheidsladen"
            reason = (
                "De 72-uurs SOC-route dreigt onder de 5%+7% planningsmarge te "
                "komen; het huidige uur is een geselecteerd goedkoop veiligheidslaadvenster"
            )
        elif selected_hours:
            decision = "wachten"
            reason = (
                "De 72-uurs SOC-route vraagt veiligheidslading; een goedkoper "
                "technisch haalbaar laadvenster ligt later"
            )
        else:
            decision = "wachten"
            reason = (
                "De 72-uurs SOC-route dreigt onder de planningsmarge te komen, "
                "maar de beschikbare laadvensters zijn technisch onvoldoende"
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
        "planner_preview_safety_charge_kwh": round(selected_safety_stored_kwh, 3),
        "planner_preview_safety_charge_hours": selected_hours,
        "planner_preview_safety_charge_hour_count": len(selected_hours),
        "planner_preview_safety_schedule_sufficient": safety_schedule_sufficient,
        "planner_preview_safety_reserve_target_soc": round(required_min_soc, 1),
        "planner_preview_safety_first_breach_time": (
            safety_first_breach_time.isoformat()
            if safety_first_breach_time is not None
            else None
        ),
        "planner_preview_safety_initial_breach_count": initial_breach_count,
        "planner_preview_safety_remaining_breach_count": len(final_breaches),
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
            "Alpha80 gebruikt de bestaande categorie veiligheidsladen voor de "
            "goedkoopste technisch haalbare energie om de rollende 72-uurs "
            "self_consumption-route boven 5%+7% planningsmarge te houden. Solar "
            "blijft eerste bron; er is geen extra laadtype of publieke sensor."
        ),
    }
