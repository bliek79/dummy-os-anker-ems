from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ForecastReadinessThresholds:
    min_history_days_shadow: int = 7
    min_history_days_candidate: int = 14
    min_history_days_leading: int = 30
    min_source_coverage_percent: float = 90.0
    min_confidence_percent_candidate: float = 25.0
    min_confidence_percent_leading: float = 50.0
    max_mean_absolute_error_kwh_15m: float = 0.08
    max_absolute_bias_kwh_per_day: float = 1.0


DEFAULT_THRESHOLDS = ForecastReadinessThresholds()


def evaluate_forecast_points(
    points: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate predicted versus actual quarter-hour demand points.

    Expected input fields per point:
    - predicted_kwh
    - actual_kwh
    Optional:
    - mode: normal | absence
    - period: night | morning | midday | afternoon | evening
    """
    usable: list[dict[str, Any]] = []
    for raw in points:
        try:
            predicted = max(0.0, float(raw.get("predicted_kwh")))
            actual = max(0.0, float(raw.get("actual_kwh")))
        except (TypeError, ValueError):
            continue
        usable.append(
            {
                "predicted_kwh": predicted,
                "actual_kwh": actual,
                "mode": str(raw.get("mode") or "normal"),
                "period": str(raw.get("period") or "unknown"),
            }
        )

    if not usable:
        return {
            "points": 0,
            "mae_kwh_15m": None,
            "mean_bias_kwh_15m": None,
            "absolute_bias_kwh_per_day": None,
            "predicted_total_kwh": 0.0,
            "actual_total_kwh": 0.0,
            "by_mode": {},
            "by_period": {},
        }

    errors = [item["predicted_kwh"] - item["actual_kwh"] for item in usable]
    mae = sum(abs(error) for error in errors) / len(errors)
    bias = sum(errors) / len(errors)
    absolute_bias_day = abs(sum(errors)) / len(errors) * 96.0

    def _group(key: str) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in usable:
            grouped.setdefault(item[key], []).append(item)
        result: dict[str, Any] = {}
        for name, rows in grouped.items():
            group_errors = [row["predicted_kwh"] - row["actual_kwh"] for row in rows]
            result[name] = {
                "points": len(rows),
                "mae_kwh_15m": round(
                    sum(abs(error) for error in group_errors) / len(group_errors), 6
                ),
                "mean_bias_kwh_15m": round(sum(group_errors) / len(group_errors), 6),
                "predicted_total_kwh": round(sum(row["predicted_kwh"] for row in rows), 3),
                "actual_total_kwh": round(sum(row["actual_kwh"] for row in rows), 3),
            }
        return result

    return {
        "points": len(usable),
        "mae_kwh_15m": round(mae, 6),
        "mean_bias_kwh_15m": round(bias, 6),
        "absolute_bias_kwh_per_day": round(absolute_bias_day, 3),
        "predicted_total_kwh": round(sum(item["predicted_kwh"] for item in usable), 3),
        "actual_total_kwh": round(sum(item["actual_kwh"] for item in usable), 3),
        "by_mode": _group("mode"),
        "by_period": _group("period"),
    }


def determine_forecast_stage(
    *,
    history_days: int,
    source_coverage_percent: float,
    confidence_percent: float,
    evaluation: dict[str, Any] | None = None,
    thresholds: ForecastReadinessThresholds = DEFAULT_THRESHOLDS,
) -> dict[str, Any]:
    """Determine the highest permitted migration stage.

    Stages are intentionally conservative:
    learning -> shadow -> candidate -> leading_ready

    This helper does not switch any source. It only reports readiness.
    """
    blockers: list[str] = []

    if history_days < thresholds.min_history_days_shadow:
        blockers.append("insufficient_history_for_shadow")
    if source_coverage_percent < thresholds.min_source_coverage_percent:
        blockers.append("source_coverage_too_low")

    if blockers:
        return {"stage": "learning", "ready": False, "blockers": blockers}

    stage = "shadow"

    candidate_blockers: list[str] = []
    if history_days < thresholds.min_history_days_candidate:
        candidate_blockers.append("insufficient_history_for_candidate")
    if confidence_percent < thresholds.min_confidence_percent_candidate:
        candidate_blockers.append("confidence_too_low_for_candidate")

    if candidate_blockers:
        return {"stage": stage, "ready": True, "blockers": candidate_blockers}

    stage = "candidate"

    leading_blockers: list[str] = []
    if history_days < thresholds.min_history_days_leading:
        leading_blockers.append("insufficient_history_for_leading")
    if confidence_percent < thresholds.min_confidence_percent_leading:
        leading_blockers.append("confidence_too_low_for_leading")

    if not evaluation or int(evaluation.get("points") or 0) <= 0:
        leading_blockers.append("no_forecast_evaluation")
    else:
        mae = evaluation.get("mae_kwh_15m")
        bias_day = evaluation.get("absolute_bias_kwh_per_day")
        if mae is None or float(mae) > thresholds.max_mean_absolute_error_kwh_15m:
            leading_blockers.append("forecast_error_too_high")
        if bias_day is None or float(bias_day) > thresholds.max_absolute_bias_kwh_per_day:
            leading_blockers.append("forecast_bias_too_high")

    if leading_blockers:
        return {"stage": stage, "ready": True, "blockers": leading_blockers}

    return {"stage": "leading_ready", "ready": True, "blockers": []}


def resolve_home_forecast_source(
    *,
    requested_source: str,
    internal_available: bool,
    internal_stage: str,
) -> dict[str, Any]:
    """Resolve source choice with safe fallback, without changing planner code.

    Accepted requested sources:
    - external
    - internal_shadow
    - internal

    Internal may only become active when readiness reached leading_ready.
    Until then external remains the active source.
    """
    requested = str(requested_source or "external").strip().lower()
    if requested not in {"external", "internal_shadow", "internal"}:
        requested = "external"

    if requested == "external":
        return {
            "active_source": "external",
            "comparison_source": "internal" if internal_available else None,
            "fallback_used": False,
            "reason": "external_requested",
        }

    if requested == "internal_shadow":
        return {
            "active_source": "external",
            "comparison_source": "internal" if internal_available else None,
            "fallback_used": not internal_available,
            "reason": "shadow_mode" if internal_available else "internal_unavailable",
        }

    if not internal_available:
        return {
            "active_source": "external",
            "comparison_source": None,
            "fallback_used": True,
            "reason": "internal_unavailable",
        }

    if internal_stage != "leading_ready":
        return {
            "active_source": "external",
            "comparison_source": "internal",
            "fallback_used": True,
            "reason": "internal_not_ready",
        }

    return {
        "active_source": "internal",
        "comparison_source": "external",
        "fallback_used": False,
        "reason": "internal_ready",
    }
