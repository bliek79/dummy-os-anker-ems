"""Regression tests: DOEMS R6 adapter is read-only and fail-closed."""
from types import SimpleNamespace

import pytest

from custom_components.anker_ems.doems_r6_provider import read_doems_r6_publication
from custom_components.anker_ems.doems_ingress import validate_doems_proposals


def _plan():
    return {
        "origin": "automatic_72h_planner", "action": "laden",
        "execution_mode": "gepland", "max_start_delay_min": 10,
        "planner_identity": "charge-1", "planner_signature": "sig-1",
        "power_w": 1900, "target_soc": 70, "max_runtime_h": 1,
        "start_time": "2026-10-29T11:00:00+00:00",
        "planned_end_time": "2026-10-29T12:00:00+00:00",
    }


def _runtime(witness=True, ready=True):
    plan = _plan()
    proof = {**plan, "_doems_r6_proof": {
        "source": "published_r6_bridge", "planner_generation": 17,
        "bridge_ready": True, "planner_valid": True,
        "invalid_candidate_count": 0, "physical_execution_enabled": False,
    }}
    bridge = SimpleNamespace(
        last_result={"status": "ready" if ready else "waiting"},
        verified_published_candidate=lambda _: proof if witness else None,
    )
    return {
        "r6_slot_bridge": bridge, "planner": SimpleNamespace(_generation=17),
        "manual_plan_store": SimpleNamespace(
            get_plan=lambda slot: plan if slot == 1 else {},
        ),
    }


def test_published_plan_crosses_existing_ingress_contract():
    hass = SimpleNamespace(data={"doems": {"entry": _runtime()}})
    publication = read_doems_r6_publication(hass)
    accepted = validate_doems_proposals(
        publication["proposals"], generation=publication["generation"],
        max_charge_w=3200, max_discharge_w=3200,
    )
    assert accepted[1]["planner_identity"] == "charge-1"
    assert "_doems_r6_proof" not in accepted[1]


@pytest.mark.parametrize("runtimes", [{}, {"one": _runtime(), "two": _runtime()}])
def test_missing_or_ambiguous_doems_runtime_rejected(runtimes):
    with pytest.raises(ValueError, match="Exactly one"):
        read_doems_r6_publication(SimpleNamespace(data={"doems": runtimes}))


def test_stale_r6_witness_rejected():
    with pytest.raises(ValueError, match="witness"):
        read_doems_r6_publication(
            SimpleNamespace(data={"doems": {"entry": _runtime(witness=False)}})
        )


def test_unready_publication_rejected():
    with pytest.raises(ValueError, match="not ready"):
        read_doems_r6_publication(
            SimpleNamespace(data={"doems": {"entry": _runtime(ready=False)}})
        )
