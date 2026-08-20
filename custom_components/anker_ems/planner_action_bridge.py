from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

from homeassistant.util import dt as dt_util

from .const import PLAN_SLOT_COUNT

_MIN_ACTION_ENERGY_KWH = 0.01
_DEFAULT_START_DELAY_MIN = 10


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return parsed.astimezone(dt_util.UTC)


def _round_power_up(power_w: float, max_power_w: int) -> int:
    """Round planned average power upward to 10 W without exceeding hardware limit."""
    if power_w <= 0:
        return 0
    rounded = int(math.ceil(power_w / 10.0) * 10)
    return max(100, min(max_power_w, rounded))


def _manual_slot_available(detail: dict[str, Any]) -> bool:
    """Return True only when an existing manual slot is safe to reuse.

    Alpha28 treats terminal lifecycle states as reusable. A cancelled, completed
    or failed plan must never remain a permanent slot lock. Active and still
    actionable manual plans remain protected from automatic overwrite.
    """
    action = detail.get("action")
    status = str(detail.get("status") or "").lower()
    lifecycle = str(detail.get("lifecycle_status") or "").lower()
    origin = str(detail.get("origin") or "manual")

    # A planner-owned concept is safe for the next rolling planner refresh.
    # Any user edit changes origin to manual in Plan Store.
    if origin == "automatic_72h_planner" and lifecycle == "concept":
        return True
    if action in (None, "geen"):
        return True
    if lifecycle in {"geannuleerd", "voltooid", "fout"}:
        return True
    if status in {"geannuleerd", "voltooid", "fout", "leeg"}:
        return True
    return False


def _forced_row_action(row: dict[str, Any]) -> tuple[str, str, float] | None:
    safety = max(0.0, _as_float(row.get("charge_from_grid_safety_kwh")) or 0.0)
    trade_charge = max(0.0, _as_float(row.get("charge_from_grid_trade_kwh")) or 0.0)
    grid_discharge = max(0.0, _as_float(row.get("discharge_to_grid_kwh")) or 0.0)

    grid_charge = safety + trade_charge
    if grid_charge > _MIN_ACTION_ENERGY_KWH:
        if safety > _MIN_ACTION_ENERGY_KWH and trade_charge > _MIN_ACTION_ENERGY_KWH:
            purpose = "veiligheidsladen+handelsladen"
        elif safety > _MIN_ACTION_ENERGY_KWH:
            purpose = "veiligheidsladen"
        else:
            purpose = "handelsladen"
        return "laden", purpose, grid_charge

    if grid_discharge > _MIN_ACTION_ENERGY_KWH:
        return "ontladen", "handel_ontladen", grid_discharge

    # Solar charging and discharge to the home are intentionally not converted
    # to explicit third-party-control actions. Those flows belong to the normal
    # self_consumption behaviour of the battery.
    return None


def _build_candidate(segment: list[dict[str, Any]], now_utc: datetime, max_charge_power_w: int, max_discharge_power_w: int) -> dict[str, Any]:
    first = segment[0]
    last = segment[-1]
    action = str(first["bridge_action"])
    purpose = str(first["bridge_purpose"])

    first_hour = first["parsed_time"]
    last_hour = last["parsed_time"]
    planned_start = max(first_hour, now_utc)
    planned_end = last_hour + timedelta(hours=1)
    duration_h = max(0.0, (planned_end - planned_start).total_seconds() / 3600.0)
    energy_kwh = sum(float(item["bridge_energy_kwh"]) for item in segment)

    max_power_w = max_charge_power_w if action == "laden" else max_discharge_power_w
    average_power_w = energy_kwh * 1000.0 / duration_h if duration_h > 0 else 0.0
    power_w = _round_power_up(average_power_w, max_power_w)
    target_soc = _as_float(last.get("soc_end"))

    valid = True
    reasons: list[str] = []
    if duration_h <= 0:
        valid = False
        reasons.append("invalid_duration")
    if power_w < 100 or power_w > max_power_w:
        valid = False
        reasons.append("invalid_power")
    if average_power_w > max_power_w + 1:
        valid = False
        reasons.append("required_power_above_limit")
    if target_soc is None or not 5 <= target_soc <= 100:
        valid = False
        reasons.append("invalid_target_soc")

    prices = [
        value
        for value in (_as_float(item.get("price")) for item in segment)
        if value is not None
    ]

    return {
        "action": action,
        "purpose": purpose,
        "execution_mode": "gepland",
        "start_time": planned_start.isoformat(),
        "planned_end_time": planned_end.isoformat(),
        "power_w": power_w,
        "average_required_power_w": round(average_power_w, 1),
        "target_soc": round(target_soc, 1) if target_soc is not None else None,
        "max_runtime_h": round(max(0.25, min(12.0, duration_h)), 2),
        "max_start_delay_min": _DEFAULT_START_DELAY_MIN,
        "expected_energy_kwh": round(energy_kwh, 3),
        "source_hour_count": len(segment),
        "source_hours": [item["parsed_time"].isoformat() for item in segment],
        "price_min": round(min(prices), 5) if prices else None,
        "price_max": round(max(prices), 5) if prices else None,
        "soc_start": _as_float(first.get("soc_start")),
        "soc_end": target_soc,
        "execution_reserve_start_soc": _as_float(first.get("execution_reserve_floor_start_soc")),
        "execution_reserve_end_soc": _as_float(last.get("execution_reserve_floor_soc")),
        "valid": valid,
        "validation_reasons": reasons,
        "origin": "automatic_72h_planner",
        "observational_only": True,
    }


def _candidate_identity(candidate: dict[str, Any]) -> str:
    """Return the stable planner-action identity independent of forecast revisions.

    Alpha31 separates *which* action this is from the latest calculated values.
    Source-hour anchors remain stable when SOC, power, target SOC or expected
    energy are revised by a rolling 72-hour replan.
    """
    return "|".join(
        [
            str(candidate.get("action") or ""),
            str(candidate.get("purpose") or ""),
            ",".join(str(value) for value in candidate.get("source_hours") or []),
            str(candidate.get("planned_end_time") or ""),
        ]
    )


def _identity_from_signature(signature: Any) -> str | None:
    """Derive Alpha31 identity from an Alpha29/30 six-part signature."""
    if not isinstance(signature, str) or not signature:
        return None
    parts = signature.split("|")
    if len(parts) < 4:
        return None
    return "|".join(parts[:4])


def _candidate_signature(candidate: dict[str, Any]) -> str:
    """Return the latest revision signature for a planner action."""
    signature_energy = round(float(candidate.get("expected_energy_kwh") or 0.0), 2)
    return "|".join(
        [
            str(candidate.get("action") or ""),
            str(candidate.get("purpose") or ""),
            ",".join(str(value) for value in candidate.get("source_hours") or []),
            str(candidate.get("planned_end_time") or ""),
            str(round(float(candidate.get("target_soc") or 0.0), 1)),
            str(signature_energy),
        ]
    )


def build_planner_action_bridge(
    data: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Translate the observer 72h plan to a rolling three-slot execution preview.

    Alpha30 feeds this validated rolling preview to the controlled Plan Store
    writer and then allows matching planner-owned concepts to be handed off to
    the Scheduler as ``pending``. Physical execution remains disabled.
    """
    now_utc = (now or dt_util.utcnow()).astimezone(dt_util.UTC)
    auto_plan = data.get("auto_plan_72h_plan") or []
    plan_valid = bool(data.get("auto_plan_72h_valid"))
    buffer_safe = bool(data.get("auto_plan_72h_execution_buffer_safe"))
    forecast_ready = bool(data.get("forecast_ready"))
    max_charge_power_w = int(data.get("max_charge_power_w") or 800)
    max_discharge_power_w = int(data.get("max_discharge_power_w") or 800)

    base = {
        "auto_bridge_observational_only": False,
        "auto_bridge_plan_store_write_enabled": True,
        "auto_bridge_scheduler_handoff_enabled": True,
        "auto_bridge_execution_enabled": False,
        "auto_bridge_rolling_window": True,
        "auto_bridge_slot_capacity": PLAN_SLOT_COUNT,
        "auto_bridge_pending_reconciliation_enabled": True,
        "auto_bridge_max_charge_power_w": max_charge_power_w,
        "auto_bridge_max_discharge_power_w": max_discharge_power_w,
    }

    if not plan_valid or not isinstance(auto_plan, list) or not auto_plan:
        return {
            **base,
            "auto_bridge_status": "blocked_invalid_plan",
            "auto_bridge_valid": False,
            "auto_bridge_reason": "72-uursplan is niet geldig of niet beschikbaar",
            "auto_bridge_candidate_count": 0,
            "auto_bridge_slot_preview_count": 0,
            "auto_bridge_overflow_count": 0,
            "auto_bridge_candidates": [],
            "auto_bridge_slot_preview": [],
            "auto_bridge_available_manual_slots": 0,
            "auto_bridge_manual_slot_conflict": False,
        }

    if not buffer_safe:
        return {
            **base,
            "auto_bridge_status": "blocked_execution_buffer",
            "auto_bridge_valid": False,
            "auto_bridge_reason": "Uitvoeringsbuffer van het 72-uursplan is niet veilig",
            "auto_bridge_candidate_count": 0,
            "auto_bridge_slot_preview_count": 0,
            "auto_bridge_overflow_count": 0,
            "auto_bridge_candidates": [],
            "auto_bridge_slot_preview": [],
            "auto_bridge_available_manual_slots": 0,
            "auto_bridge_manual_slot_conflict": False,
        }

    prepared_rows: list[dict[str, Any]] = []
    for raw in auto_plan:
        if not isinstance(raw, dict):
            continue
        parsed_time = _parse_time(raw.get("time"))
        if parsed_time is None or parsed_time + timedelta(hours=1) <= now_utc:
            continue
        forced = _forced_row_action(raw)
        if forced is None:
            continue
        action, purpose, energy_kwh = forced
        item = dict(raw)
        item["parsed_time"] = parsed_time
        item["bridge_action"] = action
        item["bridge_purpose"] = purpose
        item["bridge_energy_kwh"] = energy_kwh
        prepared_rows.append(item)

    prepared_rows.sort(key=lambda item: item["parsed_time"])

    segments: list[list[dict[str, Any]]] = []
    for row in prepared_rows:
        if not segments:
            segments.append([row])
            continue
        previous = segments[-1][-1]
        consecutive = row["parsed_time"] - previous["parsed_time"] == timedelta(hours=1)
        same_action = row["bridge_action"] == previous["bridge_action"]
        same_purpose = row["bridge_purpose"] == previous["bridge_purpose"]
        if consecutive and same_action and same_purpose:
            segments[-1].append(row)
        else:
            segments.append([row])

    candidates = [_build_candidate(segment, now_utc, max_charge_power_w, max_discharge_power_w) for segment in segments]
    candidates = [candidate for candidate in candidates if candidate["expected_energy_kwh"] > _MIN_ACTION_ENERGY_KWH]

    scheduler_slots = data.get("scheduler_slots") or {}
    slot_statuses: list[dict[str, Any]] = []
    available_slots = 0
    for slot in range(1, PLAN_SLOT_COUNT + 1):
        detail = scheduler_slots.get(slot) or scheduler_slots.get(str(slot)) or {}
        available = _manual_slot_available(detail)
        if available:
            available_slots += 1
        slot_statuses.append(
            {
                "slot": slot,
                "available_for_automatic_write": available,
                "manual_action": detail.get("action"),
                "manual_status": detail.get("status"),
                "manual_lifecycle_status": detail.get("lifecycle_status"),
                "manual_origin": detail.get("origin"),
                "planner_signature": detail.get("planner_signature"),
                "planner_identity": detail.get("planner_identity") or _identity_from_signature(detail.get("planner_signature")),
            }
        )

    # Alpha31 reconciles planner-owned pending slots by stable planner identity,
    # not by the revision signature. Forecast/SOC changes may legitimately alter
    # power, target SOC and expected energy while the underlying planned action
    # (purpose + source hour(s)) remains the same.
    preview: list[dict[str, Any]] = []
    used_slots: set[int] = set()
    for candidate in candidates[:PLAN_SLOT_COUNT]:
        enriched = dict(candidate)
        identity = _candidate_identity(enriched)
        signature = _candidate_signature(enriched)
        enriched["planner_identity"] = identity
        enriched["planner_signature"] = signature

        matched = next(
            (
                item
                for item in slot_statuses
                if item["slot"] not in used_slots
                and item.get("manual_origin") == "automatic_72h_planner"
                and str(item.get("manual_lifecycle_status") or "").lower() == "pending"
                and item.get("planner_identity") == identity
            ),
            None,
        )
        if matched is not None:
            actual_slot = matched
            automatic_pending_match = True
        else:
            actual_slot = next(
                (
                    item
                    for item in slot_statuses
                    if item["slot"] not in used_slots
                    and item.get("available_for_automatic_write")
                ),
                None,
            )
            automatic_pending_match = False

        if actual_slot is not None:
            used_slots.add(int(actual_slot["slot"]))

        enriched["suggested_slot"] = actual_slot["slot"] if actual_slot else None
        enriched["manual_slot_available"] = actual_slot is not None
        enriched["manual_slot_status"] = actual_slot["manual_status"] if actual_slot else None
        enriched["automatic_pending_match"] = automatic_pending_match
        enriched["plan_store_write_permitted"] = bool(
            candidate.get("valid")
            and actual_slot is not None
            and (
                automatic_pending_match
                or actual_slot.get("available_for_automatic_write")
            )
        )
        enriched["scheduler_handoff_permitted"] = bool(
            candidate.get("valid") and actual_slot is not None
        )
        preview.append(enriched)

    invalid_candidates = sum(1 for candidate in candidates if not candidate.get("valid"))
    preview_conflicts = sum(1 for item in preview if not item.get("manual_slot_available"))
    overflow = max(0, len(candidates) - len(preview))

    if not candidates:
        status = "idle_no_forced_actions"
        reason = (
            "Geen expliciete netlaad- of netontlaadactie nodig; solar laden en woningdekking "
            "blijven onder normale self_consumption vallen"
        )
        valid = True
    elif invalid_candidates:
        status = "blocked_invalid_candidates"
        reason = f"{invalid_candidates} automatische actiekandidaat/kandidaten zijn niet uitvoerbaar"
        valid = False
    elif not forecast_ready:
        status = "preview_forecast_incomplete"
        reason = "Actiepreview gemaakt, maar forecastbronnen zijn nog niet volledig startklaar"
        valid = True
    elif preview_conflicts:
        status = "preview_manual_slots_in_use"
        reason = (
            "Actiepreview gemaakt; niet alle kandidaten passen naast bestaande handmatige planslots"
        )
        valid = True
    else:
        pending_matches = sum(1 for item in preview if item.get("automatic_pending_match"))
        if pending_matches:
            status = "scheduler_handoff_active"
            reason = (
                f"{pending_matches} automatische planneractie(s) staan gecontroleerd in de Scheduler"
            )
        else:
            status = "ready_preview"
            reason = (
                "Volgende expliciete planneracties zijn gevalideerd voor Plan Store-write en Scheduler-handoff"
            )
        valid = True

    return {
        **base,
        "auto_bridge_status": status,
        "auto_bridge_valid": valid,
        "auto_bridge_reason": reason,
        "auto_bridge_candidate_count": len(candidates),
        "auto_bridge_slot_preview_count": len(preview),
        "auto_bridge_overflow_count": overflow,
        "auto_bridge_invalid_candidate_count": invalid_candidates,
        "auto_bridge_candidates": candidates,
        "auto_bridge_slot_preview": preview,
        "auto_bridge_manual_slots": slot_statuses,
        "auto_bridge_available_manual_slots": available_slots,
        "auto_bridge_manual_slot_conflict": preview_conflicts > 0,
        "auto_bridge_manual_slot_conflict_count": preview_conflicts,
        "auto_bridge_note": (
            "Planner-owned pending plannen worden op stabiele planner identity gereconcilieerd. "
            "Plan Store-write, Scheduler-handoff en pre-start veiligheidsvalidatie zijn actief; "
            "fysieke automatische uitvoering blijft uitgeschakeld."
        ),
    }
