from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from homeassistant.util import dt as dt_util

HORIZON_QUARTERS = 72 * 4
MIN_SOURCE_COVERAGE_PERCENT = 80.0
MIN_READY_HISTORY_DAYS = 7
QUARTERS_PER_DAY = 96


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


def _quarter_index(local_time: datetime) -> int:
    return local_time.hour * 4 + local_time.minute // 15


def _day_type(local_time: datetime) -> str:
    return "weekend" if local_time.weekday() >= 5 else "weekday"


def _weighted_quantile(values: list[tuple[float, float]], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values, key=lambda item: item[0])
    total_weight = sum(max(0.0, weight) for _value, weight in ordered)
    if total_weight <= 0:
        return median(value for value, _weight in ordered)
    threshold = total_weight * max(0.0, min(1.0, quantile))
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += max(0.0, weight)
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def _history_rows(history: list[dict[str, Any]], now_utc: datetime) -> list[dict[str, Any]]:
    parsed_rows: list[dict[str, Any]] = []
    for raw in history:
        start = _parse_time(raw.get("start"))
        try:
            energy_kwh = max(0.0, float(raw.get("energy_kwh")))
            coverage = max(0.0, min(100.0, float(raw.get("coverage_percent"))))
        except (TypeError, ValueError):
            continue
        if start is None or start > now_utc or coverage < MIN_SOURCE_COVERAGE_PERCENT:
            continue
        local = start.astimezone(dt_util.DEFAULT_TIME_ZONE)
        parsed_rows.append(
            {
                "start": start,
                "local": local,
                "energy_kwh": energy_kwh,
                "coverage_percent": coverage,
                "quarter_index": _quarter_index(local),
                "weekday": local.weekday(),
                "day_type": _day_type(local),
            }
        )
    parsed_rows.sort(key=lambda item: item["start"])
    return parsed_rows


def _source_coverage(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    first = rows[0]["start"]
    last = rows[-1]["start"]
    expected = max(1, int((last - first).total_seconds() // 900) + 1)
    return min(100.0, len(rows) / expected * 100.0)


def _predict_quarter(
    target_local: datetime,
    rows_by_quarter: dict[int, list[dict[str, Any]]],
    all_rows: list[dict[str, Any]],
    now_utc: datetime,
) -> tuple[float, int, str, float]:
    qidx = _quarter_index(target_local)
    candidates = list(rows_by_quarter.get(qidx, []))
    source_kind = "same_quarter"

    same_weekday = [row for row in candidates if row["weekday"] == target_local.weekday()]
    same_day_type = [row for row in candidates if row["day_type"] == _day_type(target_local)]
    if len(same_weekday) >= 2:
        selected = same_weekday
        source_kind = "same_weekday_quarter"
    elif len(same_day_type) >= 2:
        selected = same_day_type
        source_kind = "same_daytype_quarter"
    elif candidates:
        selected = candidates
    else:
        selected = []
        for distance in (1, 2, 3, 4):
            nearby: list[dict[str, Any]] = []
            for offset in (-distance, distance):
                nearby.extend(rows_by_quarter.get((qidx + offset) % QUARTERS_PER_DAY, []))
            nearby_same_type = [
                row for row in nearby if row["day_type"] == _day_type(target_local)
            ]
            if nearby_same_type:
                selected = nearby_same_type
                source_kind = f"nearby_quarter_{distance}"
                break
            if nearby:
                selected = nearby
                source_kind = f"nearby_quarter_{distance}_all_days"
                break

    if not selected:
        if not all_rows:
            return 0.0, 0, "no_history", 0.0
        fallback = median(row["energy_kwh"] for row in all_rows)
        return max(0.0, fallback), 0, "global_median", 0.05

    weighted: list[tuple[float, float]] = []
    for row in selected:
        age_days = max(0.0, (now_utc - row["start"]).total_seconds() / 86400.0)
        recency_weight = 0.92 ** min(age_days, 42.0)
        coverage_weight = row["coverage_percent"] / 100.0
        weekday_weight = 1.25 if row["weekday"] == target_local.weekday() else 1.0
        daytype_weight = 1.10 if row["day_type"] == _day_type(target_local) else 0.80
        weighted.append(
            (
                row["energy_kwh"],
                recency_weight * coverage_weight * weekday_weight * daytype_weight,
            )
        )

    robust_center = _weighted_quantile(weighted, 0.50)
    upper_pattern = _weighted_quantile(weighted, 0.75)
    prediction = max(0.0, robust_center * 0.75 + upper_pattern * 0.25)
    support = len(selected)
    support_score = min(1.0, support / 7.0)
    recency_days = min(
        max(0.0, (now_utc - row["start"]).total_seconds() / 86400.0)
        for row in selected
    )
    recency_score = max(0.2, 1.0 - min(recency_days, 21.0) / 26.25)
    confidence = min(1.0, (0.25 + 0.75 * support_score) * recency_score)
    return prediction, support, source_kind, confidence


def build_internal_home_forecast(
    history: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a 72-hour, 15-minute EMS-owned home demand forecast.

    Alpha71 is deliberately parallel/shadow. The output is diagnostic
    only and is not injected into the existing Home Forecast / Plan72
    source path.
    """
    now_utc = (now or dt_util.utcnow()).astimezone(dt_util.UTC)
    rows = _history_rows(history, now_utc)
    local_dates = {row["local"].date().isoformat() for row in rows}
    history_days = len(local_dates)
    source_coverage = _source_coverage(rows)

    rows_by_quarter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_quarter[row["quarter_index"]].append(row)

    current_quarter = now_utc.replace(
        minute=(now_utc.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    forecast_start = current_quarter + timedelta(minutes=15)
    forecast_rows: list[dict[str, Any]] = []
    confidence_values: list[float] = []
    direct_pattern_count = 0
    fallback_count = 0

    for index in range(HORIZON_QUARTERS):
        target_utc = forecast_start + timedelta(minutes=15 * index)
        target_local = target_utc.astimezone(dt_util.DEFAULT_TIME_ZONE)
        predicted, support, source_kind, row_confidence = _predict_quarter(
            target_local,
            rows_by_quarter,
            rows,
            now_utc,
        )
        if source_kind.startswith("same_"):
            direct_pattern_count += 1
        elif source_kind in {"global_median", "no_history"}:
            fallback_count += 1
        confidence_values.append(row_confidence)
        forecast_rows.append(
            {
                "time": target_utc.isoformat(),
                "predicted": round(predicted, 6),
                "kwh": round(predicted, 6),
                "support_samples": support,
                "pattern_source": source_kind,
                "confidence_percent": round(row_confidence * 100.0, 1),
            }
        )

    hourly_map: dict[datetime, float] = defaultdict(float)
    hourly_points: dict[datetime, int] = defaultdict(int)
    for row in forecast_rows:
        stamp = _parse_time(row["time"])
        if stamp is None:
            continue
        hour = stamp.replace(minute=0, second=0, microsecond=0)
        hourly_map[hour] += float(row["predicted"])
        hourly_points[hour] += 1
    hourly_forecast = [
        {
            "time": hour.isoformat(),
            "predicted": round(hourly_map[hour], 6),
            "kwh": round(hourly_map[hour], 6),
            "source_point_count": hourly_points[hour],
            "forecast_granularity": "internal_15m_sum",
        }
        for hour in sorted(hourly_map)
    ]

    raw_confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else 0.0
    )
    history_depth_factor = min(1.0, history_days / 14.0)
    confidence_percent = min(
        100.0,
        raw_confidence * history_depth_factor * (source_coverage / 100.0) * 100.0,
    )
    pattern_coverage_percent = (
        direct_pattern_count / HORIZON_QUARTERS * 100.0
        if HORIZON_QUARTERS
        else 0.0
    )
    if not rows:
        status = "waiting_for_history"
    elif history_days < MIN_READY_HISTORY_DAYS:
        status = "learning"
    else:
        status = "ready"

    return {
        "internal_home_forecast_status": status,
        "internal_home_forecast_total_72h_kwh": round(
            sum(float(row["predicted"]) for row in forecast_rows), 3
        ),
        "internal_home_forecast_coverage_percent": round(source_coverage, 1),
        "internal_home_forecast_confidence_percent": round(confidence_percent, 1),
        "internal_home_forecast_pattern_coverage_percent": round(pattern_coverage_percent, 1),
        "internal_home_forecast_generated_at": now_utc.isoformat(),
        "internal_home_forecast_horizon_hours": 72,
        "internal_home_forecast_resolution_minutes": 15,
        "internal_home_forecast_history_days": history_days,
        "internal_home_forecast_history_points": len(rows),
        "internal_home_forecast_direct_pattern_quarters": direct_pattern_count,
        "internal_home_forecast_fallback_quarters": fallback_count,
        "internal_home_forecast_model": "weighted_time_pattern_v1",
        "internal_home_forecast_min_source_coverage_percent": MIN_SOURCE_COVERAGE_PERCENT,
        "internal_home_forecast_min_ready_history_days": MIN_READY_HISTORY_DAYS,
        "internal_home_forecast_forecasts": forecast_rows,
        "internal_home_forecast_hourly": hourly_forecast,
        "internal_home_forecast_shadow_only": True,
        "internal_home_forecast_plan72_source": False,
    }
