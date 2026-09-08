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
        profile_field: str = "profile",
    ) -> dict:
        start = start or self.start
        attrs = {
            profile_field: profile,
            "forecasts": [
                {
                    "time": (start + timedelta(hours=index)).isoformat(),
                    "predicted": value,
                    "profile": profile,
                }
                for index in range(hours)
            ],
        }
        return attrs

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

    def _compare(self, legacy: dict, contract: dict | None = None) -> dict:
        return build_forecast_parallel_compare(
            legacy_entity_state="ready",
            legacy_attributes=legacy,
            contract_shadow=contract or self._contract(),
        )

    def test_identical_72_hours_are_ready_full_with_zero_delta(self) -> None:
        result = self._compare(self._legacy())
        self.assertEqual("ready_full", result["status"])
        self.assertEqual(72, result["matched_hours"])
        self.assertTrue(result["profile_comparable"])
        self.assertEqual(72, result["matched_profile_normal_hours"])
        self.assertEqual(0, result["matched_profile_missing_hours"])
        self.assertEqual(0.0, result["total_delta_kwh"])
        self.assertEqual(64, len(result["comparison_signature"]))

    def test_operating_mode_is_recognized_and_allows_normal_compare(self) -> None:
        result = self._compare(self._legacy(profile_field="operating_mode"))
        self.assertEqual("ready_full", result["status"])
        self.assertEqual("normal", result["legacy_profile"])
        self.assertEqual("operating_mode", result["legacy_profile_source"])
        self.assertTrue(result["profile_comparable"])

    def test_one_hour_shift_yields_exact_71_hour_overlap(self) -> None:
        result = self._compare(
            self._legacy(profile_field="operating_mode"),
            self._contract(start=self.start + timedelta(hours=1)),
        )
        self.assertEqual("ready_partial", result["status"])
        self.assertEqual(71, result["matched_hours"])
        self.assertEqual(1, result["legacy_only_hours"])
        self.assertEqual(1, result["contract_only_hours"])
        self.assertEqual(1.0, result["window_start_offset_hours"])
        self.assertTrue(result["matched_hours_contiguous"])
        self.assertEqual(71, result["matched_profile_normal_hours"])

    def test_equivalent_timezone_offsets_match_exactly(self) -> None:
        legacy = {
            "operating_mode": "normal",
            "forecasts": [
                {
                    "time": "2026-09-08T14:00:00+02:00",
                    "predicted": 1.0,
                    "profile": "normal",
                }
            ],
        }
        contract = {
            "forecast_contract_shadow_structural_ready": True,
            "forecast_contract_shadow_runtime_operational": True,
            "forecast_contract_shadow_profile": "normal",
            "forecast_contract_shadow_hours": [
                {"time": "2026-09-08T12:00:00+00:00", "home_consumption_kwh": 1.0}
            ],
        }
        result = self._compare(legacy, contract)
        self.assertEqual("limited_overlap", result["status"])
        self.assertEqual(1, result["matched_hours"])

    def test_subhourly_energy_is_summed_and_profiles_must_all_be_explicit(self) -> None:
        forecasts = [
            {
                "time": self.start.replace(minute=minute).isoformat(),
                "predicted": 0.25,
                "profile": "normal",
            }
            for minute in (0, 15, 30, 45)
        ]
        forecasts.append(dict(forecasts[0]))
        legacy = {"operating_mode": "normal", "forecasts": forecasts}
        contract = {
            "forecast_contract_shadow_structural_ready": True,
            "forecast_contract_shadow_runtime_operational": True,
            "forecast_contract_shadow_profile": "normal",
            "forecast_contract_shadow_hours": [
                {"time": self.start.isoformat(), "home_consumption_kwh": 1.0}
            ],
        }
        result = self._compare(legacy, contract)
        self.assertEqual(1.0, result["legacy_matched_total_kwh"])
        self.assertEqual(5, result["legacy_raw_rows"])
        self.assertEqual(4, result["legacy_unique_points"])

    def test_missing_matched_row_profile_blocks_metrics(self) -> None:
        legacy = self._legacy(profile_field="operating_mode")
        legacy["forecasts"][3].pop("profile")
        result = self._compare(legacy)
        self.assertEqual("blocked", result["status"])
        self.assertFalse(result["profile_comparable"])
        self.assertEqual(1, result["matched_profile_missing_hours"])
        self.assertIsNone(result["total_delta_kwh"])

    def test_vacation_or_mixed_matched_profile_blocks_metrics(self) -> None:
        legacy = self._legacy(profile_field="operating_mode")
        legacy["forecasts"][5]["profile"] = "vacation"
        result = self._compare(legacy)
        self.assertEqual("blocked", result["status"])
        self.assertFalse(result["profile_comparable"])
        self.assertEqual(1, result["matched_profile_vacation_hours"])
        self.assertIsNone(result["contract_matched_total_kwh"])

    def test_invalid_values_are_not_fabricated_as_zero(self) -> None:
        legacy = {
            "operating_mode": "normal",
            "forecasts": [
                {"time": self.start.isoformat(), "predicted": "nan", "profile": "normal"},
                {
                    "time": (self.start + timedelta(hours=1)).isoformat(),
                    "predicted": "unavailable",
                    "profile": "normal",
                },
            ],
        }
        result = self._compare(legacy)
        self.assertEqual("blocked", result["status"])
        self.assertEqual(2, result["legacy_invalid_rows"])
        self.assertIsNone(result["legacy_matched_total_kwh"])

    def test_negative_legacy_value_is_transparently_clamped(self) -> None:
        legacy = {
            "operating_mode": "normal",
            "forecasts": [
                {"time": self.start.isoformat(), "predicted": -1.0, "profile": "normal"},
                {
                    "time": self.start.replace(minute=15).isoformat(),
                    "predicted": 1.0,
                    "profile": "normal",
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
        result = self._compare(legacy, contract)
        self.assertEqual(1, result["legacy_negative_clamped_count"])
        self.assertEqual(1.0, result["legacy_matched_total_kwh"])

    def test_runtime_unavailable_does_not_block_structural_shadow_compare(self) -> None:
        result = self._compare(self._legacy(), self._contract(runtime_operational=False))
        self.assertEqual("ready_full", result["status"])
        self.assertFalse(result["contract_runtime_operational"])
        self.assertIn("contract_runtime_not_operational", result["warnings"])

    def test_contract_structural_failure_blocks_metrics(self) -> None:
        result = self._compare(self._legacy(), self._contract(structural_ready=False))
        self.assertEqual("blocked", result["status"])
        self.assertIn("contract_structural_not_ready", result["blockers"])
        self.assertIsNone(result["total_delta_kwh"])

    def test_non_normal_profile_is_deferred_to_step3(self) -> None:
        result = self._compare(
            self._legacy(profile="vacation", profile_field="operating_mode"),
            self._contract(profile="away"),
        )
        self.assertEqual("blocked", result["status"])
        self.assertFalse(result["profile_comparable"])
        self.assertIn("profile_gate_pending_step3", result["blockers"])

    def test_zero_legacy_total_keeps_delta_percent_none(self) -> None:
        result = self._compare(self._legacy(value=0.0))
        self.assertEqual("ready_full", result["status"])
        self.assertIsNone(result["total_delta_percent"])


if __name__ == "__main__":
    unittest.main()
