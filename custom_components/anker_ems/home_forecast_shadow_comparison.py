from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util


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
    return parsed.astimezone(dt_util.UTC).replace(minute=0, second=0, microsecond=0)


def _hourly_map(rows: list[dict[str, Any]], value_keys: tuple[str, ...]) -> dict[datetime, float]:
    result: dict[datetime, float] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        stamp = _parse_time(raw.get("time") or raw.get("timestamp") or raw.get("start"))
        if stamp is None:
            continue
        value = None
        for key in value_keys:
            try:
                candidate = raw.get(key)
                if candidate not in (None, ""):
                    value = max(0.0, float(candidate))
                    break
            except (TypeError, ValueError):
                continue
        if value is not None:
            result[stamp] = value
    return result


def compare_home_forecasts(
    *,
    external_rows: list[dict[str, Any]],
    internal_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare external and internal hourly forecasts without selecting either.

    This is intentionally a shadow-only diagnostic. It compares only matching
    full clock hours and does not feed Energy Need, Plan72, bridge, or execution.
    """
    external = _hourly_map(
        external_rows,
        ("home_consumption_kwh", "predicted", "kwh", "value"),
    )
    internal = _hourly_map(
        internal_rows,
        ("home_consumption_kwh", "predicted", "kwh", "value"),
    )
    common = sorted(set(external) & set(internal))

    rows: list[dict[str, Any]] = []
    differences: list[float] = []
    absolute_differences: list[float] = []
    for stamp in common:
        ext = external[stamp]
        inte = internal[stamp]
        delta = inte - ext
        differences.append(delta)
        absolute_differences.append(abs(delta))
        rows.append(
            {
                "time": stamp.isoformat(),
                "external_kwh": round(ext, 6),
                "internal_kwh": round(inte, 6),
                "delta_kwh": round(delta, 6),
                "absolute_delta_kwh": round(abs(delta), 6),
            }
        )

    matched = len(common)
    external_total = sum(external[stamp] for stamp in common)
    internal_total = sum(internal[stamp] for stamp in common)
    mae = sum(absolute_differences) / matched if matched else None
    bias = sum(differences) / matched if matched else None
    coverage_percent = (
        matched / max(len(external), len(internal), 1) * 100.0
        if external or internal
        else 0.0
    )

    return {
        "home_forecast_shadow_comparison_status": "ready" if matched else "waiting_for_overlap",
        "home_forecast_shadow_comparison_matched_hours": matched,
        "home_forecast_shadow_comparison_external_hours": len(external),
        "home_forecast_shadow_comparison_internal_hours": len(internal),
        "home_forecast_shadow_comparison_overlap_percent": round(coverage_percent, 1),
        "home_forecast_shadow_comparison_mae_kwh_hour": (
            round(mae, 6) if mae is not None else None
        ),
        "home_forecast_shadow_comparison_mean_bias_kwh_hour": (
            round(bias, 6) if bias is not None else None
        ),
        "home_forecast_shadow_comparison_external_total_kwh": round(external_total, 3),
        "home_forecast_shadow_comparison_internal_total_kwh": round(internal_total, 3),
        "home_forecast_shadow_comparison_total_delta_kwh": round(
            internal_total - external_total, 3
        ),
        "home_forecast_shadow_comparison_rows": rows,
        "home_forecast_shadow_comparison_shadow_only": True,
        "home_forecast_shadow_comparison_plan72_source": False,
    }
