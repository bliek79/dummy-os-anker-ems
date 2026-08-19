from __future__ import annotations

from typing import Any

from .const import MAX_SOC_PERCENT, MIN_SOC_PERCENT


class AnkerEmsSafetyGuard:
    """Evaluate whether a scheduler-selected action is safe to prepare.

    Alpha 10 keeps the normal EMS controller non-actuating. The guard validates the current
    Home Assistant source state and the selected persistent plan, but never
    calls services or writes to the physical battery.
    """

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def evaluate(self, data: dict[str, Any]) -> dict[str, Any]:
        slot = data.get("scheduler_selected_slot")
        slots = data.get("scheduler_slots", {}) or {}
        detail = slots.get(slot) or slots.get(str(slot)) or {}

        reasons: list[str] = []
        warnings: list[str] = []

        if slot is None or not data.get("scheduler_ready"):
            return {
                "safety_safe": False,
                "safety_status": "geen_actie",
                "safety_reason": "Geen startklaar plan geselecteerd",
                "safety_reasons": ["no_selected_plan"],
                "safety_warnings": [],
                "safety_selected_slot": None,
                "safety_physical_control": False,
            }

        action = detail.get("action")
        power = self._number(detail.get("power_w"))
        target_soc = self._number(detail.get("target_soc"))
        soc = self._number(data.get("soc"))
        charge_power = self._number(data.get("charge_power_w"))
        discharge_power = self._number(data.get("discharge_power_w"))

        observation_values = (
            data.get("soc"),
            data.get("device_status"),
            data.get("charge_power_w"),
            data.get("discharge_power_w"),
            data.get("operating_mode"),
        )
        if any(value is None for value in observation_values):
            reasons.append("observation_sources_missing")

        if data.get("operating_mode") != "third_party_control":
            reasons.append("not_in_external_mode")
        else:
            control_values = (
                data.get("action_direction"),
                data.get("power_setpoint_w"),
            )
            if any(value is None for value in control_values):
                reasons.append("control_sources_missing")

        if action not in {"laden", "ontladen"}:
            reasons.append("invalid_action")

        max_power = 3000 if action == "ontladen" else 3500
        if power is None or not 100 <= power <= max_power:
            reasons.append("invalid_power")

        if soc is None or not 0 <= soc <= MAX_SOC_PERCENT:
            reasons.append("invalid_soc")

        if target_soc is None or not MIN_SOC_PERCENT <= target_soc <= MAX_SOC_PERCENT:
            reasons.append("invalid_target_soc")

        if soc is not None and target_soc is not None:
            if action == "laden" and soc >= target_soc:
                reasons.append("charge_target_already_reached")
            if action == "ontladen" and soc <= target_soc:
                reasons.append("discharge_target_already_reached")
            if action == "ontladen" and soc <= MIN_SOC_PERCENT:
                reasons.append("minimum_soc_reached")

        if (
            charge_power is not None
            and discharge_power is not None
            and charge_power > 100
            and discharge_power > 100
        ):
            reasons.append("conflicting_battery_power")

        if data.get("forecast_ready") is not True:
            warnings.append("forecast_not_ready")

        safe = len(reasons) == 0
        if safe and data.get("simulation_mode"):
            status = "veilig_simulatie"
            reason_text = "Veiligheidscontrole akkoord; fysieke uitvoering geblokkeerd door simulatiemodus"
        elif safe:
            status = "veilig_observe"
            reason_text = "Veiligheidscontrole akkoord; normale EMS-controller voert nog geen fysieke commando's uit"
        else:
            status = "geblokkeerd"
            reason_text = ", ".join(reasons)

        return {
            "safety_safe": safe,
            "safety_status": status,
            "safety_reason": reason_text,
            "safety_reasons": reasons,
            "safety_warnings": warnings,
            "safety_selected_slot": slot,
            "safety_physical_control": False,
        }
