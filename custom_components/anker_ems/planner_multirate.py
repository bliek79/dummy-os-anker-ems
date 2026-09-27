"""Alpha81 multi-rate planner runtime helpers.

This module changes planner orchestration only. The Alpha80 cheapest-energy
safety policy stays in energy_need.py, planner_preview.py and planner_72h.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .const import DEFAULT_AUTO_EXECUTION_BUFFER_PERCENT
from .energy_need import build_energy_need_analysis
from .planner_preview import build_planner_preview
from .planner_72h import build_72h_plan_preview


MULTIRATE_RUNTIME_VERSION = "alpha81_multirate_runtime_v1"
PLANNER_POLICY_VERSION = "alpha80_cheapest_energy_safety_v1"

PLANNER_TRIGGERS = frozenset(
    {
        "startup",
        "quarter_boundary",
        "source_content_changed",
        "forecast_recovered",
        "soc_recovered",
        "start_critical",
    }
)


def _as_utc(reference: datetime) -> datetime:
    if reference.tzinfo is None:
        return reference.replace(tzinfo=timezone.utc)
    return reference.astimezone(timezone.utc)


def planner_cycle_id(reference: datetime) -> str:
    """Return the native 15-minute UTC planner-cycle identity."""
    reference_utc = _as_utc(reference)
    minute = (reference_utc.minute // 15) * 15
    return reference_utc.replace(
        minute=minute,
        second=0,
        microsecond=0,
    ).isoformat()


def planner_input_signature(
    *,
    forecast: list[dict[str, Any]],
    soc: float,
    safety_reserve_percent: float,
    charge_efficiency_percent: float,
    discharge_efficiency_percent: float,
    minimum_trade_margin: float,
    max_charge_power_w: int,
    max_discharge_power_w: int,
    reference: datetime,
) -> str:
    """Hash all Alpha80 policy-relevant inputs for one native quarter.

    The exact wall-clock second is intentionally excluded. Repeated fast-path
    coordinator ticks therefore cannot start duplicate heavy planner work for
    identical content inside the same native quarter.
    """
    payload = {
        "runtime": MULTIRATE_RUNTIME_VERSION,
        "policy": PLANNER_POLICY_VERSION,
        "cycle": planner_cycle_id(reference),
        "forecast": forecast,
        "soc": float(soc),
        "settings": {
            "safety_reserve_percent": float(safety_reserve_percent),
            "charge_efficiency_percent": float(charge_efficiency_percent),
            "discharge_efficiency_percent": float(discharge_efficiency_percent),
            "minimum_trade_margin": float(minimum_trade_margin),
            "max_charge_power_w": int(max_charge_power_w),
            "max_discharge_power_w": int(max_discharge_power_w),
            "execution_buffer_percent": float(
                DEFAULT_AUTO_EXECUTION_BUFFER_PERCENT
            ),
        },
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def is_planner_trigger(trigger: str) -> bool:
    """Return whether a trigger belongs to the heavy planner lane."""
    return trigger in PLANNER_TRIGGERS


def compute_alpha80_planner_bundle(
    *,
    forecast: list[dict[str, Any]],
    soc: float,
    safety_reserve_percent: float,
    charge_efficiency_percent: float,
    discharge_efficiency_percent: float,
    minimum_trade_margin: float,
    max_charge_power_w: int,
    max_discharge_power_w: int,
    reference: datetime,
) -> dict[str, Any]:
    """Run the unchanged Alpha80 policy as one atomic planner bundle."""
    energy_need = build_energy_need_analysis(
        forecast,
        soc,
        safety_reserve_percent,
        now=reference,
    )
    planner_preview = build_planner_preview(
        forecast,
        energy_need,
        soc,
        charge_efficiency_percent,
        discharge_efficiency_percent,
        minimum_trade_margin,
        max_charge_power_w=max_charge_power_w,
        max_discharge_power_w=max_discharge_power_w,
        now=reference,
    )
    plan72 = build_72h_plan_preview(
        forecast,
        energy_need,
        planner_preview,
        soc,
        charge_efficiency_percent,
        discharge_efficiency_percent,
        execution_buffer_percent=DEFAULT_AUTO_EXECUTION_BUFFER_PERCENT,
        max_charge_power_w=max_charge_power_w,
        max_discharge_power_w=max_discharge_power_w,
        now=reference,
    )
    return {
        "energy_need": energy_need,
        "planner_preview": planner_preview,
        "plan72": plan72,
        "planner_cycle_id": planner_cycle_id(reference),
        "planner_reference": _as_utc(reference).isoformat(),
    }
