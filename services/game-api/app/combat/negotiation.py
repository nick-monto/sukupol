from __future__ import annotations

from typing import Any


NEGOTIATION_OUTCOMES: dict[str, str] = {
    "recruit": "Invite to join",
    "tribute": "Demand tribute",
    "retreat": "Force retreat",
}


def _reason_blocked_message(temperament: str, reason_blocked: str, can_negotiate: bool) -> str:
    if reason_blocked or can_negotiate:
        return reason_blocked
    if temperament == "resentful":
        return "It understands you, but old bitterness closes every opening."
    if temperament == "irate":
        return "It can speak, but rage has burned past reason."
    return "It understands you, but offers no terms."


def _parse_raw_negotiation(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "can_negotiate": bool(raw.get("can_negotiate", bool(raw.get("outcomes")))),
        "temperament": str(raw.get("temperament", "wary")).strip() or "wary",
        "difficulty": max(1, min(10, int(raw.get("difficulty", 5)))),
        "anger_limit": max(1, int(raw.get("anger_limit", 2))),
        "outcomes": [o for o in raw.get("outcomes", []) if o in NEGOTIATION_OUTCOMES],
        "ally_battles": max(0, int(raw.get("ally_battles", 0))),
        "tribute_item_id": raw.get("tribute_item_id"),
        "tribute_quantity": max(1, int(raw.get("tribute_quantity", 1))),
        "reason_blocked": str(raw.get("reason_blocked", "")).strip(),
    }


def enemy_negotiation_profile(enemy_def: dict[str, Any]) -> dict[str, Any] | None:
    communication_mode = enemy_def.get("communication_mode")
    if communication_mode not in {"speech", "telepathy"}:
        return None
    raw_value = enemy_def.get("negotiation")
    raw: dict[str, Any] = raw_value if isinstance(raw_value, dict) else {}
    p = _parse_raw_negotiation(raw)
    return {
        "communication_mode": communication_mode,
        "can_negotiate": p["can_negotiate"],
        "temperament": p["temperament"],
        "difficulty": p["difficulty"],
        "anger_limit": p["anger_limit"],
        "outcomes": p["outcomes"],
        "ally_battles": p["ally_battles"],
        "tribute_item_id": p["tribute_item_id"],
        "tribute_quantity": p["tribute_quantity"],
        "reason_blocked": _reason_blocked_message(p["temperament"], p["reason_blocked"], p["can_negotiate"]),
    }


def normalize_negotiation_transcript(raw_transcript: Any) -> list[dict[str, str]]:
    transcript: list[dict[str, str]] = []
    if not isinstance(raw_transcript, list):
        return transcript
    for entry in raw_transcript[-6:]:
        if not isinstance(entry, dict):
            continue
        raw_speaker = entry.get("speaker")
        speaker = str(raw_speaker) if raw_speaker in {"player", "enemy", "system"} else "system"
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        transcript.append({"speaker": speaker, "text": text})
    return transcript


def _build_parley_options(outcomes: list[str], locked: bool) -> list[dict[str, Any]]:
    return [
        {"id": f"parley_{oid}", "label": NEGOTIATION_OUTCOMES[oid], "outcome": oid, "enabled": not locked}
        for oid in outcomes
    ]


def _read_existing_negotiation_state(existing: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempts": max(0, int(existing.get("attempts", 0))),
        "anger": max(0, int(existing.get("anger", 0))),
        "leverage": max(-3, min(3, int(existing.get("leverage", 0)))),
        "active": bool(existing.get("active", False)),
        "locked": bool(existing.get("locked", False)),
        "active_intent": str(existing.get("active_intent", "")).strip() or None,
        "outcome": str(existing.get("outcome", "")).strip() or None,
        "lock_reason": str(existing.get("lock_reason", "")).strip(),
        "transcript": normalize_negotiation_transcript(existing.get("transcript")),
    }


def _build_negotiation_result(profile: dict[str, Any], s: dict[str, Any]) -> dict[str, Any]:
    anger, locked = s["anger"], (s["locked"] or not profile["can_negotiate"])
    active = s["active"] and not locked
    if anger >= profile["anger_limit"]:
        locked, active = True, False
    return {
        "communication_mode": profile["communication_mode"],
        "temperament": profile["temperament"],
        "available": not locked and profile["can_negotiate"],
        "locked": locked, "active": active, "attempts": s["attempts"],
        "anger": anger, "anger_limit": profile["anger_limit"],
        "leverage": s["leverage"], "difficulty": profile["difficulty"],
        "lock_reason": s["lock_reason"] or profile["reason_blocked"],
        "active_intent": s["active_intent"], "outcome": s["outcome"],
        "options": _build_parley_options(profile["outcomes"], locked),
        "transcript": s["transcript"],
    }


def build_negotiation_state(
    enemy_def: dict[str, Any], existing: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    profile = enemy_negotiation_profile(enemy_def)
    if profile is None:
        return None
    existing_state = _read_existing_negotiation_state(existing or {})
    existing_state["locked"] = existing_state["locked"] or not profile["can_negotiate"]
    return _build_negotiation_result(profile, existing_state)


def append_negotiation_transcript(negotiation: dict[str, Any], speaker: str, text: str) -> None:
    transcript = normalize_negotiation_transcript(negotiation.get("transcript"))
    transcript.append({"speaker": speaker, "text": text})
    negotiation["transcript"] = transcript[-6:]


def update_negotiation_lock(negotiation: dict[str, Any], enemy_def: dict[str, Any]) -> None:
    profile = enemy_negotiation_profile(enemy_def)
    if profile is None:
        return
    if int(negotiation.get("anger", 0)) >= int(negotiation.get("anger_limit", profile["anger_limit"])):
        negotiation["locked"] = True
        negotiation["available"] = False
        negotiation["active"] = False
        negotiation["lock_reason"] = "The creature rejects any further terms and commits fully to violence."


def parley_target_number(profile: dict[str, Any], negotiation: dict[str, Any], action: str) -> int:
    base = int(profile["difficulty"])
    modifiers = {"parley_recruit": 2, "parley_tribute": 1, "parley_retreat": 0}
    temperament = str(profile.get("temperament", "wary"))
    temperament_penalty = {"wary": 0, "resentful": 2, "irate": 4}.get(temperament, 0)
    leverage = int(negotiation.get("leverage", 0))
    return max(2, min(10, base + modifiers.get(action, 0) + temperament_penalty + int(negotiation.get("anger", 0)) - leverage))


def _match_polite_terms(lowered: str) -> tuple[int, bool]:
    delta = 0
    calming = False
    if any(t in lowered for t in ("please", "peace", "terms", "listen", "parley", "spare", "understand")):
        delta += 1
        calming = True
    if any(t in lowered for t in ("sorry", "forgive", "mean no", "no wish", "no need")):
        delta += 1
        calming = True
    return delta, calming


def _match_intent_terms(lowered: str, outcomes: list[str]) -> tuple[str | None, int]:
    inferred: str | None = None
    delta = 0
    if any(t in lowered for t in ("join", "together", "beside", "aid", "help", "with me")):
        inferred = "recruit"
        delta += 1 if "recruit" in outcomes else 0
    if any(t in lowered for t in ("tribute", "offer", "give", "payment", "gift", "toll")):
        inferred = "tribute"
        delta += 1 if "tribute" in outcomes else 0
    if any(t in lowered for t in ("retreat", "withdraw", "leave", "back away", "go now", "stand down")):
        inferred = "retreat"
        delta += 1 if "retreat" in outcomes else 0
    return inferred, delta


def _match_negative_terms(lowered: str, inferred_intent: str | None, outcomes: list[str], anger: int) -> tuple[int, int]:
    delta = 0
    anger_delta = anger
    if any(t in lowered for t in ("or die", "kill", "destroy", "cut you down", "burn", "end you")):
        if inferred_intent == "retreat" and "retreat" in outcomes:
            delta += 1
        else:
            delta -= 1
        anger_delta += 1
    if any(t in lowered for t in ("fool", "worm", "beast", "vermin", "filth", "stupid")):
        delta -= 1
        anger_delta += 1
    word_count = len([p for p in lowered.replace("\n", " ").split(" ") if p])
    if word_count < 3:
        delta -= 1
    return delta, anger_delta


def _apply_temperament(temperament: str, calming: bool, leverage_delta: int) -> int:
    delta = leverage_delta
    if temperament == "resentful" and calming:
        delta += 1
    if temperament == "irate" and calming:
        delta -= 1
    return delta


def _classify_parley_terms(lowered: str, profile: dict[str, Any]) -> tuple[str | None, int, int, bool]:
    outcomes = profile["outcomes"]
    polite_delta, calming = _match_polite_terms(lowered)
    inferred, intent_delta = _match_intent_terms(lowered, outcomes)
    neg_delta, anger_delta = _match_negative_terms(lowered, inferred, outcomes, 0)

    leverage_delta = _apply_temperament(
        str(profile.get("temperament", "wary")), calming, polite_delta + intent_delta + neg_delta,
    )
    return inferred, max(-2, min(3, leverage_delta)), max(-1 if calming else 0, min(2, anger_delta)), calming


def _parley_reply_text(leverage_delta: int, anger_delta: int, calming: bool) -> str:
    if leverage_delta >= 2:
        return "The creature stills for a moment, weighing what you said."
    if leverage_delta == 1:
        return "The creature does not yield, but it keeps listening."
    if anger_delta > 0:
        return "Your words bite wrong, and the creature answers with rising hostility."
    return "The creature hears you, but the meaning slides off without purchase."


def analyze_parley_message(profile: dict[str, Any], message: str, negotiation: dict[str, Any]) -> dict[str, Any]:
    lowered = message.lower()
    inferred_intent, leverage_delta, anger_delta, calming = _classify_parley_terms(lowered, profile)
    reply = _parley_reply_text(leverage_delta, anger_delta, calming)
    grants_pause = leverage_delta > 0 or calming
    provoked = anger_delta > 0 and not grants_pause
    return {
        "reply": reply,
        "inferred_intent": inferred_intent,
        "leverage_delta": leverage_delta,
        "anger_delta": anger_delta,
        "grants_pause": grants_pause,
        "provoked": provoked,
    }
