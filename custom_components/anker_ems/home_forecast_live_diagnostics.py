from __future__ import annotations

from copy import deepcopy
from typing import Any

from .home_forecast_planner_adapter import build_planner_home_forecast
from .home_forecast_shadow_comparison import compare_home_forecasts
from .home_forecast_transition import determine_forecast_stage, resolve_home_forecast_source
from .home_presence_profile import profile_decision


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, dict)]


def build_home_forecast_live_diagnostics(
    *,
    internal_forecast: dict[str, Any] | None,
    external_hourly_rows: list[dict[str, Any]] | None,
    evaluation: dict[str, Any] | None,
    presence_source_value: Any = None,
    presence_source_configured: bool = False,
    requested_source: str = "external",
) -> dict[str, Any]:
    """Assemble all Home Forecast migration diagnostics in one passive payload.

    This helper deliberately has no access to the scheduler, Energy Need,
    Plan72, plan store or execution controller. It can therefore be wired into
    the coordinator later without giving the diagnostic layer authority over
    the active forecast source.
    """
    internal = dict(internal_forecast or {})
    quarter_rows = _rows(internal.get("internal_home_forecast_forecasts"))
    planner_adapter = build_planner_home_forecast(quarter_rows)

    comparison = compare_home_forecasts(
        external_rows=_rows(external_hourly_rows),
        internal_rows=_rows(planner_adapter.get("internal_home_forecast_planner_adapter_rows")),
    )

    history_days = int(internal.get("internal_home_forecast_history_days") or 0)
    coverage = float(internal.get("internal_home_forecast_coverage_percent") or 0.0)
    confidence = float(internal.get("internal_home_forecast_confidence_percent") or 0.0)
    readiness = determine_forecast_stage(
        history_days=history_days,
        source_coverage_percent=coverage,
        confidence_percent=confidence,
        evaluation=evaluation,
    )

    internal_available = bool(
        quarter_rows
        and planner_adapter.get("internal_home_forecast_planner_adapter_ready") is True
    )
    source_decision = resolve_home_forecast_source(
        requested_source=requested_source,
        internal_available=internal_available,
        internal_stage=str(readiness.get("stage") or "learning"),
    )
    presence = profile_decision(
        source_value=presence_source_value,
        source_configured=presence_source_configured,
    )

    return {
        "home_forecast_live_diagnostics_status": "ready",
        "home_forecast_live_diagnostics_shadow_only": True,
        "home_forecast_live_diagnostics_plan72_source": False,
        "home_forecast_live_diagnostics_active_source_unchanged": True,
        "home_forecast_live_diagnostics_requested_source": requested_source,
        "home_forecast_live_diagnostics_stage": readiness.get("stage"),
        "home_forecast_live_diagnostics_ready": readiness.get("ready", False),
        "home_forecast_live_diagnostics_blockers": list(readiness.get("blockers") or []),
        "home_forecast_live_diagnostics_source_decision": deepcopy(source_decision),
        "home_forecast_live_diagnostics_presence": deepcopy(presence),
        "home_forecast_live_diagnostics_evaluation": deepcopy(evaluation or {}),
        "home_forecast_live_diagnostics_comparison": deepcopy(comparison),
        "home_forecast_live_diagnostics_planner_adapter": deepcopy(planner_adapter),
        "home_forecast_live_diagnostics_dashboard": {
            "forecast_series": list(comparison.get("home_forecast_shadow_comparison_rows") or []),
            "matched_hours": comparison.get("home_forecast_shadow_comparison_matched_hours", 0),
            "overlap_percent": comparison.get("home_forecast_shadow_comparison_overlap_percent", 0.0),
            "mae_kwh_hour": comparison.get("home_forecast_shadow_comparison_mae_kwh_hour"),
            "mean_bias_kwh_hour": comparison.get("home_forecast_shadow_comparison_mean_bias_kwh_hour"),
            "external_total_kwh": comparison.get("home_forecast_shadow_comparison_external_total_kwh"),
            "internal_total_kwh": comparison.get("home_forecast_shadow_comparison_internal_total_kwh"),
            "total_delta_kwh": comparison.get("home_forecast_shadow_comparison_total_delta_kwh"),
        },
        "home_forecast_live_diagnostics_note": (
            "Passive migration diagnostics only; active external Home Forecast remains authoritative."
        ),
    }
