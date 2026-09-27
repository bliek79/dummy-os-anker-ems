from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "anker_ems"
PACKAGE = "alpha81_anker_ems_testpkg"
START = datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc)

POLICY_HASHES = {
    "energy_need.py": "9d7dd824a0f9e5cb3835705326b4037b1ef45e9b549a17d138bb859cd99e9864",
    "planner_preview.py": "f7f453c6f48dd72514604e2367c69cdefc4fdadad6c7004d5f38647aecb3eb38",
    "planner_72h.py": "71f6247a898ec8c1ffcf765534c83d485c6386fe8ccbdfcc465efa75c632be34",
}


def _install_homeassistant_dt_stub() -> None:
    ha = types.ModuleType("homeassistant")
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
    dt.UTC = timezone.utc
    dt.DEFAULT_TIME_ZONE = timezone.utc
    dt.utcnow = lambda: datetime.now(timezone.utc)
    dt.now = lambda: datetime.now(timezone.utc)
    dt.parse_datetime = lambda value: datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )
    util.dt = dt
    ha.util = util
    sys.modules.setdefault("homeassistant", ha)
    sys.modules.setdefault("homeassistant.util", util)
    sys.modules.setdefault("homeassistant.util.dt", dt)


def _load(name: str, filename: str):
    _install_homeassistant_dt_stub()
    if PACKAGE not in sys.modules:
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(COMPONENT)]
        sys.modules[PACKAGE] = package
    full_name = f"{PACKAGE}.{name}"
    spec = importlib.util.spec_from_file_location(full_name, COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


const = _load("const", "const.py")
energy_need = _load("energy_need", "energy_need.py")
planner_preview = _load("planner_preview", "planner_preview.py")
planner_72h = _load("planner_72h", "planner_72h.py")
planner_multirate = _load("planner_multirate", "planner_multirate.py")


def _forecast() -> list[dict]:
    rows = []
    for index in range(72):
        price = 0.34
        if index in {6, 7}:
            price = 0.19
        if index in {18, 19, 20}:
            price = 0.08
        home = 0.16 if index < 40 else 0.10
        solar = 0.0
        if index in range(28, 34):
            solar = 0.55
        rows.append(
            {
                "time": (START + timedelta(hours=index)).isoformat(),
                "home_consumption_kwh": home,
                "solar_kwh": solar,
                "price": price,
                "import_price": price,
                "export_price": price - 0.10,
                "price_source": "test",
                "import_price_source": "test",
                "export_price_source": "test",
            }
        )
    return rows


class Alpha81MultiRateRuntimeTests(unittest.TestCase):
    def test_alpha80_policy_files_are_byte_frozen(self) -> None:
        for filename, expected in POLICY_HASHES.items():
            actual = hashlib.sha256((COMPONENT / filename).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, filename)

    def test_bundle_is_exact_alpha80_policy_parity(self) -> None:
        forecast = _forecast()
        kwargs = {
            "forecast": forecast,
            "soc": 54.0,
            "safety_reserve_percent": 7.0,
            "charge_efficiency_percent": 92.0,
            "discharge_efficiency_percent": 92.0,
            "minimum_trade_margin": 0.10,
            "max_charge_power_w": 3200,
            "max_discharge_power_w": 3200,
            "reference": START,
        }
        bundle = planner_multirate.compute_alpha80_planner_bundle(**kwargs)

        need = energy_need.build_energy_need_analysis(
            forecast, 54.0, 7.0, now=START
        )
        preview = planner_preview.build_planner_preview(
            forecast,
            need,
            54.0,
            92.0,
            92.0,
            0.10,
            max_charge_power_w=3200,
            max_discharge_power_w=3200,
            now=START,
        )
        plan = planner_72h.build_72h_plan_preview(
            forecast,
            need,
            preview,
            54.0,
            92.0,
            92.0,
            execution_buffer_percent=const.DEFAULT_AUTO_EXECUTION_BUFFER_PERCENT,
            max_charge_power_w=3200,
            max_discharge_power_w=3200,
            now=START,
        )

        self.assertEqual(bundle["energy_need"], need)
        self.assertEqual(bundle["planner_preview"], preview)
        self.assertEqual(bundle["plan72"], plan)

    def test_native_quarter_cycle_and_signature_are_stable(self) -> None:
        forecast = _forecast()
        base = dict(
            forecast=forecast,
            soc=54.0,
            safety_reserve_percent=7.0,
            charge_efficiency_percent=92.0,
            discharge_efficiency_percent=92.0,
            minimum_trade_margin=0.10,
            max_charge_power_w=3200,
            max_discharge_power_w=3200,
        )
        ref_a = START + timedelta(minutes=1)
        ref_b = START + timedelta(minutes=14, seconds=59)
        ref_c = START + timedelta(minutes=15)

        self.assertEqual(
            planner_multirate.planner_cycle_id(ref_a),
            planner_multirate.planner_cycle_id(ref_b),
        )
        self.assertNotEqual(
            planner_multirate.planner_cycle_id(ref_a),
            planner_multirate.planner_cycle_id(ref_c),
        )

        sig_a = planner_multirate.planner_input_signature(**base, reference=ref_a)
        sig_b = planner_multirate.planner_input_signature(**base, reference=ref_b)
        sig_c = planner_multirate.planner_input_signature(**base, reference=ref_c)
        sig_soc = planner_multirate.planner_input_signature(
            **{**base, "soc": 53.0}, reference=ref_a
        )
        self.assertEqual(sig_a, sig_b)
        self.assertNotEqual(sig_a, sig_c)
        self.assertNotEqual(sig_a, sig_soc)

    def test_coordinator_fast_path_no_longer_calls_policy_functions(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn("update_interval=timedelta(seconds=10)", source)
        self.assertNotIn("build_energy_need_analysis(", source)
        self.assertNotIn("build_planner_preview(", source)
        self.assertNotIn("build_72h_plan_preview(", source)
        self.assertIn("compute_alpha80_planner_bundle", source)
        self.assertIn("async_add_executor_job", source)
        self.assertIn("_planner_pending_request", source)
        self.assertIn("generation != self._planner_generation", source)
        self.assertIn('"native_quarter_plus_events"', source)

    def test_multirate_contract_keeps_alpha80_policy_identity(self) -> None:
        self.assertEqual(
            planner_multirate.MULTIRATE_RUNTIME_VERSION,
            "alpha81_multirate_runtime_v1",
        )
        self.assertEqual(
            planner_multirate.PLANNER_POLICY_VERSION,
            "alpha80_cheapest_energy_safety_v1",
        )
        self.assertTrue(planner_multirate.is_planner_trigger("quarter_boundary"))
        self.assertTrue(planner_multirate.is_planner_trigger("source_content_changed"))
        self.assertFalse(planner_multirate.is_planner_trigger("soc_state_change"))


if __name__ == "__main__":
    unittest.main()
