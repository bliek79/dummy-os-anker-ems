from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "anker_ems"
    / "forecast_parallel_compare.py"
)
SPEC = importlib.util.spec_from_file_location("forecast_parallel_compare", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

build_forecast_parallel_compare = MODULE.build_forecast_parallel_compare


class ForecastParallelCompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)

    def _legacy(
        self,
        *,
        start: datetime | None = None,
        hours: int = 72,
        value: float = 1.0,
        profile: str = "normal",
    ) -> dict:
        start = start or self.start
        return {
            "profile": profile,
            "forecasts": [
                {
                    "time": (start + timedelta(hours=index)).isoformat(),
                    "predicted": value,
                }
                for index in range(hours)
            ],
        }

    def _contract(
        self,
        *,
        start: datetime | None = None,
        hours: int = 72,
        value: float = 1.0,
        profile: str = "normal",
        runtime_operational: bool = True,
        structural_ready: bool = True,
    ) -> dict:
        start = start or self.start
        return {
            "forecast_contract_shadow_structural_ready": structural_ready,
            "forecast_contract_shadow_runtime_operational": runtime_operational,
            "forecast_contract_shadow_runtime_input_status": (
                "ready" if runtime_operational else "source_unavailable"
            ),
            "forecast_contract_shadow_runtime_blockers": (
                [] if runtime_operational else ["source_unavailable"]
            ),
            "forecast_contract_shadow_profile": profile,
            "forecast_contract_shadow_hours": [
                {
                    "time": (start + timedelta(hours=index)).isoformat(),
                    "home_consumption_kwh": value,
                }
                for index in range(hours)
            ],
        }

    def test_identical_72_hours_are_ready_full_with_zero_delta(self) -> None:
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=self._legacy(),
            contract_shadow=self._contract(),
        )
        self.assertEqual("ready_full", result["status"])
        self.assertEqual(72, result["matched_hours"])
        self.assertEqual(0.0, result["total_delta_kwh"])
        self.assertEqual(0.0, result["mean_absolute_delta_kwh"])
        self.assertEqual(0.0, result["mean_signed_delta_kwh"])
        self.assertEqual(0.0, result["max_absolute_delta_kwh"])
        self.assertEqual(64, len(result["comparison_signature"]))

    def test_one_hour_shift_yields_exact_71_hour_overlap(self) -> None:
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=self._legacy(),
            contract_shadow=self._contract(start=self.start + timedelta(hours=1)),
        )
        self.assertEqual("ready_partial", result["status"])
        self.assertEqual(71, result["matched_hours"])
        self.assertEqual(1, result["legacy_only_hours"])
        self.assertEqual(1, result["contract_only_hours"])
        self.assertEqual(1.0, result["window_start_offset_hours"])
        self.assertTrue(result["matched_hours_contiguous"])

    def test_equivalent_timezone_offsets_match_exactly(self) -> None:
        legacy = {
            "profile": "normal",
            "forecasts": [
                {"time": "2026-09-08T14:00:00+02:00", "predicted": 1.0}
            ],
        }
        contract = {
            "forecast_contract_shadow_structural_ready": True,
            "forecast_contract_shadow_runtime_operational": True,
            "forecast_contract_shadow_profile": "normal",
            "forecast_contract_shadow_hours": [
                {
                    "time": "2026-09-08T12:00:00+00:00",
                    "home_consumption_kwh": 1.0,
                }
            ],
        }
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=legacy,
            contract_shadow=contract,
        )
        self.assertEqual("limited_overlap", result["status"])
        self.assertEqual(1, result["matched_hours"])

    def test_subhourly_legacy_energy_is_summed_and_duplicates_deduplicated(self) -> None:
        forecasts = []
        for minute in (0, 15, 30, 45):
            forecasts.append(
                {
                    "time": self.start.replace(minute=minute).isoformat(),
                    "predicted": 0.25,
                }
            )
        forecasts.append(dict(forecasts[0]))
        legacy = {"profile": "normal", "forecasts": forecasts}
        contract = {
            "forecast_contract_shadow_structural_ready": True,
            "forecast_contract_shadow_runtime_operational": True,
            "forecast_contract_shadow_profile": "normal",
            "forecast_contract_shadow_hours": [
                {"time": self.start.isoformat(), "home_consumption_kwh": 1.0}
            ],
        }
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=legacy,
            contract_shadow=contract,
        )
        self.assertEqual(1.0, result["legacy_matched_total_kwh"])
        self.assertEqual(5, result["legacy_raw_rows"])
        self.assertEqual(4, result["legacy_unique_points"])

    def test_invalid_values_are_not_fabricated_as_zero(self) -> None:
        legacy = {
            "profile": "normal",
            "forecasts": [
                {"time": self.start.isoformat(), "predicted": "nan"},
                {
                    "time": (self.start + timedelta(hours=1)).isoformat(),
                    "predicted": "unavailable",
                },
            ],
        }
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=legacy,
            contract_shadow=self._contract(),
        )
        self.assertEqual("blocked", result["status"])
        self.assertEqual(2, result["legacy_invalid_rows"])
        self.assertIsNone(result["legacy_matched_total_kwh"])

    def test_negative_legacy_value_is_transparently_clamped(self) -> None:
        legacy = {
            "profile": "normal",
            "forecasts": [
                {"time": self.start.isoformat(), "predicted": -1.0},
                {
                    "time": self.start.replace(minute=15).isoformat(),
                    "predicted": 1.0,
                },
            ],
        }
        contract = {
            "forecast_contract_shadow_structural_ready": True,
            "forecast_contract_shadow_runtime_operational": True,
            "forecast_contract_shadow_profile": "normal",
            "forecast_contract_shadow_hours": [
                {"time": self.start.isoformat(), "home_consumption_kwh": 1.0}
            ],
        }
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=legacy,
            contract_shadow=contract,
        )
        self.assertEqual(1, result["legacy_negative_clamped_count"])
        self.assertEqual(1.0, result["legacy_matched_total_kwh"])

    def test_runtime_unavailable_does_not_block_structural_shadow_compare(self) -> None:
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=self._legacy(),
            contract_shadow=self._contract(runtime_operational=False),
        )
        self.assertEqual("ready_full", result["status"])
        self.assertFalse(result["contract_runtime_operational"])
        self.assertIn("contract_runtime_not_operational", result["warnings"])

    def test_contract_structural_failure_blocks_metrics(self) -> None:
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=self._legacy(),
            contract_shadow=self._contract(structural_ready=False),
        )
        self.assertEqual("blocked", result["status"])
        self.assertIn("contract_structural_not_ready", result["blockers"])
        self.assertIsNone(result["total_delta_kwh"])

    def test_non_normal_profile_is_deferred_to_step3(self) -> None:
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=self._legacy(profile="vacation"),
            contract_shadow=self._contract(profile="away"),
        )
        self.assertEqual("blocked", result["status"])
        self.assertFalse(result["profile_comparable"])
        self.assertIn("profile_gate_pending_step3", result["blockers"])
        self.assertIsNone(result["contract_matched_total_kwh"])

    def test_zero_legacy_total_keeps_delta_percent_none(self) -> None:
        result = build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=self._legacy(value=0.0),
            contract_shadow=self._contract(value=1.0),
        )
        self.assertEqual("ready_full", result["status"])
        self.assertIsNone(result["total_delta_percent"])


if __name__ == "__main__":
    unittest.main()
