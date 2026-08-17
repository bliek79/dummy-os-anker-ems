from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .plan_store import AnkerEmsPlanStore
from .scheduler import AnkerEmsScheduler

from .const import (
    NAME,
    CONF_SIMULATION_MODE,
    CONF_SOC_ENTITY,
    CONF_DEVICE_STATUS_ENTITY,
    CONF_CHARGE_POWER_ENTITY,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_GRID_IMPORT_POWER_ENTITY,
    CONF_GRID_EXPORT_POWER_ENTITY,
    CONF_OPERATING_MODE_ENTITY,
    CONF_ACTION_DIRECTION_ENTITY,
    CONF_POWER_SETPOINT_ENTITY,
    CONF_KNOWN_PRICE_ENTITY,
    CONF_FORECAST_PRICE_ENTITY,
    CONF_HOME_FORECAST_ENTITY,
    CONF_SOLAR_TODAY_ENTITY,
    CONF_SOLAR_TOMORROW_ENTITY,
    CONF_SOLAR_DAY3_ENTITY,
    DEFAULT_KNOWN_PRICE_ENTITY,
    DEFAULT_FORECAST_PRICE_ENTITY,
    DEFAULT_HOME_FORECAST_ENTITY,
    DEFAULT_SOLAR_TODAY_ENTITY,
    DEFAULT_SOLAR_TOMORROW_ENTITY,
    DEFAULT_SOLAR_DAY3_ENTITY,
    FORECAST_HORIZON_HOURS,
)

_LOGGER = logging.getLogger(__name__)

_INVALID_STATES = {None, "unknown", "unavailable", "none", ""}


def _as_float(value: Any) -> float | None:
    if value in _INVALID_STATES:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(mapping: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _parse_datetime(value: Any) -> datetime | None:
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


def _hour_key(value: Any) -> datetime | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return parsed.replace(minute=0, second=0, microsecond=0)


class AnkerEmsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        plan_store: AnkerEmsPlanStore,
        scheduler: AnkerEmsScheduler,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            update_interval=timedelta(seconds=10),
            config_entry=entry,
        )
        self.entry = entry
        self.plan_store = plan_store
        self.scheduler = scheduler

    @property
    def simulation_mode(self) -> bool:
        return bool(self.entry.data.get(CONF_SIMULATION_MODE, True))

    def _entity_id(self, key: str, default: str | None = None) -> str | None:
        return self.entry.options.get(key) or self.entry.data.get(key) or default

    def _state_by_entity_id(self, entity_id: str | None) -> Any:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        return None if state is None else state.state

    def _state(self, key: str) -> Any:
        return self._state_by_entity_id(self._entity_id(key))

    def _number(self, key: str) -> float | None:
        return _as_float(self._state(key))

    def _attributes(self, entity_id: str | None) -> dict[str, Any]:
        if not entity_id:
            return {}
        state = self.hass.states.get(entity_id)
        return {} if state is None else dict(state.attributes)

    def _rows(self, entity_id: str | None, attribute: str) -> list[dict[str, Any]]:
        raw = self._attributes(entity_id).get(attribute, [])
        if not isinstance(raw, list):
            return []
        return [row for row in raw if isinstance(row, dict)]

    def _forecast_entity_ids(self) -> dict[str, str]:
        return {
            "known_price": self._entity_id(CONF_KNOWN_PRICE_ENTITY, DEFAULT_KNOWN_PRICE_ENTITY) or "",
            "forecast_price": self._entity_id(CONF_FORECAST_PRICE_ENTITY, DEFAULT_FORECAST_PRICE_ENTITY) or "",
            "home": self._entity_id(CONF_HOME_FORECAST_ENTITY, DEFAULT_HOME_FORECAST_ENTITY) or "",
            "solar_today": self._entity_id(CONF_SOLAR_TODAY_ENTITY, DEFAULT_SOLAR_TODAY_ENTITY) or "",
            "solar_tomorrow": self._entity_id(CONF_SOLAR_TOMORROW_ENTITY, DEFAULT_SOLAR_TOMORROW_ENTITY) or "",
            "solar_day3": self._entity_id(CONF_SOLAR_DAY3_ENTITY, DEFAULT_SOLAR_DAY3_ENTITY) or "",
        }

    def _build_forecast(self) -> dict[str, Any]:
        entity_ids = self._forecast_entity_ids()
        known_rows = self._rows(entity_ids["known_price"], "prices")
        price_rows = self._rows(entity_ids["forecast_price"], "forecasts")
        home_rows = self._rows(entity_ids["home"], "forecasts")
        solar_rows: list[dict[str, Any]] = []
        for key in ("solar_today", "solar_tomorrow", "solar_day3"):
            solar_rows.extend(self._rows(entity_ids[key], "detailedHourly"))

        now_hour = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
        end_hour = now_hour + timedelta(hours=FORECAST_HORIZON_HOURS)
        slots: dict[datetime, dict[str, Any]] = {
            now_hour + timedelta(hours=index): {
                "time": (now_hour + timedelta(hours=index)).isoformat(),
                "price": None,
                "price_min": None,
                "price_max": None,
                "price_source": None,
                "solar_kwh": None,
                "home_consumption_kwh": None,
            }
            for index in range(FORECAST_HORIZON_HOURS)
        }

        for row in price_rows:
            hour = _hour_key(_first(row, ("time", "timestamp", "datetime", "start")))
            if hour not in slots:
                continue
            predicted = _as_float(_first(row, ("predicted", "all_in", "price", "value")))
            lower = _as_float(_first(row, ("lower", "price_min", "min", "lower_bound")))
            upper = _as_float(_first(row, ("upper", "price_max", "max", "upper_bound")))
            slots[hour]["price"] = predicted
            slots[hour]["price_min"] = lower if lower is not None else predicted
            slots[hour]["price_max"] = upper if upper is not None else predicted
            slots[hour]["price_source"] = "forecast" if predicted is not None else None

        for row in known_rows:
            hour = _hour_key(_first(row, ("timestamp", "time", "datetime", "start")))
            if hour not in slots:
                continue
            price = _as_float(_first(row, ("price", "all_in", "predicted", "value")))
            if price is None:
                continue
            slots[hour]["price"] = price
            slots[hour]["price_min"] = price
            slots[hour]["price_max"] = price
            slots[hour]["price_source"] = "known"

        for row in home_rows:
            hour = _hour_key(_first(row, ("time", "timestamp", "datetime", "start")))
            if hour not in slots:
                continue
            slots[hour]["home_consumption_kwh"] = _as_float(
                _first(row, ("predicted", "value", "consumption", "kwh"))
            )

        for row in solar_rows:
            hour = _hour_key(_first(row, ("period_start", "periodStart", "time", "timestamp")))
            if hour not in slots:
                continue
            value = _as_float(_first(row, ("pv_estimate", "pvEstimate", "predicted", "value")))
            if value is None:
                continue
            current = slots[hour]["solar_kwh"]
            slots[hour]["solar_kwh"] = value if current is None else max(current, value)

        forecast = list(slots.values())
        price_count = sum(1 for row in forecast if row["price"] is not None)
        home_count = sum(1 for row in forecast if row["home_consumption_kwh"] is not None)
        solar_count = sum(1 for row in forecast if row["solar_kwh"] is not None)
        complete_count = sum(
            1
            for row in forecast
            if row["price"] is not None
            and row["home_consumption_kwh"] is not None
            and row["solar_kwh"] is not None
        )

        missing_sources: list[str] = []
        if not known_rows and not price_rows:
            missing_sources.append("price")
        if not home_rows:
            missing_sources.append("home")
        if not solar_rows:
            missing_sources.append("solar")

        ready = price_count >= 24 and home_count >= 24 and solar_count >= 24
        return {
            "forecast_ready": ready,
            "forecast_status": "ready" if ready else "waiting_for_sources",
            "forecast_horizon_hours": FORECAST_HORIZON_HOURS,
            "forecast_price_hours": price_count,
            "forecast_home_hours": home_count,
            "forecast_solar_hours": solar_count,
            "forecast_complete_hours": complete_count,
            "forecast_missing_sources": missing_sources,
            "forecast_sources": entity_ids,
            "forecast": forecast,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        data = {
            "simulation_mode": self.simulation_mode,
            "soc": self._number(CONF_SOC_ENTITY),
            "device_status": self._state(CONF_DEVICE_STATUS_ENTITY),
            "charge_power_w": self._number(CONF_CHARGE_POWER_ENTITY),
            "discharge_power_w": self._number(CONF_DISCHARGE_POWER_ENTITY),
            "grid_import_power_w": self._number(CONF_GRID_IMPORT_POWER_ENTITY),
            "grid_export_power_w": self._number(CONF_GRID_EXPORT_POWER_ENTITY),
            "operating_mode": self._state(CONF_OPERATING_MODE_ENTITY),
            "action_direction": self._state(CONF_ACTION_DIRECTION_ENTITY),
            "power_setpoint_w": self._number(CONF_POWER_SETPOINT_ENTITY),
        }
        data.update(self._build_forecast())
        data.update(self.scheduler.evaluate())
        return data
