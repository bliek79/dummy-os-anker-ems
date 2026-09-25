from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "anker_ems"


def test_alpha77_legacy_authority_fence_contract() -> None:
    fence = (INTEGRATION / "authority_fence.py").read_text(encoding="utf-8")
    execution = (INTEGRATION / "execution.py").read_text(encoding="utf-8")
    physical = (INTEGRATION / "physical_test.py").read_text(encoding="utf-8")
    init = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
    coordinator = (INTEGRATION / "coordinator.py").read_text(encoding="utf-8")
    sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")

    assert 'class AnkerEmsLegacyAuthorityFence' in fence
    assert '"status": "open"' in fence
    assert 'self._state["status"] = "closed"' in fence
    assert 'self.status == "closing" and safe_return' in fence
    assert 'float(data.get("value")) == 0.0' in fence
    assert '"self_consumption"' in fence
    assert 'authority_generation' in fence
    assert 'inflight_calls' in fence

    assert "self.hass.services.async_call(" not in execution
    assert "self.hass.services.async_call(" not in physical
    assert "await hass.services.async_call(" not in init
    assert "authority_fence.async_call(" in execution
    assert "authority_fence.async_call(" in physical
    assert "authority_fence.async_call(" in init

    assert "self.authority_fence = authority_fence" in coordinator
    assert "if armed and not self.authority_fence.is_open" in coordinator
    assert "data.update(self.authority_fence.snapshot())" in coordinator
    assert 'key="legacy_authority"' in sensor
    assert 'name="Dummy OS EMS Legacy Authority"' in sensor


def test_alpha80_version_contract() -> None:
    const = (INTEGRATION / "const.py").read_text(encoding="utf-8")
    manifest = (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
    assert 'VERSION = "0.0.1-alpha.80"' in const
    assert '"version": "0.0.1-alpha.80"' in manifest
