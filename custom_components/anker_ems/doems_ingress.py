"""Input validation for using DOEMS as a planner source in the original Alpha84 chain.

No services, no authority transfer, no plan-store writes, no physical execution.
The original coordinator and controller remain the only owners of execution.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Mapping


class DOEMSIngressRejected(ValueError):
    """DOEMS input is absent, ambiguous, stale or not proven."""


def validate_doems_candidate(
    candidate: Mapping[str, Any], *,
    expected_generation: int,
    max_charge_w: int,
    max_discharge_w: int,
) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise DOEMSIngressRejected("Candidate must be a mapping")
    proof = candidate.get("_doems_r6_proof")
    if not isinstance(proof, Mapping):
        raise DOEMSIngressRejected("R6 publication proof missing")
    if (
        proof.get("source") != "published_r6_bridge"
        or type(proof.get("planner_generation")) is not int
        or proof["planner_generation"] != expected_generation
        or proof.get("bridge_ready") is not True
        or proof.get("planner_valid") is not True
        or proof.get("invalid_candidate_count") != 0
        or proof.get("physical_execution_enabled") is not False
    ):
        raise DOEMSIngressRejected("R6 publication proof invalid or stale")
    identity = candidate.get("planner_identity")
    signature = candidate.get("planner_signature")
    if not isinstance(identity, str) or not identity or not isinstance(signature, str) or not signature:
        raise DOEMSIngressRejected("Candidate identity or signature missing")
    if candidate.get("origin") != "automatic_72h_planner":
        raise DOEMSIngressRejected("Candidate origin invalid")
    action = candidate.get("action")
    if action not in ("laden", "ontladen"):
        raise DOEMSIngressRejected("Candidate action invalid")
    power = candidate.get("power_w")
    limit = max_charge_w if action == "laden" else max_discharge_w
    if type(power) not in (int, float) or not isfinite(power) or not float(power).is_integer() or not 100 <= power <= limit:
        raise DOEMSIngressRejected("Candidate power outside original limits")
    target, runtime = candidate.get("target_soc"), candidate.get("max_runtime_h")
    if type(target) not in (int, float) or not isfinite(target) or not 5 <= target <= 100:
        raise DOEMSIngressRejected("Candidate SOC target invalid")
    if type(runtime) not in (int, float) or not isfinite(runtime) or not 0.25 <= runtime <= 12:
        raise DOEMSIngressRejected("Candidate runtime invalid")
    if not candidate.get("start_time") or not candidate.get("planned_end_time"):
        raise DOEMSIngressRejected("Candidate time window missing")
    accepted = deepcopy(dict(candidate))
    accepted.pop("_doems_r6_proof", None)
    return accepted


def validate_doems_proposals(
    proposals: Mapping[int, Mapping[str, Any]], *,
    generation: int,
    max_charge_w: int,
    max_discharge_w: int,
) -> dict[int, dict[str, Any]]:
    if type(generation) is not int or generation < 0 or not isinstance(proposals, Mapping):
        raise DOEMSIngressRejected("Publication generation or proposals invalid")
    if len(proposals) > 3:
        raise DOEMSIngressRejected("Too many proposals")
    result: dict[int, dict[str, Any]] = {}
    identities: set[str] = set()
    for slot, proposal in proposals.items():
        if type(slot) is not int or slot not in (1, 2, 3):
            raise DOEMSIngressRejected("Invalid slot")
        checked = validate_doems_candidate(
            proposal, expected_generation=generation,
            max_charge_w=max_charge_w, max_discharge_w=max_discharge_w,
        )
        if checked["planner_identity"] in identities:
            raise DOEMSIngressRejected("Duplicate plan identity")
        identities.add(checked["planner_identity"])
        result[slot] = checked
    return result
