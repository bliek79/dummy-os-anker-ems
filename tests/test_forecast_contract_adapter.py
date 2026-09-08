from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "anker_ems"
    / "forecast_contract_adapter.py"
)
SPEC = importlib.util.spec_from_file_location("forecast_contract_adapter", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def valid_contract() -> dict:
    start = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
    hours = []
    for index in range(72):
        hour_start = start + timedelta(hours=index)
        hours.append(
            {
                "index": index,
                "start": hour_start.isoformat(),
                "end": (hour_start + timedelta(hours=1)).isoformat(),
                "energy_kwh": round(0.25 + index / 1000.0, 6),
                "quarter_count": 4,
                "populated_quarters": 4,
                "supported_quarters": 4,
                "profile": "normal",
            }
        )
    return {
        "contract_name": "dummy_os_forecast_to_planner",
        "contract_version": 1,
        "schema_version": 1,
        "profile_contract_version": 1,
        "status": "ready",
        "ready_for_planner": True,
        "blockers": [],
        "profile": "normal",
        "native_resolution_minutes": 15,
        "native_slot_count": 288,
        "planner_resolution_minutes": 60,
        "planner_hour_count": 72,
        "quarters_per_hour": 4,
        "planner_start": start.isoformat(),
        "planner_end": (start + timedelta(hours=72)).isoformat(),
        "padding_used": False,
        "second_forecast_architecture": False,
        "consumer_scope": "dummy_os_ems_planner",
        "physical_execution_authority": False,
        "runtime_input_status": "ok",
        "forecast_operational_input_ok": True,
        "runtime_blockers": [],
        "hours": hours,
    }


class ForecastContractAdapterTests(unittest.TestCase):
    def adapt(self, attrs: dict, state: str = "ready") -> dict:
        return adapter.build_forecast_contract_shadow(
            entity_state=state,
            attributes=attrs,
        )

    def test_valid_contract_normalizes_exactly_72_hours(self) -> None:
        attrs = valid_contract()
        result = self.adapt(attrs)
        self.assertEqual(result["forecast_contract_shadow_status"], "ready")
        self.assertTrue(result["forecast_contract_shadow_structural_ready"])
        self.assertTrue(result["forecast_contract_shadow_runtime_operational"])
        self.assertEqual(result["forecast_contract_shadow_planner_hour_count"], 72)
        self.assertEqual(len(result["forecast_contract_shadow_hours"]), 72)
        self.assertEqual(
            result["forecast_contract_shadow_hours"][0],
            {
                "time": attrs["hours"][0]["start"],
                "home_consumption_kwh": attrs["hours"][0]["energy_kwh"],
            },
        )
        self.assertEqual(len(result["forecast_contract_shadow_consumer_signature"]), 64)
        self.assertTrue(result["forecast_contract_shadow_only"])
        self.assertFalse(result["forecast_contract_shadow_plan72_source"])

    def test_runtime_unavailable_stays_structurally_ready(self) -> None:
        attrs = valid_contract()
        attrs["runtime_input_status"] = "source_unavailable"
        attrs["forecast_operational_input_ok"] = False
        attrs["runtime_blockers"] = ["source_unavailable"]
        result = self.adapt(attrs)
        self.assertEqual(result["forecast_contract_shadow_status"], "runtime_blocked")
        self.assertTrue(result["forecast_contract_shadow_structural_ready"])
        self.assertFalse(result["forecast_contract_shadow_runtime_operational"])
        self.assertEqual(result["forecast_contract_shadow_planner_hour_count"], 72)

    def test_71_hours_blocks_without_zero_fabrication(self) -> None:
        attrs = valid_contract()
        attrs["hours"] = attrs["hours"][:-1]
        result = self.adapt(attrs)
        self.assertEqual(result["forecast_contract_shadow_status"], "blocked")
        self.assertFalse(result["forecast_contract_shadow_structural_ready"])
        self.assertEqual(result["forecast_contract_shadow_hours"], [])
        self.assertIn("planner_hour_count_not_72", result["forecast_contract_shadow_blockers"])

    def test_missing_energy_blocks_without_zero_fabrication(self) -> None:
        attrs = valid_contract()
        attrs["hours"][5]["energy_kwh"] = None
        result = self.adapt(attrs)
        self.assertEqual(result["forecast_contract_shadow_hours"], [])
        self.assertIn("hour_5_energy_unavailable", result["forecast_contract_shadow_blockers"])

    def test_wrong_schema_version_blocks(self) -> None:
        attrs = valid_contract()
        attrs["schema_version"] = 2
        result = self.adapt(attrs)
        self.assertIn("schema_version_mismatch", result["forecast_contract_shadow_blockers"])

    def test_time_gap_blocks(self) -> None:
        attrs = valid_contract()
        shifted = datetime.fromisoformat(attrs["hours"][20]["start"]) + timedelta(minutes=15)
        attrs["hours"][20]["start"] = shifted.isoformat()
        attrs["hours"][20]["end"] = (shifted + timedelta(hours=1)).isoformat()
        result = self.adapt(attrs)
        self.assertIn("hour_20_not_contiguous", result["forecast_contract_shadow_blockers"])

    def test_unclassified_profile_blocks(self) -> None:
        attrs = valid_contract()
        attrs["profile"] = "unclassified"
        for hour in attrs["hours"]:
            hour["profile"] = "unclassified"
        result = self.adapt(attrs)
        self.assertIn("profile_unclassified", result["forecast_contract_shadow_blockers"])

    def test_away_profile_is_structurally_supported(self) -> None:
        attrs = valid_contract()
        attrs["profile"] = "away"
        for hour in attrs["hours"]:
            hour["profile"] = "away"
        result = self.adapt(attrs)
        self.assertTrue(result["forecast_contract_shadow_structural_ready"])
        self.assertEqual(result["forecast_contract_shadow_profile"], "away")

    def test_negative_or_non_finite_energy_blocks(self) -> None:
        for invalid in (-0.1, float("nan"), float("inf")):
            with self.subTest(invalid=invalid):
                attrs = valid_contract()
                attrs["hours"][3]["energy_kwh"] = invalid
                result = self.adapt(attrs)
                self.assertIn(
                    "hour_3_energy_unavailable",
                    result["forecast_contract_shadow_blockers"],
                )
                self.assertEqual(result["forecast_contract_shadow_hours"], [])

    def test_producer_not_ready_is_blocked_and_preserves_reason(self) -> None:
        attrs = valid_contract()
        attrs["status"] = "blocked"
        attrs["ready_for_planner"] = False
        attrs["blockers"] = ["model_health_insufficient"]
        result = self.adapt(attrs, state="blocked")
        self.assertIn("producer_status_not_ready", result["forecast_contract_shadow_blockers"])
        self.assertIn("producer_not_ready_for_planner", result["forecast_contract_shadow_blockers"])
        self.assertIn(
            "producer:model_health_insufficient",
            result["forecast_contract_shadow_blockers"],
        )


if __name__ == "__main__":
    unittest.main()
