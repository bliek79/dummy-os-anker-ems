from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

PLANNER_HORIZON_HOURS = 72
QUARTERS_PER_HOUR = 4


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


def build_planner_home_forecast(
    quarter_rows: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    horizon_hours: int = PLANNER_HORIZON_HOURS,
) -> dict[str, Any]:
    """Build an exact full-clock-hour adapter for the hourly planner.

    The internal model is canonically 15-minute based and may start at :15,
    :30 or :45. Grouping that raw horizon by wall-clock hour can therefore
    create 73 buckets with partial first/last hours. The planner must never use
    those partial buckets as if they were full hours.

    This adapter deliberately starts at the next *full* UTC clock hour and
    accepts an hour only when all four 15-minute points are available.
    It remains a passive adapter; selecting it as the Plan72 source is a
    separate, explicit migration step.
    """
    now_utc = (now or dt_util.utcnow()).astimezone(dt_util.UTC)
    current_hour = now_utc.replace(minute=0, second=0, microsecond=0)
    start_hour = current_hour + timedelta(hours=1)
    requested_hours = max(1, int(horizon_hours))

    points: dict[datetime, float] = {}
    invalid_rows = 0
    for raw in quarter_rows:
        if not isinstance(raw, dict):
            invalid_rows += 1
            continue
        stamp = _parse_time(raw.get("time"))
        try:
            value = max(0.0, float(raw.get("predicted", raw.get("kwh"))))
        except (TypeError, ValueError):
            invalid_rows += 1
            continue
        if stamp is None or stamp.minute not in {0, 15, 30, 45}:
            invalid_rows += 1
            continue
        stamp = stamp.replace(second=0, microsecond=0)
        points[stamp] = value

    hourly: list[dict[str, Any]] = []
    incomplete_hours: list[str] = []
    for offset in range(requested_hours):
        hour = start_hour + timedelta(hours=offset)
        stamps = [hour + timedelta(minutes=15 * index) for index in range(QUARTERS_PER_HOUR)]
        present = [stamp for stamp in stamps if stamp in points]
        if len(present) != QUARTERS_PER_HOUR:
            incomplete_hours.append(hour.isoformat())
            continue
        value = sum(points[stamp] for stamp in stamps)
        hourly.append(
            {
                "time": hour.isoformat(),
                "home_consumption_kwh": round(value, 6),
                "source_point_count": QUARTERS_PER_HOUR,
                "source": "internal_home_forecast_15m",
            }
        )

    complete = len(hourly) == requested_hours
    return {
        "internal_home_forecast_planner_adapter_status": "ready" if complete else "incomplete",
        "internal_home_forecast_planner_adapter_ready": complete,
        "internal_home_forecast_planner_adapter_start": start_hour.isoformat(),
        "internal_home_forecast_planner_adapter_requested_hours": requested_hours,
        "internal_home_forecast_planner_adapter_complete_hours": len(hourly),
        "internal_home_forecast_planner_adapter_incomplete_hours": incomplete_hours,
        "internal_home_forecast_planner_adapter_invalid_rows": invalid_rows,
        "internal_home_forecast_planner_adapter_rows": hourly,
        "internal_home_forecast_planner_adapter_plan72_source": False,
        "internal_home_forecast_planner_adapter_note": "full_clock_hours_only_no_partial_bucket",
    }
