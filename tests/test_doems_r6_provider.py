"""Unittest-compatible read-only R6 provider tests."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "anker_ems"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


read_doems_r6_publication = _load("doems_r6_provider").read_doems_r6_publication
validate_doems_proposals = _load("doems_ingress").validate_doems_proposals


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


class DOEMSR6ProviderTests(unittest.TestCase):
    def test_witnessed_plan_passes_existing_ingress_contract(self):
        hass = SimpleNamespace(data={"doems": {"entry": _runtime()}})
        publication = read_doems_r6_publication(hass)
        accepted = validate_doems_proposals(
            publication["proposals"], generation=publication["generation"],
            max_charge_w=3200, max_discharge_w=3200,
        )
        self.assertEqual(accepted[1]["planner_identity"], "charge-1")
        self.assertNotIn("_doems_r6_proof", accepted[1])

    def test_missing_or_ambiguous_runtime_rejected(self):
        for runtimes in ({}, {"one": _runtime(), "two": _runtime()}):
            with self.subTest(runtime_count=len(runtimes)):
                with self.assertRaisesRegex(ValueError, "Exactly one"):
                    read_doems_r6_publication(SimpleNamespace(data={"doems": runtimes}))

    def test_stale_witness_rejected(self):
        with self.assertRaisesRegex(ValueError, "witness"):
            read_doems_r6_publication(
                SimpleNamespace(data={"doems": {"entry": _runtime(witness=False)}})
            )

    def test_unready_publication_rejected(self):
        with self.assertRaisesRegex(ValueError, "not ready"):
            read_doems_r6_publication(
                SimpleNamespace(data={"doems": {"entry": _runtime(ready=False)}})
            )


if __name__ == "__main__":
    unittest.main()
