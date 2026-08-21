from __future__ import annotations

from datetime import datetime, timedelta
from copy import deepcopy
import logging
from typing import Any, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .plan_store import AnkerEmsPlanStore
from .scheduler import AnkerEmsScheduler
from .safety_guard import AnkerEmsSafetyGuard
from .prestart_validator import AnkerEmsPreStartValidator
from .action_controller import AnkerEmsActionController
from .physical_test import AnkerEmsPhysicalTestController
from .execution import AnkerEmsExecutionController
from .source_monitor import AnkerEmsSourceMonitor
from .energy_need import build_energy_need_analysis
from .planner_preview import build_planner_preview
from .planner_72h import build_72h_plan_preview
from .planner_action_bridge import build_planner_action_bridge

from .const import (
    NAME,
    CONF_SIMULATION_MODE,
    CONF_ELECTRICAL_PROFILE,
    CONF_MAX_CHARGE_POWER_W,
    CONF_MAX_DISCHARGE_POWER_W,
    DEFAULT_ELECTRICAL_PROFILE,
    DEFAULT_SHARED_MAX_POWER_W,
    ELECTRICAL_PROFILE_SHARED,
    ABSOLUTE_MAX_CHARGE_POWER_W,
    ABSOLUTE_MAX_DISCHARGE_POWER_W,
    CONF_SOC_ENTITY,
    CONF_DEVICE_STATUS_ENTITY,
    CONF_CHARGE_POWER_ENTITY,
    CONF_DISCHARGE_POWER_ENTITY,
    CONF_GRID_IMPORT_POWER_ENTITY,
    CONF_GRID_EXPORT_POWER_ENTITY,
    CONF_OPERATING_MODE_ENTITY,
    CONF_ACTION_DIRECTION_ENTITY,
    CONF_POWER_SETPOINT_ENTITY,
    CONF_MARKET_PRICE_ARCHITECTURE_ENABLED,
    CONF_MARKET_PRICE_ENTITY,
    CONF_IMPORT_MARKUP_PER_KWH,
    CONF_EXPORT_MARKUP_PER_KWH,
    CONF_TARIFF_RESOLUTION,
    TARIFF_RESOLUTION_HOURLY,
    TARIFF_RESOLUTION_QUARTER_HOURLY,
    DEFAULT_TARIFF_RESOLUTION,
    DEFAULT_MARKET_PRICE_ENTITY,
    DEFAULT_IMPORT_MARKUP_PER_KWH,
    DEFAULT_EXPORT_MARKUP_PER_KWH,
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
    CONF_MONITOR_ENERGYZERO_ENTITY,
    CONF_MONITOR_STROOMVOORSPELLER_ENTITY,
    CONF_MONITOR_SOLCAST_API_ENTITY,
    DEFAULT_MONITOR_ENERGYZERO_ENTITY,
    DEFAULT_MONITOR_STROOMVOORSPELLER_ENTITY,
    DEFAULT_MONITOR_SOLCAST_API_ENTITY,
    FORECAST_HORIZON_HOURS,
    CONF_SOFTWARE_RESERVE_PERCENT,
    DEFAULT_SOFTWARE_RESERVE_PERCENT,
    CONF_CHARGE_EFFICIENCY_PERCENT,
    CONF_DISCHARGE_EFFICIENCY_PERCENT,
    CONF_MINIMUM_TRADE_MARGIN,
    DEFAULT_CHARGE_EFFICIENCY_PERCENT,
    DEFAULT_DISCHARGE_EFFICIENCY_PERCENT,
    DEFAULT_MINIMUM_TRADE_MARGIN,
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
        safety_guard: AnkerEmsSafetyGuard,
        action_controller: AnkerEmsActionController,
        physical_test: AnkerEmsPhysicalTestController,
        execution: AnkerEmsExecutionController,
        source_monitor: AnkerEmsSourceMonitor,
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
        self.safety_guard = safety_guard
        self.action_controller = action_controller
        self.physical_test = physical_test
        self.execution = execution
        self.source_monitor = source_monitor
        self._cached_72h_plan: dict[str, Any] | None = None
        self._last_plan_source_token: str | None = None
        self._last_plan_refresh_at: datetime | None = None
        self._last_plan_refresh_reason: str | None = None
        self._last_plan_periodic_bucket: str | None = None
        self._last_plan_start_critical_key: str | None = None
        self._last_forecast_ready: bool | None = None
        self._plan_refresh_count_date = dt_util.now().date()
        self._plan_refresh_count_today = 0


    @staticmethod
    def _planner_source_token(data: dict[str, Any]) -> str:
        """Return a stable token for content changes relevant to the 72h planner."""
        sources = data.get("source_monitor_sources") or {}
        relevant = (
            "solcast_forecast",
            "stroomvoorspeller",
            "energyzero_prices",
            "price_forecast",
        )
        return "|".join(
            f"{name}:{(sources.get(name) or {}).get('last_content_change') or ''}"
            for name in relevant
        )

    def _planner_start_critical_key(self, scheduler_data: dict[str, Any]) -> str | None:
        """Return a one-shot key when an automatic plan enters a start-critical phase."""
        slots = scheduler_data.get("scheduler_slots") or {}
        selected_slot = scheduler_data.get("scheduler_selected_slot")
        if isinstance(selected_slot, int):
            detail = slots.get(selected_slot) or slots.get(str(selected_slot)) or {}
            if detail.get("origin") == "automatic_72h_planner":
                identity = detail.get("planner_identity") or f"slot_{selected_slot}"
                return f"due:{identity}"

        next_slot = scheduler_data.get("scheduler_next_future_slot")
        next_start_raw = scheduler_data.get("scheduler_next_future_start")
        if not isinstance(next_slot, int) or not next_start_raw:
            return None
        detail = slots.get(next_slot) or slots.get(str(next_slot)) or {}
        if detail.get("origin") != "automatic_72h_planner":
            return None
        next_start = _parse_datetime(next_start_raw)
        if next_start is None:
            return None
        now_utc = dt_util.utcnow().astimezone(dt_util.UTC)
        minutes = (next_start - now_utc).total_seconds() / 60.0
        if 0.0 < minutes <= 15.0:
            identity = detail.get("planner_identity") or f"slot_{next_slot}"
            return f"near:{identity}"
        return None

    def _should_refresh_72h_plan(
        self,
        data: dict[str, Any],
        scheduler_data: dict[str, Any],
    ) -> tuple[bool, str, str, str | None]:
        """Apply alpha40.2 planner refresh policy.

        The coordinator itself remains fast for live safety/execution state, while
        the expensive 72-hour planner is refreshed at most once per local hour
        between 05:00 and 22:00, plus immediate event-driven exceptions.
        """
        now_local = dt_util.now()
        if self._plan_refresh_count_date != now_local.date():
            self._plan_refresh_count_date = now_local.date()
            self._plan_refresh_count_today = 0

        source_token = self._planner_source_token(data)
        hour_bucket = now_local.strftime("%Y-%m-%dT%H")
        start_key = self._planner_start_critical_key(scheduler_data)
        forecast_ready = bool(data.get("forecast_ready"))

        if self._cached_72h_plan is None:
            return True, "startup", source_token, start_key

        if source_token != self._last_plan_source_token:
            return True, "source_content_changed", source_token, start_key

        if self._last_forecast_ready is False and forecast_ready:
            return True, "forecast_recovered", source_token, start_key

        if start_key is not None and start_key != self._last_plan_start_critical_key:
            return True, "start_critical", source_token, start_key

        if 5 <= now_local.hour <= 22 and hour_bucket != self._last_plan_periodic_bucket:
            return True, "hourly_window", source_token, start_key

        return False, "cached", source_token, start_key

    def _planner_refresh_metadata(self, reason: str) -> dict[str, Any]:
        return {
            "auto_plan_72h_refresh_policy": "hourly_05_22_plus_events",
            "auto_plan_72h_refresh_cached": reason == "cached",
            "auto_plan_72h_refresh_reason": reason,
            "auto_plan_72h_last_refreshed_at": (
                self._last_plan_refresh_at.isoformat()
                if self._last_plan_refresh_at is not None
                else None
            ),
            "auto_plan_72h_refresh_count_today": self._plan_refresh_count_today,
            "auto_plan_72h_periodic_window": "05:00-22:00",
            "auto_plan_72h_periodic_max_per_hour": 1,
            "auto_plan_72h_event_refresh_enabled": True,
        }

    @property
    def simulation_mode(self) -> bool:
        return bool(self.entry.data.get(CONF_SIMULATION_MODE, True))

    @property
    def electrical_profile(self) -> str:
        return str(self.entry.options.get(CONF_ELECTRICAL_PROFILE, self.entry.data.get(CONF_ELECTRICAL_PROFILE, DEFAULT_ELECTRICAL_PROFILE)))

    @property
    def max_charge_power_w(self) -> int:
        fallback = DEFAULT_SHARED_MAX_POWER_W if self.electrical_profile == ELECTRICAL_PROFILE_SHARED else ABSOLUTE_MAX_CHARGE_POWER_W
        raw = self.entry.options.get(CONF_MAX_CHARGE_POWER_W, self.entry.data.get(CONF_MAX_CHARGE_POWER_W, fallback))
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            value = fallback
        profile_cap = DEFAULT_SHARED_MAX_POWER_W if self.electrical_profile == ELECTRICAL_PROFILE_SHARED else ABSOLUTE_MAX_CHARGE_POWER_W
        return max(100, min(profile_cap, value))

    @property
    def max_discharge_power_w(self) -> int:
        fallback = DEFAULT_SHARED_MAX_POWER_W if self.electrical_profile == ELECTRICAL_PROFILE_SHARED else ABSOLUTE_MAX_DISCHARGE_POWER_W
        raw = self.entry.options.get(CONF_MAX_DISCHARGE_POWER_W, self.entry.data.get(CONF_MAX_DISCHARGE_POWER_W, fallback))
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            value = fallback
        profile_cap = DEFAULT_SHARED_MAX_POWER_W if self.electrical_profile == ELECTRICAL_PROFILE_SHARED else ABSOLUTE_MAX_DISCHARGE_POWER_W
        return max(100, min(profile_cap, value))

    def _entity_id(self, key: str, default: str | None = None) -> str | None:
        return self.entry.options.get(key) or self.entry.data.get(key) or default


    @property
    def control_entity_ids(self) -> dict[str, str | None]:
        return {
            "operating_mode": self._entity_id(CONF_OPERATING_MODE_ENTITY),
            "action_direction": self._entity_id(CONF_ACTION_DIRECTION_ENTITY),
            "power_setpoint": self._entity_id(CONF_POWER_SETPOINT_ENTITY),
        }

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

    def _price_architecture_settings(self) -> dict[str, Any]:
        options = self.entry.options
        return {
            "enabled": bool(options.get(CONF_MARKET_PRICE_ARCHITECTURE_ENABLED, False)),
            "market_entity": self._entity_id(CONF_MARKET_PRICE_ENTITY, DEFAULT_MARKET_PRICE_ENTITY) or "",
            "import_markup": _as_float(options.get(CONF_IMPORT_MARKUP_PER_KWH, DEFAULT_IMPORT_MARKUP_PER_KWH)) or 0.0,
            "export_markup": _as_float(options.get(CONF_EXPORT_MARKUP_PER_KWH, DEFAULT_EXPORT_MARKUP_PER_KWH)) or 0.0,
            "resolution": str(options.get(CONF_TARIFF_RESOLUTION, DEFAULT_TARIFF_RESOLUTION)),
        }

    @staticmethod
    def _iter_market_rows(raw: Any, source_kind: str) -> list[dict[str, Any]]:
        """Flatten common Stroomvoorspeller today/tomorrow/forecast payload shapes."""
        rows: list[dict[str, Any]] = []
        time_keys = ("time", "timestamp", "datetime", "start", "period_start", "periodStart")
        price_keys = ("market", "market_price", "marketPrice", "market_predicted", "price", "value", "predicted")

        def walk(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    walk(item)
                return
            if not isinstance(value, dict):
                return
            time_value = _first(value, time_keys)
            price_value = _as_float(_first(value, price_keys))
            if time_value is not None and price_value is not None:
                rows.append({"time": time_value, "market_price": price_value, "source_kind": source_kind})
            for key, item in value.items():
                if key in time_keys or key in price_keys:
                    continue
                if isinstance(item, (list, dict)):
                    walk(item)
                elif isinstance(item, (int, float, str)):
                    parsed_time = _parse_datetime(key)
                    parsed_price = _as_float(item)
                    if parsed_time is not None and parsed_price is not None:
                        rows.append({"time": key, "market_price": parsed_price, "source_kind": source_kind})

        walk(raw)
        return rows

    def _stroomvoorspeller_market_rows(self, entity_id: str) -> list[dict[str, Any]]:
        """Return known hourly prices plus daily model forecast expanded hourly.

        Stroomvoorspeller exposes exact day-ahead prices in ``today.hours`` and
        ``tomorrow.hours``. Its longer horizon is deliberately coarser: each
        item in ``forecast.days`` contains a daily average market estimate, not
        an hourly curve. To keep the 72-hour EMS horizon usable without falling
        back to the legacy Package 40 price forecast, expand that daily market
        estimate across the local hours of the matching day. Exact known
        today/tomorrow rows retain precedence during hourly aggregation.
        """
        attrs = self._attributes(entity_id)
        rows: list[dict[str, Any]] = []
        rows.extend(self._iter_market_rows(attrs.get("today"), "known"))
        rows.extend(self._iter_market_rows(attrs.get("tomorrow"), "known"))

        forecast = attrs.get("forecast")
        if isinstance(forecast, dict):
            days = forecast.get("days")
            if isinstance(days, list):
                for day in days:
                    if not isinstance(day, dict):
                        continue
                    date_value = day.get("date")
                    market_estimate = _as_float(
                        _first(
                            day,
                            (
                                "average_market_estimate",
                                "market_estimate",
                                "average_market",
                                "market",
                                "predicted",
                            ),
                        )
                    )
                    if not date_value or market_estimate is None:
                        continue
                    try:
                        local_midnight = datetime.fromisoformat(str(date_value)).replace(
                            tzinfo=dt_util.DEFAULT_TIME_ZONE
                        )
                    except ValueError:
                        continue
                    for hour_offset in range(24):
                        rows.append(
                            {
                                "time": (local_midnight + timedelta(hours=hour_offset)).isoformat(),
                                "market_price": market_estimate,
                                "source_kind": "forecast",
                            }
                        )

        return rows

    @staticmethod
    def _aggregate_market_rows_hourly(
        rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Aggregate market-price rows to the hourly planner layer.

        The external market source may contain hourly or quarter-hourly values.
        The planner is still hourly, so quarter-hour values are combined into a
        single arithmetic mean per hour. Known prices always take precedence
        over forecast prices for the same hour.
        """
        grouped: dict[tuple[datetime, str], list[float]] = {}
        for row in rows:
            hour = _hour_key(row.get("time"))
            price = _as_float(row.get("market_price"))
            if hour is None or price is None:
                continue
            source_kind = str(row.get("source_kind") or "forecast")
            grouped.setdefault((hour, source_kind), []).append(price)

        hours = sorted({hour for hour, _source in grouped})
        aggregated: list[dict[str, Any]] = []
        full_quarter_hours = 0
        partial_quarter_hours = 0
        max_points_per_hour = 0

        for hour in hours:
            source_kind = "known" if (hour, "known") in grouped else "forecast"
            values = grouped.get((hour, source_kind), [])
            if not values:
                continue
            point_count = len(values)
            max_points_per_hour = max(max_points_per_hour, point_count)
            if point_count >= 4:
                full_quarter_hours += 1
            elif point_count > 1:
                partial_quarter_hours += 1
            aggregated.append(
                {
                    "time": hour.isoformat(),
                    "market_price": sum(values) / point_count,
                    "source_kind": source_kind,
                    "source_point_count": point_count,
                }
            )

        diagnostics = {
            "raw_rows": len(rows),
            "hourly_rows": len(aggregated),
            "full_quarter_hours": full_quarter_hours,
            "partial_quarter_hours": partial_quarter_hours,
            "max_points_per_hour": max_points_per_hour,
        }
        return aggregated, diagnostics

    def _forecast_entity_ids(self) -> dict[str, str]:
        return {
            "market_price": self._entity_id(CONF_MARKET_PRICE_ENTITY, DEFAULT_MARKET_PRICE_ENTITY) or "",
            "known_price": self._entity_id(CONF_KNOWN_PRICE_ENTITY, DEFAULT_KNOWN_PRICE_ENTITY) or "",
            "forecast_price": self._entity_id(CONF_FORECAST_PRICE_ENTITY, DEFAULT_FORECAST_PRICE_ENTITY) or "",
            "home": self._entity_id(CONF_HOME_FORECAST_ENTITY, DEFAULT_HOME_FORECAST_ENTITY) or "",
            "solar_today": self._entity_id(CONF_SOLAR_TODAY_ENTITY, DEFAULT_SOLAR_TODAY_ENTITY) or "",
            "solar_tomorrow": self._entity_id(CONF_SOLAR_TOMORROW_ENTITY, DEFAULT_SOLAR_TOMORROW_ENTITY) or "",
            "solar_day3": self._entity_id(CONF_SOLAR_DAY3_ENTITY, DEFAULT_SOLAR_DAY3_ENTITY) or "",
        }

    def _build_forecast(self) -> dict[str, Any]:
        entity_ids = self._forecast_entity_ids()
        price_settings = self._price_architecture_settings()
        raw_market_rows = (
            self._stroomvoorspeller_market_rows(entity_ids["market_price"])
            if price_settings["enabled"]
            else []
        )
        market_rows, market_row_diagnostics = self._aggregate_market_rows_hourly(raw_market_rows)
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
                "market_price": None,
                "import_price": None,
                "export_price": None,
                "import_price_source": None,
                "export_price_source": None,
                "solar_kwh": None,
                "home_consumption_kwh": None,
            }
            for index in range(FORECAST_HORIZON_HOURS)
        }

        if price_settings["enabled"] and market_rows:
            import_markup = float(price_settings["import_markup"])
            export_markup = float(price_settings["export_markup"])
            # The planner remains hourly. If the market source contains
            # quarter-hour values they are averaged above into the matching
            # hourly planner slot, preventing the previous last-quarter-wins
            # behaviour.
            for row in market_rows:
                hour = _hour_key(row.get("time"))
                if hour not in slots:
                    continue
                market_price = _as_float(row.get("market_price"))
                if market_price is None:
                    continue
                source_kind = str(row.get("source_kind") or "forecast")
                if source_kind == "forecast" and slots[hour].get("price_source") == "known":
                    continue
                import_price = market_price + import_markup
                export_price = market_price + export_markup
                slots[hour]["market_price"] = market_price
                slots[hour]["import_price"] = import_price
                slots[hour]["export_price"] = export_price
                slots[hour]["price"] = import_price
                slots[hour]["price_min"] = import_price
                slots[hour]["price_max"] = import_price
                slots[hour]["price_source"] = source_kind
                slots[hour]["import_price_source"] = source_kind
                slots[hour]["export_price_source"] = source_kind

        if not (price_settings["enabled"] and market_rows):
            for row in price_rows:
                hour = _hour_key(_first(row, ("time", "timestamp", "datetime", "start")))
                if hour not in slots:
                    continue
                predicted = _as_float(_first(row, ("predicted", "all_in", "price", "value")))
                lower = _as_float(_first(row, ("lower", "price_min", "min", "lower_bound")))
                upper = _as_float(_first(row, ("upper", "price_max", "max", "upper_bound")))
                slots[hour]["price"] = predicted
                slots[hour]["import_price"] = predicted
                slots[hour]["export_price"] = predicted
                slots[hour]["price_min"] = lower if lower is not None else predicted
                slots[hour]["price_max"] = upper if upper is not None else predicted
                slots[hour]["price_source"] = "forecast" if predicted is not None else None
                slots[hour]["import_price_source"] = "forecast" if predicted is not None else None
                slots[hour]["export_price_source"] = "forecast" if predicted is not None else None

            for row in known_rows:
                hour = _hour_key(_first(row, ("timestamp", "time", "datetime", "start")))
                if hour not in slots:
                    continue
                price = _as_float(_first(row, ("price", "all_in", "predicted", "value")))
                if price is None:
                    continue
                slots[hour]["price"] = price
                slots[hour]["import_price"] = price
                slots[hour]["export_price"] = price
                slots[hour]["price_min"] = price
                slots[hour]["price_max"] = price
                slots[hour]["price_source"] = "known"
                slots[hour]["import_price_source"] = "known"
                slots[hour]["export_price_source"] = "known"

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
        if price_settings["enabled"]:
            if not market_rows:
                missing_sources.append("price")
        elif not known_rows and not price_rows:
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
            "price_architecture_enabled": bool(price_settings["enabled"]),
            "price_architecture_source": entity_ids.get("market_price") if price_settings["enabled"] else "legacy_known_plus_forecast",
            "price_architecture_market_rows": len(market_rows),
            "price_architecture_raw_market_rows": market_row_diagnostics["raw_rows"],
            "price_architecture_hourly_market_rows": market_row_diagnostics["hourly_rows"],
            "price_architecture_full_quarter_hours": market_row_diagnostics["full_quarter_hours"],
            "price_architecture_partial_quarter_hours": market_row_diagnostics["partial_quarter_hours"],
            "price_architecture_max_points_per_hour": market_row_diagnostics["max_points_per_hour"],
            "price_architecture_import_markup_per_kwh": price_settings["import_markup"],
            "price_architecture_export_markup_per_kwh": price_settings["export_markup"],
            "price_architecture_requested_resolution": price_settings["resolution"],
            "price_architecture_effective_resolution": TARIFF_RESOLUTION_HOURLY,
            "price_architecture_quarter_hour_ready": bool(
                price_settings["resolution"] == TARIFF_RESOLUTION_QUARTER_HOURLY
                and market_row_diagnostics["full_quarter_hours"] >= 24
            ),
            "price_architecture_resolution_note": (
                "quarter_hour_source_aggregated_to_hourly_planner"
                if price_settings["resolution"] == TARIFF_RESOLUTION_QUARTER_HOURLY
                else "hourly_planner"
            ),
            "forecast": forecast,
        }

    def _source_monitor_specs(self) -> dict[str, dict[str, Any]]:
        forecast_ids = self._forecast_entity_ids()
        energyzero_id = self._entity_id(
            CONF_MONITOR_ENERGYZERO_ENTITY, DEFAULT_MONITOR_ENERGYZERO_ENTITY
        ) or ""
        stroom_id = self._entity_id(
            CONF_MONITOR_STROOMVOORSPELLER_ENTITY, DEFAULT_MONITOR_STROOMVOORSPELLER_ENTITY
        ) or ""
        solcast_api_id = self._entity_id(
            CONF_MONITOR_SOLCAST_API_ENTITY, DEFAULT_MONITOR_SOLCAST_API_ENTITY
        ) or ""

        def state_payload(entity_id: str, attrs: tuple[str, ...]) -> Any:
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None:
                return None
            payload: dict[str, Any] = {"state": state.state}
            for attr in attrs:
                if attr in state.attributes:
                    payload[attr] = state.attributes.get(attr)
            return payload

        solar_ids = [
            forecast_ids["solar_today"],
            forecast_ids["solar_tomorrow"],
            forecast_ids["solar_day3"],
        ]
        solar_content = [state_payload(entity_id, ("detailedHourly",)) for entity_id in solar_ids]

        return {
            "solcast_api": {
                "entity_ids": [solcast_api_id],
                "content": state_payload(solcast_api_id, ()),
            },
            "solcast_forecast": {
                "entity_ids": solar_ids,
                "content": solar_content,
            },
            "energyzero_prices": {
                "entity_ids": [energyzero_id],
                "content": state_payload(energyzero_id, ("prices", "price_count", "available_until")),
            },
            "stroomvoorspeller": {
                "entity_ids": [stroom_id],
                "content": state_payload(stroom_id, ("today", "tomorrow", "forecast", "hours", "prices", "updated")),
            },
            "price_forecast": {
                "entity_ids": [forecast_ids["forecast_price"]],
                "content": state_payload(forecast_ids["forecast_price"], ("forecasts",)),
            },
        }

    async def _async_update_data(self) -> dict[str, Any]:
        control_ids = self.control_entity_ids
        data = {
            "simulation_mode": self.simulation_mode,
            "electrical_profile": self.electrical_profile,
            "max_charge_power_w": self.max_charge_power_w,
            "max_discharge_power_w": self.max_discharge_power_w,
            "control_path_configured": all(bool(control_ids.get(key)) for key in ("operating_mode", "action_direction", "power_setpoint")),
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
        # Source Monitor remains fast and observes every coordinator cycle. It
        # supplies content-change timestamps used to trigger event-driven 72h
        # refreshes without polling the heavy planner every 10 seconds.
        data.update(await self.source_monitor.async_observe(self._source_monitor_specs()))

        reserve_percent = self.entry.options.get(
            CONF_SOFTWARE_RESERVE_PERCENT, DEFAULT_SOFTWARE_RESERVE_PERCENT
        )
        energy_need = build_energy_need_analysis(
            data.get("forecast", []), data.get("soc"), reserve_percent
        )
        data.update(energy_need)
        charge_efficiency_percent = self.entry.options.get(
            CONF_CHARGE_EFFICIENCY_PERCENT, DEFAULT_CHARGE_EFFICIENCY_PERCENT
        )
        discharge_efficiency_percent = self.entry.options.get(
            CONF_DISCHARGE_EFFICIENCY_PERCENT, DEFAULT_DISCHARGE_EFFICIENCY_PERCENT
        )
        minimum_trade_margin = self.entry.options.get(
            CONF_MINIMUM_TRADE_MARGIN, DEFAULT_MINIMUM_TRADE_MARGIN
        )
        planner_preview = build_planner_preview(
            data.get("forecast", []),
            energy_need,
            data.get("soc"),
            charge_efficiency_percent,
            discharge_efficiency_percent,
            minimum_trade_margin,
            max_charge_power_w=self.max_charge_power_w,
        )
        data.update(planner_preview)

        # Scheduler timing is cheap and remains live. It is also used as an
        # exception trigger so the 72h planner gets one fresh calculation when
        # an automatic action enters the final 15-minute decision window or
        # becomes start-ready.
        scheduler_snapshot = self.scheduler.evaluate(
            self.max_charge_power_w, self.max_discharge_power_w
        )
        refresh, refresh_reason, source_token, start_key = self._should_refresh_72h_plan(
            data, scheduler_snapshot
        )
        if refresh:
            self._cached_72h_plan = build_72h_plan_preview(
                data.get("forecast", []),
                energy_need,
                planner_preview,
                data.get("soc"),
                charge_efficiency_percent,
                discharge_efficiency_percent,
                max_charge_power_w=self.max_charge_power_w,
                max_discharge_power_w=self.max_discharge_power_w,
            )
            now_local = dt_util.now()
            self._last_plan_refresh_at = now_local
            self._last_plan_refresh_reason = refresh_reason
            self._last_plan_source_token = source_token
            self._last_forecast_ready = bool(data.get("forecast_ready"))
            self._last_plan_start_critical_key = start_key
            self._plan_refresh_count_today += 1
            if 5 <= now_local.hour <= 22:
                # Any event-driven refresh during this hour also satisfies the
                # hourly periodic refresh, preventing a redundant second pass.
                self._last_plan_periodic_bucket = now_local.strftime("%Y-%m-%dT%H")
        else:
            self._last_forecast_ready = bool(data.get("forecast_ready"))

        if self._cached_72h_plan is not None:
            data.update(deepcopy(self._cached_72h_plan))
        data.update(self._planner_refresh_metadata(refresh_reason))
        data.update(scheduler_snapshot)
        bridge = build_planner_action_bridge(data)
        data.update(bridge)

        # Alpha30: controlled automatic Plan Store write followed by a separate
        # guarded Scheduler handoff. Physical execution remains disabled.
        desired_auto_plans: dict[int, dict[str, Any]] = {}
        write_gate_open = (
            bool(data.get("auto_bridge_valid"))
            and bool(data.get("auto_plan_72h_execution_buffer_safe"))
            and bool(data.get("forecast_ready"))
            and not int(data.get("auto_bridge_invalid_candidate_count") or 0)
        )
        if write_gate_open:
            for proposal in data.get("auto_bridge_slot_preview") or []:
                if not proposal.get("plan_store_write_permitted"):
                    continue
                slot = proposal.get("suggested_slot")
                if isinstance(slot, int):
                    desired_auto_plans[slot] = proposal

        # Alpha40.1: preserve existing planner-owned future plans while the
        # planner/forecast gate is temporarily unavailable. An empty desired
        # set is only authoritative when the write gate is open; otherwise
        # syncing with {} would incorrectly clear valid pending plans during
        # startup or a transient source outage.
        if write_gate_open:
            write_result = await self.plan_store.async_sync_automatic_plans(
                desired_auto_plans
            )
        else:
            write_result = {
                "changed": False,
                "changed_slots": [],
                "written_slots": [],
                "cleared_slots": [],
                "skipped_slots": [],
                "preserved_due_gate_closed": True,
            }
        # Promote only the exact planner proposals that are currently approved
        # by the bridge. Matching signatures protect against stale data and
        # concurrent/manual edits between write and handoff.
        handoff_gate_open = write_gate_open
        handoff_allowed: dict[int, str] = {}
        if handoff_gate_open:
            for proposal in data.get("auto_bridge_slot_preview") or []:
                if not proposal.get("scheduler_handoff_permitted"):
                    continue
                slot = proposal.get("suggested_slot")
                signature = proposal.get("planner_signature")
                if isinstance(slot, int) and isinstance(signature, str) and signature:
                    handoff_allowed[slot] = signature

        handoff_result = await self.plan_store.async_handoff_automatic_plans(
            handoff_allowed if handoff_gate_open else {}
        )

        data.update(
            {
                "auto_bridge_plan_store_write_enabled": True,
                "auto_bridge_plan_store_write_gate_open": write_gate_open,
                "auto_bridge_plan_store_preserved_due_gate_closed": write_result.get("preserved_due_gate_closed", False),
                "auto_bridge_plan_store_write_changed": write_result.get("changed", False),
                "auto_bridge_plan_store_written_slots": write_result.get("written_slots", []),
                "auto_bridge_plan_store_cleared_slots": write_result.get("cleared_slots", []),
                "auto_bridge_plan_store_skipped_slots": write_result.get("skipped_slots", []),
                "auto_bridge_scheduler_handoff_enabled": True,
                "auto_bridge_scheduler_handoff_gate_open": handoff_gate_open,
                "auto_bridge_scheduler_handoff_changed": handoff_result.get("changed", False),
                "auto_bridge_scheduler_handoff_slots": handoff_result.get("handed_off_slots", []),
                "auto_bridge_scheduler_handoff_skipped_slots": handoff_result.get("skipped_slots", []),
                "auto_bridge_execution_enabled": False,
                "auto_bridge_observational_only": False,
            }
        )

        # Refresh scheduler details from the just-synchronized and handed-off store.
        data.update(self.scheduler.evaluate(self.max_charge_power_w, self.max_discharge_power_w))
        refreshed_bridge = build_planner_action_bridge(data)
        # Keep writer result flags from above while refreshing candidate/slot data.
        for key, value in refreshed_bridge.items():
            if key not in {
                "auto_bridge_plan_store_write_enabled",
                "auto_bridge_scheduler_handoff_enabled",
                "auto_bridge_scheduler_handoff_gate_open",
                "auto_bridge_scheduler_handoff_changed",
                "auto_bridge_scheduler_handoff_slots",
                "auto_bridge_scheduler_handoff_skipped_slots",
                "auto_bridge_execution_enabled",
                "auto_bridge_observational_only",
            }:
                data[key] = value
        # Time-aware diagnostics + authoritative pre-start gate for automatic
        # Scheduler-ready plans. Alpha35 then hands the approved automatic plan
        # to a non-actuating Safety Guard stage. Physical execution remains off.
        data.update(AnkerEmsPreStartValidator().evaluate(data))
        data["physical_test_active"] = bool(self.physical_test.data.get("active"))
        data["execution_active"] = bool(self.execution.data.get("active"))
        data.update(self.safety_guard.evaluate_automatic_handoff(data))
        # Expose the automatic handoff into the Execution Controller as a
        # non-actuating preview, followed by Alpha38 final live revalidation.
        # No Home Assistant control service is called by either stage.
        data.update(self.execution.evaluate_automatic_handoff(data))
        data.update(self.execution.evaluate_final_revalidation(data))
        data.update(self.execution.evaluate_mode_switch_transaction(data))

        # Legacy Safety Guard / Action Controller remain available for the
        # existing manual execution path. The automatic Alpha35 handoff stops
        # before the Execution Controller and does not call services.
        data.update(self.safety_guard.evaluate(data))
        data.update(self.action_controller.evaluate(data))
        test_data = self.physical_test.data
        data.update({f"physical_test_{key}": value for key, value in test_data.items()})

        execution_data = self.execution.data
        data.update({f"execution_{key}": value for key, value in execution_data.items()})
        return data
