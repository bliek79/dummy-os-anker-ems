"""Unittest-compatible contract tests without importing Home Assistant package."""
import importlib.util
from pathlib import Path
import unittest

_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "anker_ems"

def _load(name):
    spec = importlib.util.spec_from_file_location(name, _ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_ingress = _load("doems_ingress")
validate_doems_proposals = _ingress.validate_doems_proposals
DOEMSIngressRejected = _ingress.DOEMSIngressRejected

def candidate(identity="charge-1", generation=17):
    return {
        "origin": "automatic_72h_planner", "action": "laden",
        "execution_mode": "gepland", "max_start_delay_min": 10,
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


class DOEMSIngressContractTests(unittest.TestCase):
    def test_valid_plan_preserves_identity_without_proof(self):
        plans = check({1: candidate()})
        self.assertEqual(plans[1]["planner_identity"], "charge-1")
        self.assertNotIn("_doems_r6_proof", plans[1])

    def test_invalid_proposals_rejected(self):
        for field, value in (("power_w", 3300), ("action", "other"),
                             ("planner_signature", ""), ("origin", "manual")):
            with self.subTest(field=field):
                item = candidate()
                item[field] = value
                with self.assertRaises(DOEMSIngressRejected):
                    check({1: item})

    def test_stale_generation_rejected(self):
        with self.assertRaises(DOEMSIngressRejected):
            check({1: candidate(generation=16)})

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(DOEMSIngressRejected):
            check({1: candidate(), 2: candidate()})

    def test_invalid_proof_rejected(self):
        item = candidate()
        item["_doems_r6_proof"]["bridge_ready"] = False
        with self.assertRaises(DOEMSIngressRejected):
            check({1: item})

    def test_invalid_slot_rejected(self):
        with self.assertRaises(DOEMSIngressRejected):
            check({4: candidate()})


if __name__ == "__main__":
    unittest.main()
