"""Alpha83: executable regression of Plan72 -> partial charge -> safe bridge handoff.

Only the bridge translation is changed. Frozen alpha80 forecast/planner policy
and the Alpha82 battery Number and emergency reset are independent contracts.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "anker_ems"
PACKAGE = "alpha83_bridge_testpkg"
START = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)


def load_bridge():
    if "homeassistant.util.dt" not in sys.modules:
        ha = types.ModuleType("homeassistant")
        util = types.ModuleType("homeassistant.util")
        dt = types.ModuleType("homeassistant.util.dt")
        dt.UTC = timezone.utc
        dt.DEFAULT_TIME_ZONE = timezone.utc
        dt.utcnow = lambda: datetime.now(timezone.utc)
        dt.now = lambda: datetime.now(timezone.utc)
        dt.parse_datetime = lambda value: datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        util.dt = dt
        ha.util = util
        sys.modules.setdefault("homeassistant", ha)
        sys.modules.setdefault("homeassistant.util", util)
        sys.modules.setdefault("homeassistant.util.dt", dt)
    if PACKAGE not in sys.modules:
        pkg = types.ModuleType(PACKAGE)
        pkg.__path__ = [str(COMPONENT)]
        sys.modules[PACKAGE] = pkg
    for stem in ("const", "planner_action_bridge"):
        qualified = f"{PACKAGE}.{stem}"
        if qualified not in sys.modules:
            spec = importlib.util.spec_from_file_location(qualified, COMPONENT / f"{stem}.py")
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            sys.modules[qualified] = module
            spec.loader.exec_module(module)
    return sys.modules[f"{PACKAGE}.planner_action_bridge"]


bridge = load_bridge()


def segment(*, offset: int, hours: int, energy: float, soc: float | None = 27.0) -> list[dict]:
    rows = []
    for i in range(hours):
        hour = START + timedelta(hours=offset+i)
        rows.append({
            "time": hour.isoformat(),
            "parsed_time": hour,
            "bridge_action": "laden",
            "bridge_purpose": "veiligheidsladen",
            "bridge_energy_kwh": energy / hours,
            "charge_from_grid_safety_kwh": energy / hours,
            "soc_start": soc if i == 0 else min(95, (soc or 0) + i * 5),
            "execution_reserve_floor_start_soc": 14.0,
            "execution_reserve_floor_soc": 14.0,
            "price": 0.14729,
            "price_source": "known",
        })
    return rows


def snapshot(*parts: list[dict], slots=None, **extra) -> dict:
    data = {
        "auto_plan_72h_valid": True,
        "auto_plan_72h_execution_buffer_safe": True,
        "forecast_ready": True,
        "max_charge_power_w": 2400,
        "max_discharge_power_w": 2400,
        "battery_capacity_kwh": 7.2,
        "charge_efficiency_percent": 92.0,
        "discharge_efficiency_percent": 92.0,
        "auto_plan_72h_plan": [
            {k: v for k, v in item.items() if k not in {"parsed_time", "bridge_action", "bridge_purpose", "bridge_energy_kwh"}}
            for chunk in parts for item in chunk
        ],
        "scheduler_slots": slots or {},
    }
    data.update(extra)
    return data


class CandidateFeasibilityTests(unittest.TestCase):
    def _make(self, **kw):
        return bridge._build_candidate(
            segment(offset=8, hours=1, energy=2.4, soc=27.0),
            START, 2400, 2400, 7.2, 92.0, 92.0, **kw
        )

    def test_reported_2400_w_1_hour_shortfall_is_80_wh(self):
        item = self._make()
        self.assertTrue(item["valid"])
        self.assertEqual(item["validation_reasons"], [])
        self.assertEqual(item["validation_warnings"], ["partial_charge_due_to_configured_power_limit"])
        self.assertTrue(item["capacity_limited"])
        self.assertEqual(item["requested_energy_kwh"], 2.4)
        self.assertEqual(item["planned_energy_kwh"], 2.32)
        self.assertEqual(item["feasible_energy_kwh"], 2.32)
        self.assertEqual(item["energy_shortfall_kwh"], 0.08)
        self.assertEqual(item["power_w"], 2400)
        self.assertEqual(item["average_required_power_w"], 2482.8)
        self.assertLess(item["target_soc"], 57.7)
        self.assertEqual(item["target_soc"], 56.6)
        self.assertEqual(item["planned_end_time"], (START + timedelta(hours=9)).isoformat())
        self.assertEqual(item["max_runtime_h"], 1.0)
        self.assertEqual(item["expected_energy_kwh"], 2.32)

    def test_normal_charge_window_is_unchanged(self):
        item = bridge._build_candidate(
            segment(offset=8, hours=1, energy=1.2),
            START, 2400, 2400, 7.2, 92.0, 92.0,
        )
        self.assertTrue(item["valid"])
        self.assertFalse(item["capacity_limited"])
        self.assertEqual(item["planned_energy_kwh"], 1.2)
        self.assertEqual(item["requested_energy_kwh"], 1.2)
        self.assertEqual(item["energy_shortfall_kwh"], 0)
        self.assertEqual(item["validation_warnings"], [])

    def test_no_expanding_price_window_or_increasing_configured_power(self):
        item = self._make()
        self.assertEqual(item["power_w"], item["power_limit_w"])
        self.assertLessEqual(item["planned_energy_kwh"], 2400 * (58 / 60) / 1000)
        self.assertEqual(item["start_time"], (START + timedelta(hours=8)).isoformat())

    def test_too_small_partial_window_is_not_marked_valid(self):
        item = bridge._build_candidate(
            segment(offset=8, hours=1, energy=2.4),
            START + timedelta(hours=8, minutes=59),
            2400, 2400, 7.2, 92.0, 92.0,
        )
        self.assertFalse(item["valid"])
        self.assertIn("invalid_power", item["validation_reasons"])
        self.assertFalse(item["capacity_limited"])

    def test_missing_soc_remains_a_blocker_even_if_power_limited(self):
        item = bridge._build_candidate(
            segment(offset=8, hours=1, energy=2.4, soc=None),
            START, 2400, 2400, 7.2, 92.0, 92.0,
        )
        self.assertFalse(item["valid"])
        self.assertIn("invalid_target_soc", item["validation_reasons"])


class BridgeSafetyTests(unittest.TestCase):
    def run_bridge(self, *parts, **kw):
        return bridge.build_planner_action_bridge(
            snapshot(*parts, **kw), now=START + timedelta(seconds=20)
        )

    def test_live_reproduction_9_candidates_one_overlimit_becomes_partial(self):
        parts = [
            segment(offset=0, hours=7, energy=5.09, soc=5.0),
            segment(offset=8, hours=1, energy=2.4, soc=27),
            segment(offset=15, hours=6, energy=8.435, soc=12),
            segment(offset=25, hours=3, energy=5.868, soc=45.5),
            segment(offset=41, hours=2, energy=3.971, soc=40.7),
            segment(offset=44, hours=2, energy=1.212, soc=86),
            segment(offset=52, hours=1, energy=0.365, soc=15.1),
            segment(offset=54, hours=5, energy=7.936, soc=7.3),
            segment(offset=65, hours=2, energy=4.591, soc=29),
        ]
        result = self.run_bridge(*parts)
        self.assertTrue(result["auto_bridge_valid"])
        self.assertEqual(result["auto_bridge_candidate_count"], 9)
        self.assertEqual(result["auto_bridge_invalid_candidate_count"], 0)
        self.assertEqual(result["auto_bridge_capacity_limited_count"], 1)
        self.assertEqual(result["auto_bridge_unmet_requested_energy_kwh"], 0.08)
        self.assertEqual(result["auto_bridge_slot_preview_count"], 2)
        self.assertEqual(result["auto_bridge_held_after_limited_count"], 7)
        self.assertEqual(result["auto_bridge_overflow_count"], 7)
        self.assertTrue(all(x["plan_store_write_permitted"] for x in result["auto_bridge_slot_preview"]))
        self.assertEqual([x["suggested_slot"] for x in result["auto_bridge_slot_preview"]], [1,2])
        self.assertEqual(result["auto_bridge_slot_preview"][1]["planned_energy_kwh"], 2.32)
        self.assertEqual(result["auto_bridge_slot_preview"][1]["target_soc"], 56.6)
        self.assertEqual(result["auto_bridge_status"], "ready_preview_limited_energy")

    def test_invalid_later_candidate_does_not_block_safe_prefix(self):
        result = self.run_bridge(
            segment(offset=0, hours=1, energy=0.3, soc=18),
            segment(offset=2, hours=1, energy=0.3, soc=None),
            segment(offset=4, hours=1, energy=0.3, soc=30),
        )
        self.assertTrue(result["auto_bridge_valid"])
        self.assertEqual(result["auto_bridge_status"], "ready_preview_before_invalid_candidate")
        self.assertEqual(result["auto_bridge_invalid_candidate_count"], 1)
        self.assertEqual(result["auto_bridge_held_after_invalid_count"], 1)
        self.assertEqual(result["auto_bridge_slot_preview_count"], 1)
        self.assertEqual(result["auto_bridge_slot_preview"][0]["suggested_slot"], 1)
        self.assertEqual(result["auto_bridge_invalid_candidates"][0]["validation_reasons"], ["invalid_target_soc"])

    def test_invalid_first_candidate_fails_closed(self):
        result = self.run_bridge(
            segment(offset=0, hours=1, energy=0.3, soc=None),
            segment(offset=2, hours=1, energy=0.3, soc=30),
        )
        self.assertFalse(result["auto_bridge_valid"])
        self.assertEqual(result["auto_bridge_status"], "blocked_first_candidate_invalid")
        self.assertEqual(result["auto_bridge_slot_preview_count"], 0)

    def test_limited_action_holds_dependent_future_actions(self):
        result = self.run_bridge(
            segment(offset=0, hours=1, energy=0.3, soc=18),
            segment(offset=2, hours=1, energy=2.4, soc=27),
            segment(offset=4, hours=1, energy=0.3, soc=30),
        )
        self.assertTrue(result["auto_bridge_valid"])
        self.assertEqual(result["auto_bridge_slot_preview_count"], 2)
        self.assertEqual(result["auto_bridge_held_after_limited_count"], 1)
        self.assertTrue(all(x["plan_store_write_permitted"] for x in result["auto_bridge_slot_preview"]))
        self.assertFalse(any(x["start_time"] == (START + timedelta(hours=4)).isoformat() for x in result["auto_bridge_slot_preview"]))

    def test_manual_pending_slot_is_never_overwritten(self):
        manual = {
            1: {"action": "laden", "status": "wachtend",
                "lifecycle_status": "pending", "origin": "manual"},
            2: {"action": "geen", "status": "leeg",
                "lifecycle_status": "concept", "origin": "manual"},
        }
        result = self.run_bridge(
            segment(offset=0, hours=1, energy=0.3, soc=18),
            slots=manual
        )
        self.assertTrue(result["auto_bridge_valid"])
        self.assertEqual(result["auto_bridge_slot_preview"][0]["suggested_slot"], 2)
        self.assertEqual(result["auto_bridge_slot_preview"][0]["plan_store_write_permitted"], True)

    def test_unmodified_normal_3_slot_capacity(self):
        result = self.run_bridge(
            segment(offset=0, hours=1, energy=0.3),
            segment(offset=2, hours=1, energy=0.3),
            segment(offset=4, hours=1, energy=0.3),
            segment(offset=6, hours=1, energy=0.3),
        )
        self.assertTrue(result["auto_bridge_valid"])
        self.assertEqual(result["auto_bridge_capacity_limited_count"], 0)
        self.assertEqual(result["auto_bridge_slot_preview_count"], 3)
        self.assertEqual(result["auto_bridge_overflow_count"], 1)

    def test_planner_policy_files_remain_byte_frozen(self):
        import hashlib
        hashes = {
            "energy_need.py": "9d7dd824a0f9e5cb3835705326b4037b1ef45e9b549a17d138bb859cd99e9864",
            "planner_preview.py": "f7f453c6f48dd72514604e2367c69cdefc4fdadad6c7004d5f38647aecb3eb38",
            "planner_72h.py": "71f6247a898ec8c1ffcf765534c83d485c6386fe8ccbdfcc465efa75c632be34",
        }
        for name, digest in hashes.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((COMPONENT / name).read_bytes()).hexdigest(), digest)

    def test_alpha83_upgrade_requires_one_explicit_automatic_rearm(self):
        arm = (COMPONENT / "switch.py").read_text(encoding="utf-8")
        const = (COMPONENT / "const.py").read_text(encoding="utf-8")
        self.assertIn('AUTOMATIC_ARM_CONTRACT_VERSION = "alpha83_bridge_feasible_v1"', const)
        self.assertIn(
            'previous.attributes.get("arm_contract_version") == AUTOMATIC_ARM_CONTRACT_VERSION',
            arm,
        )
        self.assertIn('"arm_contract_version": AUTOMATIC_ARM_CONTRACT_VERSION', arm)
        self.assertIn('await self.coordinator.async_set_auto_execution_armed(armed)', arm)
        self.assertIn('await self.coordinator.async_set_auto_execution_armed(True)', arm)

    def test_coordinator_gate_does_not_globally_reject_later_invalid(self):
        s = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('bool(data.get("auto_bridge_valid"))', s)
        self.assertNotIn('and not int(data.get("auto_bridge_invalid_candidate_count") or 0)', s)
        self.assertIn('if not proposal.get("plan_store_write_permitted"):', s)
        self.assertIn('if not proposal.get("scheduler_handoff_permitted"):', s)


if __name__ == "__main__":
    unittest.main()
