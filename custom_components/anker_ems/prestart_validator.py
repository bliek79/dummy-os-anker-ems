from __future__ import annotations

from typing import Any

from .const import MAX_SOC_PERCENT, MIN_SOC_PERCENT


class AnkerEmsPreStartValidator:
    """Validate an automatic Scheduler-ready plan immediately before execution.

    Alpha32 is observational only. It evaluates whether the currently selected
    planner-owned plan would be allowed to proceed to the execution stage, but
    it never calls the Execution Controller or any physical battery service.
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

        result: dict[str, Any] = {
            "auto_prestart_enabled": True,
            "auto_prestart_required": False,
            "auto_prestart_safe": False,
            "auto_prestart_status": "not_required",
            "auto_prestart_reason": "Geen automatische startklare planneractie geselecteerd",
            "auto_prestart_reasons": [],
            "auto_prestart_warnings": [],
            "auto_prestart_selected_slot": None,
            "auto_prestart_planner_identity": None,
            "auto_prestart_current_identity_match": False,
            "auto_prestart_current_signature_match": False,
            "auto_prestart_current_soc": self._number(data.get("soc")),
            "auto_prestart_target_soc": None,
            "auto_prestart_execution_reserve_soc": None,
            "auto_prestart_execution_enabled": False,
            "auto_prestart_physical_control": False,
        }

        if slot is None or not data.get("scheduler_ready"):
            return result

        origin = str(detail.get("origin") or "manual")
        planner_identity = detail.get("planner_identity")
        if origin != "automatic_72h_planner" or not planner_identity:
            result.update(
                {
                    "auto_prestart_status": "manual_plan",
                    "auto_prestart_reason": "Geselecteerd plan is handmatig; automatische pre-start validatie is niet van toepassing",
                    "auto_prestart_selected_slot": slot,
                }
            )
            return result

        result["auto_prestart_required"] = True
        result["auto_prestart_selected_slot"] = slot
        result["auto_prestart_planner_identity"] = planner_identity

        reasons: list[str] = []
        warnings: list[str] = []

        if data.get("auto_plan_72h_valid") is not True:
            reasons.append("planner_invalid")
        if data.get("forecast_ready") is not True:
            reasons.append("forecast_not_ready")
        if data.get("auto_plan_72h_execution_buffer_safe") is not True:
            reasons.append("execution_buffer_unsafe")
        if int(data.get("auto_bridge_invalid_candidate_count") or 0) > 0:
            reasons.append("invalid_bridge_candidates")
        if data.get("auto_bridge_valid") is not True:
            reasons.append("bridge_invalid")

        candidates = data.get("auto_bridge_candidates") or []
        current = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("planner_identity") == planner_identity
            ),
            None,
        )
        # build_planner_action_bridge exposes planner_identity on slot preview,
        # but older candidate dictionaries may not carry it. Fall back to the
        # current preview so alpha32 remains compatible with alpha31 data flow.
        if current is None:
            current = next(
                (
                    proposal
                    for proposal in (data.get("auto_bridge_slot_preview") or [])
                    if proposal.get("planner_identity") == planner_identity
                ),
                None,
            )

        identity_match = current is not None
        result["auto_prestart_current_identity_match"] = identity_match
        if not identity_match:
            reasons.append("planner_identity_missing")

        stored_signature = detail.get("planner_signature")
        current_signature = current.get("planner_signature") if current else None
        signature_match = bool(
            stored_signature and current_signature and stored_signature == current_signature
        )
        result["auto_prestart_current_signature_match"] = signature_match
        if identity_match and not signature_match:
            warnings.append("planner_revision_changed_after_due")

        action = detail.get("action")
        power = self._number(detail.get("power_w"))
        target_soc = self._number(detail.get("target_soc"))
        soc = self._number(data.get("soc"))
        result["auto_prestart_target_soc"] = target_soc

        if action not in {"laden", "ontladen"}:
            reasons.append("invalid_action")
        max_power = 3000 if action == "ontladen" else 3500
        if power is None or not 100 <= power <= max_power:
            reasons.append("invalid_power")
        if soc is None or not MIN_SOC_PERCENT <= soc <= MAX_SOC_PERCENT:
            reasons.append("invalid_soc")
        if target_soc is None or not MIN_SOC_PERCENT <= target_soc <= MAX_SOC_PERCENT:
            reasons.append("invalid_target_soc")

        if soc is not None and target_soc is not None:
            if action == "laden" and soc >= target_soc:
                reasons.append("charge_target_already_reached")
            if action == "ontladen" and soc <= target_soc:
                reasons.append("discharge_target_already_reached")

        reserve_soc = None
        if current is not None:
            reserve_soc = self._number(current.get("execution_reserve_start_soc"))
        result["auto_prestart_execution_reserve_soc"] = reserve_soc
        if action == "ontladen" and soc is not None and reserve_soc is not None and soc <= reserve_soc:
            reasons.append("execution_reserve_reached")

        safe = not reasons
        result.update(
            {
                "auto_prestart_safe": safe,
                "auto_prestart_status": "safe_observe" if safe else "blocked",
                "auto_prestart_reason": (
                    "Pre-start veiligheidscontrole akkoord; automatische fysieke uitvoering blijft uitgeschakeld"
                    if safe
                    else ", ".join(reasons)
                ),
                "auto_prestart_reasons": reasons,
                "auto_prestart_warnings": warnings,
            }
        )
        return result
