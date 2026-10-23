"""Fail-closed adapter from planned charge watts to the live HA Number limit.

The Anker SOLIX can lower the allowed number.max dynamically at low SOC.
The planner cap is a separate upper bound; this module NEVER increases it.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite
from typing import Any, Mapping


@dataclass(frozen=True)
class ChargePowerDecision:
    planned_w: int
    applied_w: int
    battery_min_w: float
    battery_max_w: float
    step_w: float | None

    @property
    def limited(self) -> bool:
        return self.applied_w < self.planned_w


def choose_charge_power(
    planned_w: int,
    attributes: Mapping[str, Any],
    *,
    configured_max_w: int,
    minimum_control_w: int = 100,
) -> ChargePowerDecision:
    """Select the largest valid integral watt setpoint without exceeding limits.

    No fallback is permitted for missing or invalid live maximum metadata.
    NumberEntity min and step are respected when the integration reports them.
    """
    def finite(name: str, raw: Any) -> float:
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError) as err:
            raise ValueError(f"Anker number.{name} ontbreekt of is ongeldig") from err
        if not isfinite(value):
            raise ValueError(f"Anker number.{name} is niet eindig")
        return value

    requested = int(planned_w)
    cap = int(configured_max_w)
    if requested < minimum_control_w or cap < minimum_control_w or requested > cap:
        raise ValueError("Planvermogen is buiten de geconfigureerde EMS-veiligheidslimiet")
    if "max" not in attributes:
        raise ValueError("Live Anker-laadmaximum ontbreekt; niet blind terugvallen")
    battery_max = finite("max", attributes["max"])
    battery_min = finite("min", attributes.get("min", 0))
    if battery_min < 0 or battery_max < battery_min:
        raise ValueError("Anker-laadgrenzen zijn ongeldig")

    step = None
    if attributes.get("step") is not None:
        step = finite("step", attributes["step"])
        if step <= 0:
            raise ValueError("Anker laadvermogensstap is ongeldig")

    allowed = float(min(requested, cap, floor(battery_max)))
    if step is not None:
        allowed = battery_min + floor((allowed - battery_min) / step + 1e-9) * step
    result = floor(allowed + 1e-9)
    if result < minimum_control_w or result < battery_min or result > battery_max:
        raise ValueError("Geen geldig laadvermogen binnen de actuele batterijgrens")
    return ChargePowerDecision(requested, int(result), battery_min, battery_max, step)
