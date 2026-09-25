from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "anker_ems"
PACKAGE = "alpha79_anker_ems_testpkg"


def _install_homeassistant_dt_stub() -> None:
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
bridge = _load("planner_action_bridge", "planner_action_bridge.py")


START = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def forecast(*, cheap_support: bool) -> list[dict]:
    rows: list[dict] = []
    for index in range(72):
        price = 0.25
        if cheap_support and index == 4:
            price = 0.05
        elif cheap_support and 9 <= index < 18:
            price = 0.45

        # First demonstrably usable solar block starts at +18 h.
        solar = 1.2 if 18 <= index <= 20 else 0.0
        rows.append(
            {
                "time": (START.replace() + __import__("datetime").timedelta(hours=index)).isoformat(),
                "home_consumption_kwh": 0.8,
                "solar_kwh": solar,
                "price": price,
                "import_price": price,
                "export_price": price,
                "price_source": "test",
                "import_price_source": "test",
                "export_price_source": "test",
            }
        )
    return rows


def run_chain(rows: list[dict]) -> tuple[dict, dict, dict]:
    need = energy_need.build_energy_need_analysis(
        rows,
        100.0,
        7.0,
        now=START,
        discharge_efficiency_percent=92.0,
    )
    preview = planner_preview.build_planner_preview(
        rows,
        need,
        100.0,
        92.0,
        92.0,
        0.10,
        max_charge_power_w=3200,
        max_discharge_power_w=3200,
        now=START,
    )
    plan = planner_72h.build_72h_plan_preview(
        rows,
        need,
        preview,
        100.0,
        92.0,
        92.0,
        execution_buffer_percent=2.0,
        max_charge_power_w=3200,
        max_discharge_power_w=3200,
        now=START,
    )
    return need, preview, plan


class Alpha79SelfConsumptionPolicyTests(unittest.TestCase):
    def test_low_solar_need_does_not_create_fictitious_100_percent_floor(self) -> None:
        need, preview, plan = run_chain(forecast(cheap_support=False))

        self.assertTrue(need["energy_need_valid"])
        self.assertGreater(need["energy_need_until_solar_kwh"], const.DEFAULT_BATTERY_CAPACITY_KWH)
        self.assertFalse(need["energy_need_reserve_enforceable_in_self_consumption"])

        first = plan["auto_plan_72h_plan"][0]
        self.assertEqual(first["reserve_floor_soc"], 12.0)
        self.assertEqual(first["execution_reserve_floor_soc"], 14.0)
        self.assertGreater(first["discharge_to_home_kwh"], 0.0)
        self.assertLess(first["soc_end"], 100.0)
        self.assertGreater(first["planning_need_soc_equivalent"], first["reserve_floor_soc"])

    def test_flat_prices_accept_natural_discharge_to_device_minimum(self) -> None:
        _need, preview, plan = run_chain(forecast(cheap_support=False))

        self.assertTrue(preview["planner_preview_support_charge_needed"])
        self.assertFalse(preview["planner_preview_support_charge_economic"])
        self.assertEqual(preview["planner_preview_support_charge_hours"], [])
        self.assertAlmostEqual(plan["auto_plan_72h_min_soc"], 5.0, places=1)
        self.assertGreater(plan["auto_plan_72h_grid_import_for_home_kwh"], 0.0)
        self.assertTrue(plan["auto_plan_72h_execution_buffer_safe"])
        self.assertEqual(plan["auto_plan_72h_execution_buffer_breach_hours"], 0)

    def test_cheaper_earlier_window_creates_limited_support_charge(self) -> None:
        need, preview, plan = run_chain(forecast(cheap_support=True))

        self.assertGreater(need["energy_need_unavoidable_grid_import_kwh"], 0.0)
        self.assertTrue(preview["planner_preview_support_charge_needed"])
        self.assertTrue(preview["planner_preview_support_charge_economic"])
        self.assertGreater(preview["planner_preview_support_charge_kwh"], 0.0)
        self.assertGreater(preview["planner_preview_support_expected_savings_eur"], 0.0)
        self.assertGreater(plan["auto_plan_72h_grid_support_charge_kwh"], 0.0)
        self.assertTrue(
            any(
                "zelfconsumptie_bijladen" in row["action"]
                for row in plan["auto_plan_72h_plan"]
            )
        )

    def test_bridge_promotes_support_charge_but_not_home_discharge(self) -> None:
        support = bridge._forced_row_action(
            {
                "charge_from_grid_safety_kwh": 0.0,
                "charge_from_grid_support_kwh": 0.5,
                "charge_from_grid_trade_kwh": 0.0,
                "discharge_to_grid_kwh": 0.0,
                "discharge_to_home_kwh": 0.8,
            }
        )
        self.assertEqual(support, ("laden", "zelfconsumptie_bijladen", 0.5))

        natural = bridge._forced_row_action(
            {
                "charge_from_grid_safety_kwh": 0.0,
                "charge_from_grid_support_kwh": 0.0,
                "charge_from_grid_trade_kwh": 0.0,
                "discharge_to_grid_kwh": 0.0,
                "discharge_to_home_kwh": 0.8,
            }
        )
        self.assertIsNone(natural)


if __name__ == "__main__":
    unittest.main()
