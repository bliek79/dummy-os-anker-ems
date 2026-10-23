"""Alpha82: dynamic Anker charger limit + explicit, non-actuating emergency reset."""
from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "anker_ems"


def load_pure(name):
    path = COMPONENT / (name + ".py")
    spec = importlib.util.spec_from_file_location("alpha82_" + name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


power = load_pure("charge_power_limit")
reset = load_pure("execution_status_reset")


class PowerLimitTests(unittest.TestCase):
    def test_deep_discharge_2620_is_reduced_to_battery_2408(self):
        decision = power.choose_charge_power(2620, {"min": 0, "max": 2408, "step": 1}, configured_max_w=3500)
        self.assertEqual((decision.planned_w, decision.applied_w), (2620, 2408))
        self.assertTrue(decision.limited)

    def test_normal_battery_does_not_degrade_valid_plan(self):
        self.assertEqual(power.choose_charge_power(2620, {"min": 0, "max": 3500}, configured_max_w=3500).applied_w, 2620)

    def test_dynamic_limit_can_change_without_policy_change(self):
        limits = {"min": 0, "max": 2408, "step": 1}
        self.assertEqual(power.choose_charge_power(2620, limits, configured_max_w=3500).applied_w, 2408)
        limits["max"] = 2075
        self.assertEqual(power.choose_charge_power(2620, limits, configured_max_w=3500).applied_w, 2075)
        limits["max"] = 3000
        self.assertEqual(power.choose_charge_power(2620, limits, configured_max_w=3500).applied_w, 2620)

    def test_number_step_and_offset_are_respected(self):
        self.assertEqual(power.choose_charge_power(2620, {"min": 100, "max": 2408, "step": 25}, configured_max_w=3500).applied_w, 2400)

    def test_missing_invalid_or_too_low_hardware_limit_fails_closed(self):
        for data in ({}, {"max": None}, {"max": "unavailable"}, {"max": float("nan")}, {"min": 0, "max": 90}, {"min": 2500, "max": 2408}, {"max": 2408, "step": 0}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                power.choose_charge_power(2620, data, configured_max_w=3500)

    def test_never_overrides_configured_ems_maximum(self):
        with self.assertRaises(ValueError):
            power.choose_charge_power(2620, {"max": 3500}, configured_max_w=2400)
        self.assertEqual(power.choose_charge_power(2200, {"max": 2408}, configured_max_w=2200).applied_w, 2200)


class ResetPolicyTests(unittest.TestCase):
    def setUp(self):
        self.execution = {"active": False, "auto_mode_switch_active": False, "status": "emergency_stopped"}
        self.test = {"active": False}

    def can_reset(self, **kwargs):
        args = {"automatic_armed": False, "operating_mode": "self_consumption", "power_state": "0"}
        args.update(kwargs)
        return reset.check_execution_status_reset(self.execution, self.test, **args)

    def test_finished_emergency_with_zero_or_unavailable_control(self):
        self.assertIsNone(self.can_reset())
        self.assertIsNone(self.can_reset(power_state="unavailable"))

    def test_no_restart_or_arm_can_be_hidden(self):
        for kwargs in ({"automatic_armed": True}, {"operating_mode": "third_party_control"}, {"operating_mode": None}, {"power_state": "350"}, {"power_state": "invalid"}):
            with self.subTest(kwargs=kwargs):
                self.assertIsNotNone(self.can_reset(**kwargs))
        self.execution["active"] = True
        self.assertIsNotNone(self.can_reset())
        self.execution["active"] = False
        self.execution["auto_mode_switch_active"] = True
        self.assertIsNotNone(self.can_reset())
        self.execution["auto_mode_switch_active"] = False
        self.test["active"] = True
        self.assertIsNotNone(self.can_reset())
        self.test["active"] = False
        self.execution["status"] = "stop_error"
        self.assertIsNotNone(self.can_reset())


class EmergencyError(Exception):
    pass


def isolated_controller_type():
    """Execute actual selected controller method bodies without Home Assistant."""
    src = ast.parse((COMPONENT / "execution.py").read_text(encoding="utf-8"))
    controller = next(n for n in src.body if isinstance(n, ast.ClassDef) and n.name == "AnkerEmsExecutionController")
    names = {"_live_charge_power_decision", "_async_write_charge_power", "async_reset_emergency_status"}
    methods = [n for n in controller.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name in names]
    assert len(methods) == 3
    cls = ast.ClassDef(name="TestableController", bases=[], keywords=[], body=methods, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    ns = {"choose_charge_power": power.choose_charge_power,
          "check_execution_status_reset": reset.check_execution_status_reset,
          "HomeAssistantError": EmergencyError,
          "dt_util": SimpleNamespace(now=lambda: datetime(2026, 10, 23, tzinfo=timezone.utc))}
    exec(compile(module, "<actual EMS controller methods>", "exec"), ns)
    return ns["TestableController"]


class ControllerRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        C = isolated_controller_type()
        self.controller = C()
        self.controller._state = {
            "active": False, "status": "emergency_stopped",
            "reason": "automatic_start_failed: old_max", "stop_at": "2026-10-22T14:33:28+02:00",
            "last_result": "emergency_stopped", "automatic_run_history": [{"result": "emergency_stopped"}],
            "automatic_last_reason": "old_max", "origin": "automatic_72h_planner",
            "power_w": 2620, "automatic_last_limit_adjustment_count": 0,
        }
        self.controller._stop_lock = asyncio.Lock()
        self.controller.data = dict(self.controller._state)
        self.controller._async_save = self.save
        self.controller._trace_automatic = self.trace
        self.calls = []
        self.errors = []
        self.saved = 0
        self.state = SimpleNamespace(state="0", attributes={"min": 0, "max": 2408, "step": 1})
        self.mode = SimpleNamespace(state="self_consumption", attributes={})
        self.states = {"number.test_charging": self.state, "select.test_mode": self.mode}
        self.controller.hass = SimpleNamespace(states=SimpleNamespace(get=self.states.get))
        self.controller._coordinator = SimpleNamespace(
            max_charge_power_w=3500, auto_execution_armed=False,
            authority_fence=SimpleNamespace(async_call=self.write_power),
            physical_test=SimpleNamespace(data={"active": False}),
            control_entity_ids={"power_setpoint": "number.test_charging", "operating_mode": "select.test_mode"},
            async_refresh=self.refresh,
        )

    async def save(self):
        self.saved += 1

    async def refresh(self):
        pass

    def trace(self, stage, detail):
        self.calls.append(("trace", stage, detail))

    async def write_power(self, domain, action, data, *, target, blocking):
        assert domain == "number" and action == "set_value" and blocking
        requested = data["value"]
        self.calls.append(("power", requested))
        if self.errors:
            effect = self.errors.pop(0)
            if effect is not None:
                if isinstance(effect, tuple):
                    self.state.attributes["max"] = effect[1]
                raise ValueError("Battery rejected old setpoint")
        if requested > self.state.attributes["max"]:
            raise ValueError("Above Anker max")
        self.state.state = str(requested)

    async def test_real_write_uses_2408_but_records_2620(self):
        result = await self.controller._async_write_charge_power(2620, "number.test_charging", phase="start")
        self.assertEqual(result, 2408)
        self.assertIn(("power", 2408), self.calls)
        self.assertEqual(self.controller._state["power_w"], 2408)
        self.assertEqual(self.controller._state["planned_power_w"], 2620)
        self.assertEqual(self.controller._state["charge_limit_status"], "limited")
        self.assertEqual(self.controller._state["automatic_last_applied_power_w"], 2408)
        self.assertGreater(self.saved, 0)

    async def test_one_retry_only_when_actual_max_shrinks(self):
        self.errors = [("reject", 2100)]
        result = await self.controller._async_write_charge_power(2620, "number.test_charging", phase="start")
        self.assertEqual(result, 2100)
        self.assertEqual([x[1] for x in self.calls if x[0] == "power"], [2408, 2100])

    async def test_same_max_does_not_retry_a_rejected_write(self):
        self.errors = ["reject"]
        with self.assertRaises(ValueError):
            await self.controller._async_write_charge_power(2620, "number.test_charging", phase="start")
        self.assertEqual(len([x for x in self.calls if x[0] == "power"]), 1)

    async def test_completed_reset_preserves_old_emergency_audit(self):
        before = self.controller._state["automatic_run_history"].copy()
        await self.controller.async_reset_emergency_status()
        state = self.controller._state
        self.assertEqual(state["status"], "idle")
        self.assertEqual(state["reason"], "Noodstop bevestigd; geen EMS-uitvoering actief")
        self.assertEqual(state["last_result"], "emergency_stopped")
        self.assertEqual(state["automatic_run_history"], before)
        self.assertEqual(state["emergency_acknowledged_reason"], "automatic_start_failed: old_max")
        self.assertEqual(self.calls, [])

    async def test_reset_does_not_override_armed_or_running_state(self):
        self.controller._coordinator.auto_execution_armed = True
        with self.assertRaises(EmergencyError):
            await self.controller.async_reset_emergency_status()
        self.assertEqual(self.controller._state["status"], "emergency_stopped")
        self.assertEqual(self.calls, [])


class WiringTests(unittest.TestCase):
    def test_platform_service_and_dashboard_button_are_wired(self):
        const = (COMPONENT / "const.py").read_text()
        init = (COMPONENT / "__init__.py").read_text()
        button = (COMPONENT / "button.py").read_text()
        self.assertIn('"button"', const)
        self.assertIn("SERVICE_RESET_EXECUTION_STATUS", init)
        self.assertIn("async_reset_emergency_status()", init)
        self.assertIn("async_reset_emergency_status()", button)

    def test_planner_policy_files_remain_unchanged(self):
        import hashlib
        frozen = {
            "energy_need.py": "9d7dd824a0f9e5cb3835705326b4037b1ef45e9b549a17d138bb859cd99e9864",
            "planner_preview.py": "f7f453c6f48dd72514604e2367c69cdefc4fdadad6c7004d5f38647aecb3eb38",
            "planner_72h.py": "71f6247a898ec8c1ffcf765534c83d485c6386fe8ccbdfcc465efa75c632be34",
        }
        for name, sha in frozen.items():
            self.assertEqual(hashlib.sha256((COMPONENT / name).read_bytes()).hexdigest(), sha)


if __name__ == "__main__":
    unittest.main()
