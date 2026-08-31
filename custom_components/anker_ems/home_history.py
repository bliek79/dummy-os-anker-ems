from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

STORAGE_VERSION = 1
RETENTION_DAYS = 42
MAX_SAMPLE_GAP_SECONDS = 120.0
QUARTER_SECONDS = 15 * 60


def _quarter_start(value: datetime) -> datetime:
    value = value.astimezone(dt_util.UTC)
    return value.replace(minute=(value.minute // 15) * 15, second=0, microsecond=0)


class AnkerEmsHomeHistory:
    """Persist canonical EMS home demand as completed 15-minute energy buckets."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}.home_history",
        )
        self._history: list[dict[str, Any]] = []
        self._current_start: datetime | None = None
        self._current_energy_kwh = 0.0
        self._current_coverage_s = 0.0
        self._current_samples = 0
        self._last_sample_at: datetime | None = None
        self._last_power_w: float | None = None
        self._latest_completed: dict[str, Any] | None = None

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return
        raw = stored.get("history")
        if not isinstance(raw, list):
            return
        clean: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            start = dt_util.parse_datetime(str(row.get("start") or ""))
            try:
                energy = float(row.get("energy_kwh"))
                coverage = float(row.get("coverage_percent"))
                sample_count = int(row.get("sample_count") or 0)
            except (TypeError, ValueError):
                continue
            if start is None:
                continue
            clean.append(
                {
                    "start": start.astimezone(dt_util.UTC).isoformat(),
                    "energy_kwh": round(max(0.0, energy), 6),
                    "coverage_percent": round(max(0.0, min(100.0, coverage)), 1),
                    "sample_count": max(0, sample_count),
                }
            )
        self._history = sorted(clean, key=lambda row: row["start"])
        self._prune(dt_util.utcnow().astimezone(dt_util.UTC))
        self._latest_completed = self._history[-1] if self._history else None

    async def _async_save(self) -> None:
        await self._store.async_save({"history": self._history})

    def _prune(self, now_utc: datetime) -> None:
        cutoff = now_utc - timedelta(days=RETENTION_DAYS)
        self._history = [
            row
            for row in self._history
            if (dt_util.parse_datetime(str(row.get("start") or "")) or now_utc) >= cutoff
        ]

    async def _async_finish_current(self, now_utc: datetime) -> None:
        if self._current_start is None:
            return
        row = {
            "start": self._current_start.isoformat(),
            "energy_kwh": round(max(0.0, self._current_energy_kwh), 6),
            "coverage_percent": round(
                max(0.0, min(100.0, self._current_coverage_s / QUARTER_SECONDS * 100.0)),
                1,
            ),
            "sample_count": self._current_samples,
        }
        self._history = [item for item in self._history if item.get("start") != row["start"]]
        self._history.append(row)
        self._history.sort(key=lambda item: item["start"])
        self._latest_completed = row
        self._prune(now_utc)
        await self._async_save()

    async def async_observe(self, power_w: float | None) -> dict[str, Any]:
        """Integrate valid canonical home power without inventing energy over data gaps."""
        now_utc = dt_util.utcnow().astimezone(dt_util.UTC)
        bucket = _quarter_start(now_utc)

        if self._current_start is None:
            self._current_start = bucket
        elif bucket != self._current_start:
            await self._async_finish_current(now_utc)
            self._current_start = bucket
            self._current_energy_kwh = 0.0
            self._current_coverage_s = 0.0
            self._current_samples = 0
            self._last_sample_at = None
            self._last_power_w = None

        numeric_power: float | None
        try:
            numeric_power = None if power_w is None else max(0.0, float(power_w))
        except (TypeError, ValueError):
            numeric_power = None

        if numeric_power is not None:
            self._current_samples += 1
            if self._last_sample_at is not None and self._last_power_w is not None:
                elapsed = (now_utc - self._last_sample_at).total_seconds()
                if 0.0 < elapsed <= MAX_SAMPLE_GAP_SECONDS:
                    average_power_w = (self._last_power_w + numeric_power) / 2.0
                    self._current_energy_kwh += average_power_w * elapsed / 3_600_000.0
                    self._current_coverage_s += elapsed
            self._last_sample_at = now_utc
            self._last_power_w = numeric_power
        else:
            self._last_sample_at = None
            self._last_power_w = None

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        latest = self._latest_completed or {}
        dates: set[str] = set()
        for row in self._history:
            parsed = dt_util.parse_datetime(str(row.get("start") or ""))
            if parsed is not None:
                dates.add(parsed.astimezone(dt_util.DEFAULT_TIME_ZONE).date().isoformat())
        covered_quarters = sum(
            1 for row in self._history if float(row.get("coverage_percent") or 0.0) >= 80.0
        )
        return {
            "home_energy_15m_kwh": latest.get("energy_kwh"),
            "home_energy_15m_status": "ready" if latest else "building_history",
            "home_energy_15m_period_start": latest.get("start"),
            "home_energy_15m_coverage_percent": latest.get("coverage_percent"),
            "home_energy_15m_sample_count": latest.get("sample_count"),
            "home_history_days": len(dates),
            "home_history_points": len(self._history),
            "home_history_covered_quarters": covered_quarters,
            "home_history_retention_days": RETENTION_DAYS,
            "home_history_interval_minutes": 15,
            "home_history_max_sample_gap_seconds": MAX_SAMPLE_GAP_SECONDS,
            "home_history_plan72_source": False,
            "home_history_forecast_source": False,
        }

    @property
    def history(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._history]
