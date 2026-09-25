from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "anker_ems"
PACKAGE = "alpha80_anker_ems_testpkg"


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

START = datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)


def rows(*, start_soc: float, home: list[float], solar: list[float], prices: list[float]):
    data = []
    for i in range(72):
        data.append(
            {
                "time": (START + timedelta(hours=i)).isoformat(),
                "home_consumption_kwh": home[i],
                "solar_kwh": solar[i],
                "price": prices[i],
                "import_price": prices[i],
                "export_price": prices[i],
                "price_source": "test",
                "import_price_source": "test",
                "export_price_source": "test",
            }
        )
    need = energy_need.build_energy_need_analysis(data, start_soc, 7.0, now=START)
    preview = planner_preview.build_planner_preview(
        data,
        need,
        start_soc,
        92.0,
        92.0,
        0.10,
        max_charge_power_w=3200,
        max_discharge_power_w=3200,
        now=START,
    )
    plan = planner_72h.build_72h_plan_preview(
        data,
        need,
        preview,
        start_soc,
        92.0,
        92.0,
        execution_buffer_percent=2.0,
        max_charge_power_w=3200,
        max_discharge_power_w=3200,
        now=START,
    )
    return need, preview, plan


class Alpha80CheapestEnergySafetyTests(unittest.TestCase):
    def test_no_usable_solar_still_keeps_horizon_planable(self) -> None:
        home = [0.15] * 72
        solar = [0.0] * 72
        prices = [0.30] * 72
        need, preview, _plan = rows(start_soc=80.0, home=home, solar=solar, prices=prices)
        self.assertTrue(need["energy_need_valid"])
        self.assertIsNone(need["energy_need_first_usable_solar"])
        self.assertEqual(preview["planner_preview_safety_reserve_target_soc"], 12.0)

    def test_solar_first_means_no_grid_safety_charge_when_route_stays_safe(self) -> None:
        home = [0.12] * 72
        solar = [0.0] * 72
        for i in range(4, 10):
            solar[i] = 0.8
        prices = [0.30] * 72
        _need, preview, plan = rows(start_soc=65.0, home=home, solar=solar, prices=prices)
        self.assertFalse(preview["planner_preview_safety_charge_needed"])
        self.assertEqual(preview["planner_preview_safety_charge_hours"], [])
        self.assertEqual(plan["auto_plan_72h_grid_safety_charge_kwh"], 0.0)

    def test_later_cheaper_window_beats_night_when_battery_can_reach_it(self) -> None:
        home = [0.15] * 72
        solar = [0.0] * 72
        prices = [0.34] * 72
        prices[6] = 0.20
        prices[18] = 0.10
        for i in range(19, 40):
            prices[i] = 0.45
        _need, preview, _plan = rows(start_soc=60.0, home=home, solar=solar, prices=prices)
        selected = preview["planner_preview_safety_charge_hours"]
        self.assertTrue(selected)
        selected_times = {item["time"] for item in selected}
        self.assertIn((START + timedelta(hours=18)).isoformat(), selected_times)
        self.assertNotIn((START + timedelta(hours=6)).isoformat(), selected_times)

    def test_night_bridge_charge_is_used_when_cheaper_midday_cannot_be_reached_safely(self) -> None:
        home = [0.25] * 72
        solar = [0.0] * 72
        prices = [0.34] * 72
        prices[6] = 0.20
        prices[18] = 0.10
        _need, preview, _plan = rows(start_soc=25.0, home=home, solar=solar, prices=prices)
        selected_times = {item["time"] for item in preview["planner_preview_safety_charge_hours"]}
        self.assertIn((START + timedelta(hours=6)).isoformat(), selected_times)

    def test_cheap_window_can_fill_battery_when_later_demand_requires_it(self) -> None:
        home = [0.05] * 72
        solar = [0.0] * 72
        prices = [0.40] * 72
        for i in range(18, 21):
            prices[i] = 0.05
        for i in range(21, 31):
            home[i] = 0.60
            prices[i] = 0.48
        _need, preview, plan = rows(start_soc=25.0, home=home, solar=solar, prices=prices)
        selected = preview["planner_preview_safety_charge_hours"]
        self.assertTrue(any(18 <= int((datetime.fromisoformat(i["time"]) - START).total_seconds() // 3600) <= 20 for i in selected))
        peak_soc = max(item["soc_end"] for item in plan["auto_plan_72h_plan"])
        self.assertGreaterEqual(peak_soc, 98.0)
        self.assertGreater(plan["auto_plan_72h_grid_safety_charge_kwh"], 0.0)

    def test_compact_public_contract_has_no_support_charge_category(self) -> None:
        sensor_text = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        bridge_text = (COMPONENT / "planner_action_bridge.py").read_text(encoding="utf-8")
        self.assertNotIn("grid_support_charge", sensor_text)
        self.assertNotIn("Self-Consumption Support Charge", sensor_text)
        self.assertNotIn("zelfconsumptie_bijladen", bridge_text)
        self.assertNotIn("charge_from_grid_support_kwh", bridge_text)


if __name__ == "__main__":
    unittest.main()
