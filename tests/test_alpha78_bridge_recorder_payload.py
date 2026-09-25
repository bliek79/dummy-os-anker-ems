from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SENSOR = ROOT / "custom_components" / "anker_ems" / "sensor.py"
RECORDER_BUDGET_BYTES = 10 * 1024


def _sensor_source() -> str:
    return SENSOR.read_text(encoding="utf-8")


def _compile_function(name: str):
    tree = ast.parse(_sensor_source())
    fn = next(
        deepcopy(node)
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    fn.decorator_list = []
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, f"<sensor.py:{name}>", "exec"), namespace)
    return namespace[name]


def _unrecorded_attributes() -> frozenset[str]:
    tree = ast.parse(_sensor_source())
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AnkerEmsSensor"
    )
    assignment = next(
        node for node in cls.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_unrecorded_attributes"
            for target in node.targets
        )
    )
    value = assignment.value
    assert isinstance(value, ast.Call)
    assert isinstance(value.func, ast.Name) and value.func.id == "frozenset"
    return frozenset(ast.literal_eval(value.args[0]))


def _recorded_size(attributes: dict[str, Any]) -> int:
    unrecorded = _unrecorded_attributes()
    recorder_bound = {
        key: value for key, value in attributes.items() if key not in unrecorded
    }
    return len(
        json.dumps(
            recorder_bound,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    )


def _candidate(index: int) -> dict[str, Any]:
    return {
        "identity": f"candidate-{index}-" + "x" * 64,
        "action": "laden",
        "purpose": "veiligheidsladen",
        "start_time": f"2026-09-25T{index:02d}:00:00+00:00",
        "end_time": f"2026-09-25T{index + 1:02d}:00:00+00:00",
        "power_w": 3200,
        "target_soc": 80,
        "expected_energy_kwh": 1.234,
        "source_hours": [f"2026-09-25T{h:02d}:00:00+00:00" for h in range(24)],
        "reason": "x" * 160,
    }


def _slot(index: int) -> dict[str, Any]:
    return {
        "suggested_slot": index,
        "planner_identity": f"slot-{index}-" + "x" * 64,
        "planner_signature": "x" * 128,
        "action": "laden",
        "purpose": "veiligheidsladen",
        "start_time": f"2026-09-25T0{index}:00:00+00:00",
        "planned_end_time": f"2026-09-25T0{index + 1}:00:00+00:00",
        "power_w": 3200,
        "target_soc": 80,
        "planned_energy_kwh": 1.234,
        "scheduler_handoff_permitted": True,
        "plan_store_write_permitted": True,
        "diagnostic": "x" * 320,
    }


def _representative_data() -> dict[str, Any]:
    data: dict[str, Any] = {
        "auto_bridge_valid": True,
        "auto_bridge_reason": "ready",
        "auto_bridge_candidate_count": 24,
        "auto_bridge_slot_preview_count": 3,
        "auto_bridge_overflow_count": 21,
        "auto_bridge_invalid_candidate_count": 0,
        "auto_bridge_slot_capacity": 3,
        "auto_bridge_available_manual_slots": [1, 2, 3],
        "auto_bridge_manual_slots": [
            {"slot": i, "status": "leeg", "detail": "x" * 120} for i in range(1, 4)
        ],
        "auto_bridge_candidates": [_candidate(i) for i in range(24)],
        "auto_bridge_slot_preview": [_slot(i) for i in range(1, 4)],
        "auto_bridge_suppressed_safety_charge_hours": [
            f"2026-09-25T{h:02d}:00:00+00:00" for h in range(24)
        ],
        "auto_bridge_plan_store_written_slots": [1, 2, 3],
        "auto_bridge_plan_store_cleared_slots": [],
        "auto_bridge_plan_store_skipped_slots": [],
        "auto_bridge_scheduler_handoff_slots": [1, 2, 3],
        "auto_bridge_scheduler_handoff_skipped_slots": [],
        "auto_expired_released_slots": [],
        "auto_expired_scheduler_slots": [],
    }
    scalar_defaults = {
        "auto_bridge_rolling_window": True,
        "electrical_profile": "dedicated_group",
        "max_charge_power_w": 3200,
        "max_discharge_power_w": 3200,
        "auto_bridge_manual_slot_conflict": False,
        "auto_bridge_plan_store_write_enabled": True,
        "auto_bridge_plan_store_write_gate_open": True,
        "auto_bridge_plan_store_write_changed": True,
        "auto_bridge_scheduler_handoff_enabled": True,
        "auto_bridge_scheduler_handoff_gate_open": True,
        "auto_bridge_scheduler_handoff_changed": True,
        "auto_prestart_enabled": True,
        "auto_prestart_required": True,
        "auto_prestart_safe": True,
        "auto_prestart_status": "ready",
        "auto_prestart_reason": "safe",
        "auto_prestart_selected_slot": 1,
        "auto_prestart_current_identity_match": True,
        "auto_prestart_current_signature_match": True,
        "auto_prestart_diagnostic_status": "ready",
        "auto_prestart_diagnostic_safe": True,
        "auto_prestart_diagnostic_phase": "decision_window",
        "auto_prestart_diagnostic_minutes_to_start": 4.5,
        "auto_safety_handoff_enabled": True,
        "auto_safety_handoff_required": True,
        "auto_safety_handoff_safe": True,
        "auto_safety_handoff_status": "ready",
        "auto_safety_handoff_reason": "safe",
        "auto_execution_handoff_enabled": True,
        "auto_execution_handoff_required": True,
        "auto_execution_handoff_ready": True,
        "auto_execution_handoff_status": "ready",
        "auto_execution_handoff_reason": "safe",
        "auto_final_revalidation_enabled": True,
        "auto_final_revalidation_required": True,
        "auto_final_revalidation_safe": True,
        "auto_final_revalidation_status": "ready",
        "auto_final_revalidation_reason": "safe",
        "auto_final_revalidation_checked_at": "2026-09-25T06:00:00+00:00",
        "auto_final_revalidation_mode_switch_required": True,
        "auto_mode_switch_preview_enabled": True,
        "auto_mode_switch_preview_required": True,
        "auto_mode_switch_preview_ready": True,
        "auto_mode_switch_preview_status": "ready",
        "auto_mode_switch_preview_reason": "safe",
        "auto_mode_switch_preview_current_mode": "self_consumption",
        "auto_mode_switch_preview_power_setpoint_w": 0,
        "execution_auto_mode_switch_active": False,
        "execution_auto_mode_switch_status": "idle",
        "execution_auto_mode_switch_reason": "waiting",
        "execution_control_path_ready": True,
        "execution_control_path_ready_reason": "stable",
        "execution_control_path_stable_seconds": 60,
        "execution_control_path_required_stable_seconds": 60,
        "auto_bridge_execution_enabled": True,
        "auto_bridge_observational_only": False,
        "auto_bridge_note": "alpha78 recorder payload fixture",
    }
    data.update(scalar_defaults)
    return data


def test_bridge_public_contracts_do_not_duplicate_heavy_payloads() -> None:
    data = _representative_data()
    status = _compile_function("_auto_bridge_status_attrs")(data)
    candidates = _compile_function("_auto_bridge_candidate_attrs")(data)
    slots = _compile_function("_auto_bridge_slots_attrs")(data)

    assert "candidates" not in status
    assert "slot_preview" not in status
    assert "slot_preview" not in candidates
    assert "candidates" not in slots
    assert candidates["candidates"] == data["auto_bridge_candidates"]
    assert slots["slot_preview"] == data["auto_bridge_slot_preview"]


def test_bridge_heavy_live_arrays_are_excluded_from_recorder() -> None:
    unrecorded = _unrecorded_attributes()
    assert {
        "candidates",
        "slot_preview",
        "manual_slots",
        "suppressed_safety_charge_hours",
    } <= unrecorded


def test_each_bridge_recorder_payload_stays_below_10_kib() -> None:
    data = _representative_data()
    functions = (
        "_auto_bridge_status_attrs",
        "_auto_bridge_candidate_attrs",
        "_auto_bridge_slots_attrs",
    )
    for name in functions:
        attrs = _compile_function(name)(data)
        size = _recorded_size(attrs)
        assert size <= RECORDER_BUDGET_BYTES, (
            f"{name} Recorder payload is {size} bytes; "
            f"budget is {RECORDER_BUDGET_BYTES} bytes"
        )


def test_bridge_fix_does_not_change_execution_or_safety_runtime() -> None:
    source = _sensor_source()
    assert 'key="auto_bridge_status"' in source
    assert 'key="auto_bridge_candidate_count"' in source
    assert 'key="auto_bridge_slot_preview_count"' in source
    assert "_auto_bridge_status_attrs" in source
    assert "_auto_bridge_candidate_attrs" in source
    assert "_auto_bridge_slots_attrs" in source

    execution = (ROOT / "custom_components" / "anker_ems" / "execution.py").read_text(
        encoding="utf-8"
    )
    coordinator = (ROOT / "custom_components" / "anker_ems" / "coordinator.py").read_text(
        encoding="utf-8"
    )
    assert "third_party_control" in execution
    assert "async_execute_automatic_plan" in execution
    assert "auto_shadow_execution_permitted" in coordinator


def test_alpha78_bridge_fix_survives_alpha79_version_bump() -> None:
    const = (ROOT / "custom_components" / "anker_ems" / "const.py").read_text(encoding="utf-8")
    manifest = (ROOT / "custom_components" / "anker_ems" / "manifest.json").read_text(encoding="utf-8")
    assert 'VERSION = "0.0.1-alpha.79"' in const
    assert '"version": "0.0.1-alpha.79"' in manifest
