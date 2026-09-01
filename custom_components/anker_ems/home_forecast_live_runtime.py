from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any

from homeassistant.core import callback

from .home_forecast_evaluation import AnkerEmsHomeForecastEvaluation
from .home_forecast_live_diagnostics import build_home_forecast_live_diagnostics

_LOGGER = logging.getLogger(__name__)


def _evaluation_attrs(data: dict[str, Any]) -> dict[str, Any]:
    evaluation = data.get("home_forecast_live_diagnostics_evaluation") or {}
    return {
        "points": evaluation.get("internal_home_forecast_evaluation_points", 0),
        "mae_kwh_15m": evaluation.get("internal_home_forecast_evaluation_mae_kwh_15m"),
        "mean_bias_kwh_15m": evaluation.get("internal_home_forecast_evaluation_mean_bias_kwh_15m"),
        "absolute_bias_kwh_per_day": evaluation.get(
            "internal_home_forecast_evaluation_absolute_bias_kwh_per_day"
        ),
        "predicted_total_kwh": evaluation.get(
            "internal_home_forecast_evaluation_predicted_total_kwh"
        ),
        "actual_total_kwh": evaluation.get(
            "internal_home_forecast_evaluation_actual_total_kwh"
        ),
        "by_mode": evaluation.get("internal_home_forecast_evaluation_by_mode", {}),
        "by_period": evaluation.get("internal_home_forecast_evaluation_by_period", {}),
        "first_point": evaluation.get("internal_home_forecast_evaluation_first_point"),
        "last_point": evaluation.get("internal_home_forecast_evaluation_last_point"),
        "retention_days": evaluation.get(
            "internal_home_forecast_evaluation_retention_days"
        ),
        "min_actual_coverage_percent": evaluation.get(
            "internal_home_forecast_evaluation_min_actual_coverage_percent"
        ),
        "rows": evaluation.get("internal_home_forecast_evaluation_rows", []),
        "shadow_only": True,
        "plan72_source": False,
    }


def _comparison_attrs(data: dict[str, Any]) -> dict[str, Any]:
    comparison = data.get("home_forecast_live_diagnostics_comparison") or {}
    dashboard = data.get("home_forecast_live_diagnostics_dashboard") or {}
    return {
        "matched_hours": comparison.get("home_forecast_shadow_comparison_matched_hours", 0),
        "external_hours": comparison.get("home_forecast_shadow_comparison_external_hours", 0),
        "internal_hours": comparison.get("home_forecast_shadow_comparison_internal_hours", 0),
        "overlap_percent": comparison.get("home_forecast_shadow_comparison_overlap_percent", 0.0),
        "mae_kwh_hour": comparison.get("home_forecast_shadow_comparison_mae_kwh_hour"),
        "mean_bias_kwh_hour": comparison.get(
            "home_forecast_shadow_comparison_mean_bias_kwh_hour"
        ),
        "external_total_kwh": comparison.get(
            "home_forecast_shadow_comparison_external_total_kwh"
        ),
        "internal_total_kwh": comparison.get(
            "home_forecast_shadow_comparison_internal_total_kwh"
        ),
        "total_delta_kwh": comparison.get(
            "home_forecast_shadow_comparison_total_delta_kwh"
        ),
        "forecast_series": dashboard.get("forecast_series", []),
        "rows": comparison.get("home_forecast_shadow_comparison_rows", []),
        "shadow_only": True,
        "plan72_source": False,
    }


def _transition_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ready": data.get("home_forecast_live_diagnostics_ready", False),
        "blockers": data.get("home_forecast_live_diagnostics_blockers", []),
        "requested_source": data.get("home_forecast_live_diagnostics_requested_source"),
        "source_decision": data.get("home_forecast_live_diagnostics_source_decision", {}),
        "presence": data.get("home_forecast_live_diagnostics_presence", {}),
        "planner_adapter": data.get("home_forecast_live_diagnostics_planner_adapter", {}),
        "active_source_unchanged": data.get(
            "home_forecast_live_diagnostics_active_source_unchanged", True
        ),
        "shadow_only": True,
        "plan72_source": False,
    }


def install_live_diagnostic_sensor_contract() -> None:
    """Install the pre-approved sensor descriptions and exact entity IDs.

    This is called before the sensor platform is forwarded, so the normal
    CoordinatorEntity platform creates the three diagnostics as registry-backed
    entities while keeping the exact Dummy OS entity-ID contract.
    """
    from . import entity_naming, sensor

    entity_naming.EXACT_ENTITY_IDS.update(
        {
            ("sensor", "home_forecast_evaluation"): "sensor.do_ems_home_forecast_evaluation",
            ("sensor", "home_forecast_comparison"): "sensor.do_ems_home_forecast_comparison",
            ("sensor", "home_forecast_transition"): "sensor.do_ems_home_forecast_transition",
        }
    )

    existing = {description.key for description in sensor.SENSORS}
    additions = []
    if "home_forecast_evaluation" not in existing:
        additions.append(
            sensor.AnkerEmsSensorDescription(
                key="home_forecast_evaluation",
                name="DO EMS Home Forecast Evaluation",
                value_fn=lambda d: (
                    (d.get("home_forecast_live_diagnostics_evaluation") or {}).get(
                        "internal_home_forecast_evaluation_status"
                    )
                    or "waiting_for_forward_predictions"
                ),
                attrs_fn=_evaluation_attrs,
            )
        )
    if "home_forecast_comparison" not in existing:
        additions.append(
            sensor.AnkerEmsSensorDescription(
                key="home_forecast_comparison",
                name="DO EMS Home Forecast Comparison",
                value_fn=lambda d: (
                    (d.get("home_forecast_live_diagnostics_comparison") or {}).get(
                        "home_forecast_shadow_comparison_status"
                    )
                    or "waiting_for_overlap"
                ),
                attrs_fn=_comparison_attrs,
            )
        )
    if "home_forecast_transition" not in existing:
        additions.append(
            sensor.AnkerEmsSensorDescription(
                key="home_forecast_transition",
                name="DO EMS Home Forecast Transition",
                value_fn=lambda d: d.get("home_forecast_live_diagnostics_stage") or "learning",
                attrs_fn=_transition_attrs,
            )
        )
    if additions:
        sensor.SENSORS = (*sensor.SENSORS, *additions)


class AnkerEmsHomeForecastLiveRuntime:
    """Attach passive forecast diagnostics to the existing EMS coordinator."""

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self.entry = coordinator.entry
        self.evaluation = AnkerEmsHomeForecastEvaluation(
            self.hass, self.entry.entry_id
        )
        self._last_history_points = -1
        self._previous_internal_forecast: dict[str, Any] | None = None
        self._task = None
        self._publishing = False

    async def async_attach(self) -> None:
        await self.evaluation.async_load()
        data = self.coordinator.data or {}
        self._last_history_points = int(data.get("home_history_points") or 0)
        self._previous_internal_forecast = self._internal_snapshot(data)
        await self._async_refresh(publish=False)
        self.entry.async_on_unload(self.coordinator.async_add_listener(self._listener))

    def _internal_snapshot(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            key: deepcopy(value)
            for key, value in data.items()
            if key.startswith("internal_home_forecast_")
        }

    def _external_hourly_rows(self) -> list[dict[str, Any]]:
        try:
            ids = self.coordinator._forecast_entity_ids()
            rows = self.coordinator._rows(ids["home"], "forecasts")
            hourly, _diagnostics = self.coordinator._aggregate_home_rows_hourly(rows)
            return hourly
        except Exception:
            _LOGGER.exception("Could not build external Home Forecast shadow rows")
            return []

    @callback
    def _listener(self) -> None:
        if self._publishing:
            return
        if self._task is not None and not self._task.done():
            return
        self._task = self.hass.async_create_task(
            self._async_refresh(publish=True),
            "Dummy OS EMS Home Forecast live diagnostics",
        )

    async def _async_refresh(self, *, publish: bool) -> None:
        try:
            data = dict(self.coordinator.data or {})
            history_points = int(data.get("home_history_points") or 0)
            current_internal = self._internal_snapshot(data)

            if history_points != self._last_history_points:
                await self.evaluation.async_observe_completed_history(
                    history_rows=self.coordinator.home_history.history,
                    forecast_snapshot=self._previous_internal_forecast,
                )
                self._last_history_points = history_points

            evaluation_snapshot = self.evaluation.snapshot()
            diagnostics = build_home_forecast_live_diagnostics(
                internal_forecast=current_internal,
                external_hourly_rows=self._external_hourly_rows(),
                evaluation=evaluation_snapshot,
                presence_source_value=None,
                presence_source_configured=False,
                requested_source="external",
            )
            self._previous_internal_forecast = current_internal

            enriched = dict(self.coordinator.data or {})
            enriched.update(diagnostics)
            if publish:
                self._publishing = True
                try:
                    self.coordinator.async_set_updated_data(enriched)
                finally:
                    self._publishing = False
            else:
                # Initial setup runs before sensor entities are forwarded. A
                # direct in-memory enrich is sufficient for their first state.
                if self.coordinator.data is not None:
                    self.coordinator.data.update(diagnostics)
        except Exception:
            _LOGGER.exception("Home Forecast live diagnostics refresh failed")
        finally:
            self._task = None
