"""Regression tests for DOEMS plan intake; never issue a battery command."""
from custom_components.anker_ems.doems_ingress import (
    validate_doems_proposals, DOEMSIngressRejected,
)
import pytest


def candidate(identity="charge-1", generation=17):
    return {
        "origin": "automatic_72h_planner", "action": "laden",
        "planner_identity": identity, "planner_signature": "sig-" + identity,
        "power_w": 1940, "target_soc": 21.6, "max_runtime_h": .5,
        "start_time": "2026-10-27T22:30:00+00:00",
        "planned_end_time": "2026-10-27T23:00:00+00:00",
        "_doems_r6_proof": {
            "source": "published_r6_bridge", "planner_generation": generation,
            "bridge_ready": True, "planner_valid": True,
            "invalid_candidate_count": 0, "physical_execution_enabled": False,
        },
    }


def check(plans, generation=17):
    return validate_doems_proposals(plans, generation=generation,
                                    max_charge_w=3200, max_discharge_w=3200)


def test_valid_plan_preserves_identity_without_proof_in_plan_store():
    plans = check({1: candidate()})
    assert plans[1]["planner_identity"] == "charge-1"
    assert "_doems_r6_proof" not in plans[1]


@pytest.mark.parametrize("field,value", [
    ("power_w", 3300),
    ("action", "other"),
    ("planner_signature", ""),
    ("origin", "manual"),
])
def test_invalid_proposals_are_rejected(field, value):
    item = candidate()
    item[field] = value
    with pytest.raises(DOEMSIngressRejected):
        check({1: item})


def test_stale_generation_rejected():
    with pytest.raises(DOEMSIngressRejected):
        check({1: candidate(generation=16)})


def test_duplicate_identity_rejected():
    with pytest.raises(DOEMSIngressRejected):
        check({1: candidate(), 2: candidate()})


def test_invalid_proof_rejected():
    item = candidate()
    item["_doems_r6_proof"]["bridge_ready"] = False
    with pytest.raises(DOEMSIngressRejected):
        check({1: item})


def test_invalid_slot_rejected():
    with pytest.raises(DOEMSIngressRejected):
        check({4: candidate()})
