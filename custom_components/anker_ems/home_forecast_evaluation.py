from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .home_forecast_transition import evaluate_forecast_points

STORAGE_VERSION = 1
RETENTION_DAYS = 42
MIN_ACTUAL_COVERAGE_PERCENT = 80.0


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


def _period(local: datetime) -> str:
    hour = local.hour
    if hour < 6:
        return "night"
    if hour < 10:
        return "morning"
    if hour < 14:
        return "midday"
    if hour < 18:
        return "afternoon"
    return "evening"


class AnkerEmsHomeForecastEvaluation:
    """Persist shadow forecast-versus-actual quarter-hour evaluation.

    This store is deliberately diagnostic only. It never selects a forecast
    source and never feeds Energy Need, Plan72, the bridge, or execution.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.home_forecast_evaluation",
        )
        self._rows: list[dict[str, Any]] = []

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return
        raw_rows = stored.get("rows")
        if not isinstance(raw_rows, list):
            return
        clean: list[dict[str, Any]] = []
        for raw in raw_rows:
            if not isinstance(raw, dict):
                continue
            stamp = _parse_time(raw.get("time"))
            try:
                predicted = max(0.0, float(raw.get("predicted_kwh")))
                actual = max(0.0, float(raw.get("actual_kwh")))
                coverage = max(0.0, min(100.0, float(raw.get("coverage_percent"))))
            except (TypeError, ValueError):
                continue
            if stamp is None:
                continue
            clean.append(
                {
                    "time": stamp.isoformat(),
                    "predicted_kwh": round(predicted, 6),
                    "actual_kwh": round(actual, 6),
                    "coverage_percent": round(coverage, 1),
                    "mode": str(raw.get("mode") or "normal"),
                    "period": str(raw.get("period") or _period(stamp.astimezone(dt_util.DEFAULT_TIME_ZONE))),
                    "forecast_generated_at": raw.get("forecast_generated_at"),
                    "pattern_source": raw.get("pattern_source"),
                }
            )
        self._rows = sorted(clean, key=lambda row: row["time"])
        self._prune(dt_util.utcnow().astimezone(dt_util.UTC))

    async def _async_save(self) -> None:
        await self._store.async_save({"rows": self._rows})

    def _prune(self, now_utc: datetime) -> None:
        cutoff = now_utc - timedelta(days=RETENTION_DAYS)
        kept: list[dict[str, Any]] = []
        for row in self._rows:
            stamp = _parse_time(row.get("time"))
            if stamp is not None and stamp >= cutoff:
                kept.append(row)
        self._rows = kept

    async def async_observe_completed_history(
        self,
        *,
        history_rows: list[dict[str, Any]],
        forecast_snapshot: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Match completed actual quarters to predictions made beforehand.

        The caller must pass the forecast snapshot that existed before a newly
        completed history quarter caused the forecast to be rebuilt. This
        prevents hindsight evaluation against a forecast generated after the
        actual value was already known.
        """
        if not forecast_snapshot:
            return self.snapshot()

        generated_at = _parse_time(forecast_snapshot.get("internal_home_forecast_generated_at"))
        forecast_rows = forecast_snapshot.get("internal_home_forecast_forecasts")
        if not isinstance(forecast_rows, list):
            return self.snapshot()

        predicted_by_time: dict[str, dict[str, Any]] = {}
        for raw in forecast_rows:
            if not isinstance(raw, dict):
                continue
            stamp = _parse_time(raw.get("time"))
            if stamp is None:
                continue
            try:
                predicted = max(0.0, float(raw.get("predicted")))
            except (TypeError, ValueError):
                continue
            predicted_by_time[stamp.isoformat()] = {
                "predicted_kwh": predicted,
                "pattern_source": raw.get("pattern_source"),
            }

        existing_times = {str(row.get("time")) for row in self._rows}
        changed = False
        for actual_row in history_rows:
            if not isinstance(actual_row, dict):
                continue
            stamp = _parse_time(actual_row.get("start"))
            if stamp is None:
                continue
            key = stamp.isoformat()
            if key in existing_times or key not in predicted_by_time:
                continue
            try:
                actual = max(0.0, float(actual_row.get("energy_kwh")))
                coverage = max(0.0, min(100.0, float(actual_row.get("coverage_percent"))))
            except (TypeError, ValueError):
                continue
            if coverage < MIN_ACTUAL_COVERAGE_PERCENT:
                continue
            # A valid shadow comparison must have been generated before the
            # actual quarter began. This makes the metric forward-looking.
            if generated_at is not None and generated_at >= stamp:
                continue
            predicted = predicted_by_time[key]
            local = stamp.astimezone(dt_util.DEFAULT_TIME_ZONE)
            self._rows.append(
                {
                    "time": key,
                    "predicted_kwh": round(float(predicted["predicted_kwh"]), 6),
                    "actual_kwh": round(actual, 6),
                    "coverage_percent": round(coverage, 1),
                    "mode": str(actual_row.get("mode") or "normal"),
                    "period": _period(local),
                    "forecast_generated_at": (
                        generated_at.isoformat() if generated_at is not None else None
                    ),
                    "pattern_source": predicted.get("pattern_source"),
                }
            )
            existing_times.add(key)
            changed = True

        if changed:
            self._rows.sort(key=lambda row: row["time"])
            self._prune(dt_util.utcnow().astimezone(dt_util.UTC))
            await self._async_save()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        evaluation = evaluate_forecast_points(self._rows)
        first = self._rows[0]["time"] if self._rows else None
        last = self._rows[-1]["time"] if self._rows else None
        return {
            "internal_home_forecast_evaluation_status": (
                "collecting" if self._rows else "waiting_for_forward_predictions"
            ),
            "internal_home_forecast_evaluation_points": evaluation.get("points", 0),
            "internal_home_forecast_evaluation_mae_kwh_15m": evaluation.get("mae_kwh_15m"),
            "internal_home_forecast_evaluation_mean_bias_kwh_15m": evaluation.get("mean_bias_kwh_15m"),
            "internal_home_forecast_evaluation_absolute_bias_kwh_per_day": evaluation.get("absolute_bias_kwh_per_day"),
            "internal_home_forecast_evaluation_predicted_total_kwh": evaluation.get("predicted_total_kwh"),
            "internal_home_forecast_evaluation_actual_total_kwh": evaluation.get("actual_total_kwh"),
            "internal_home_forecast_evaluation_by_mode": evaluation.get("by_mode", {}),
            "internal_home_forecast_evaluation_by_period": evaluation.get("by_period", {}),
            "internal_home_forecast_evaluation_first_point": first,
            "internal_home_forecast_evaluation_last_point": last,
            "internal_home_forecast_evaluation_retention_days": RETENTION_DAYS,
            "internal_home_forecast_evaluation_min_actual_coverage_percent": MIN_ACTUAL_COVERAGE_PERCENT,
            "internal_home_forecast_evaluation_shadow_only": True,
            "internal_home_forecast_evaluation_plan72_source": False,
            "internal_home_forecast_evaluation_rows": [dict(row) for row in self._rows],
        }

    @property
    def rows(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._rows]
