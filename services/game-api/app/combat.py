from __future__ import annotations

from typing import Any

from .agents import CombatParleyService
from .content import WorldContent
from .game import RunState, encounter_context_for_location, resolve_location
from .inventory import add_item, get_equipped_weapon, use_item
from .quests import recover_active_fetch_quest_items


PARTY_SLOT_COUNT = 3
EVENT_WINDOW = 12
NEGOTIATION_OUTCOMES = {
    "recruit": "Invite to join",
    "tribute": "Demand tribute",
    "retreat": "Force retreat",
}


def player_attack_value(world: WorldContent, state: RunState) -> int:
    weapon = get_equipped_weapon(world, state)
    return int(weapon.get("damage", 1)) if weapon else 1


def player_defence_value() -> int:
    return 0


def build_combat_event(round_number: int, actor: str, text: str, emphasis: str, index: int) -> dict[str, Any]:
    return {
        "id": f"round-{round_number}-{actor}-{index}",
        "round": round_number,
        "actor": actor,
        "text": text,
        "emphasis": emphasis,
    }


def inventory_quantity(state: RunState, item_id: str) -> int:
    for entry in state.inventory or []:
        if entry.get("item_id") == item_id:
            return int(entry.get("quantity", 0))
    return 0


def enemy_negotiation_profile(enemy_def: dict[str, Any]) -> dict[str, Any] | None:
    communication_mode = enemy_def.get("communication_mode")
    if communication_mode not in {"speech", "telepathy"}:
        return None

    raw_value = enemy_def.get("negotiation")
    raw: dict[str, Any] = raw_value if isinstance(raw_value, dict) else {}
    can_negotiate = bool(raw.get("can_negotiate", bool(raw.get("outcomes"))))
    temperament = str(raw.get("temperament", "wary")).strip() or "wary"
    difficulty = max(1, min(10, int(raw.get("difficulty", 5))))
    anger_limit = max(1, int(raw.get("anger_limit", 2)))
    outcomes = [outcome for outcome in raw.get("outcomes", []) if outcome in NEGOTIATION_OUTCOMES]
    ally_battles = max(0, int(raw.get("ally_battles", 0)))
    tribute_item_id = raw.get("tribute_item_id")
    tribute_quantity = max(1, int(raw.get("tribute_quantity", 1)))
    reason_blocked = str(raw.get("reason_blocked", "")).strip()

    if not reason_blocked and not can_negotiate:
        if temperament == "resentful":
            reason_blocked = "It understands you, but old bitterness closes every opening."
        elif temperament == "irate":
            reason_blocked = "It can speak, but rage has burned past reason."
        else:
            reason_blocked = "It understands you, but offers no terms."

    return {
        "communication_mode": communication_mode,
        "can_negotiate": can_negotiate,
        "temperament": temperament,
        "difficulty": difficulty,
        "anger_limit": anger_limit,
        "outcomes": outcomes,
        "ally_battles": ally_battles,
        "tribute_item_id": tribute_item_id,
        "tribute_quantity": tribute_quantity,
        "reason_blocked": reason_blocked,
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


def build_negotiation_state(enemy_def: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any] | None:
    profile = enemy_negotiation_profile(enemy_def)
    if profile is None:
        return None

    existing = existing or {}
    attempts = max(0, int(existing.get("attempts", 0)))
    anger = max(0, int(existing.get("anger", 0)))
    leverage = max(-3, min(3, int(existing.get("leverage", 0))))
    active = bool(existing.get("active", False))
    locked = bool(existing.get("locked", not profile["can_negotiate"]))
    active_intent = str(existing.get("active_intent", "")).strip() or None
    outcome = str(existing.get("outcome", "")).strip() or None
    lock_reason = str(existing.get("lock_reason", "")).strip() or profile["reason_blocked"]
    transcript = normalize_negotiation_transcript(existing.get("transcript"))

    if anger >= profile["anger_limit"]:
        locked = True
        active = False
        lock_reason = lock_reason or "The creature has had enough and rejects any further terms."

    if not profile["can_negotiate"]:
        locked = True
        active = False

    if locked:
        active = False

    options = [
        {
            "id": f"parley_{outcome_id}",
            "label": NEGOTIATION_OUTCOMES[outcome_id],
            "outcome": outcome_id,
            "enabled": not locked,
        }
        for outcome_id in profile["outcomes"]
    ]

    return {
        "communication_mode": profile["communication_mode"],
        "temperament": profile["temperament"],
        "available": not locked and profile["can_negotiate"],
        "locked": locked,
        "active": active,
        "attempts": attempts,
        "anger": anger,
        "anger_limit": profile["anger_limit"],
        "leverage": leverage,
        "difficulty": profile["difficulty"],
        "lock_reason": lock_reason,
        "active_intent": active_intent,
        "outcome": outcome,
        "options": options,
        "transcript": transcript,
    }


def active_party_allies(state: RunState) -> list[dict[str, Any]]:
    allies = state.party_allies or []
    active: list[dict[str, Any]] = []
    for ally in allies:
        if not isinstance(ally, dict):
            continue
        remaining_battles = int(ally.get("remaining_battles", 0))
        if remaining_battles < 1:
            continue
        active.append({**ally, "remaining_battles": remaining_battles})
    return active[: PARTY_SLOT_COUNT - 1]


def build_available_actions(
    world: WorldContent,
    state: RunState,
    combat_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    potion_count = inventory_quantity(state, "health_potion")
    actions = [
        {
            "id": "attack",
            "label": "Attack",
            "kind": "attack",
            "enabled": True,
            "item_id": None,
        },
        {
            "id": "defend",
            "label": "Defend",
            "kind": "defend",
            "enabled": True,
            "item_id": None,
        },
        {
            "id": "use_item:health_potion",
            "label": f"Use potion{f' ({potion_count})' if potion_count else ''}",
            "kind": "item",
            "enabled": potion_count > 0,
            "item_id": "health_potion",
        },
        {
            "id": "flee",
            "label": "Flee",
            "kind": "flee",
            "enabled": True,
            "item_id": None,
        },
    ]

    if isinstance(combat_state, dict):
        negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
        if negotiation and negotiation.get("available"):
            if negotiation.get("active"):
                for option in negotiation.get("options", []):
                    if not isinstance(option, dict):
                        continue
                    actions.append(
                        {
                            "id": str(option.get("id", "parley_invalid")),
                            "label": str(option.get("label", "Negotiate")),
                            "kind": "parley",
                            "enabled": bool(option.get("enabled", True)),
                            "item_id": None,
                        }
                    )
                actions.append(
                    {
                        "id": "parley_end",
                        "label": "End communication",
                        "kind": "parley",
                        "enabled": True,
                        "item_id": None,
                    }
                )
            else:
                mode = str(negotiation.get("communication_mode", "speech"))
                actions.append(
                    {
                        "id": "parley_open",
                        "label": f"Communicate ({mode})",
                        "kind": "parley",
                        "enabled": True,
                        "item_id": None,
                    }
                )

    return actions


def build_party_slots(world: WorldContent, state: RunState, existing_party: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = [
        {
            "slot_id": "party-1",
            "name": state.player_name,
            "role": "Vanguard",
            "hp": state.hp,
            "max_hp": state.max_hp,
            "attack": player_attack_value(world, state),
            "defence": player_defence_value(),
            "is_player": True,
            "is_active": True,
            "reserve": False,
        }
    ]

    placeholder_count = PARTY_SLOT_COUNT - 1
    allies = active_party_allies(state)
    for index in range(placeholder_count):
        ally = allies[index] if index < len(allies) else None
        existing_slot = existing_party[index + 1] if existing_party and len(existing_party) > (index + 1) else None
        slot_number = index + 2
        if ally is not None:
            slots.append(
                {
                    "slot_id": str(ally.get("slot_id", f"ally-{ally.get('ally_id', slot_number)}")),
                    "name": str(ally.get("name", "Bound ally")),
                    "role": str(ally.get("role", "Bound ally")),
                    "hp": int(ally.get("hp", ally.get("max_hp", 1))),
                    "max_hp": int(ally.get("max_hp", 1)),
                    "attack": int(ally.get("attack", 1)),
                    "defence": int(ally.get("defence", 0)),
                    "is_player": False,
                    "is_active": True,
                    "reserve": False,
                }
            )
            continue
        slots.append(
            {
                "slot_id": existing_slot.get("slot_id", f"party-{slot_number}") if isinstance(existing_slot, dict) else f"party-{slot_number}",
                "name": existing_slot.get("name", "Reserve slot") if isinstance(existing_slot, dict) else "Reserve slot",
                "role": existing_slot.get("role", "Awaiting ally") if isinstance(existing_slot, dict) else "Awaiting ally",
                "hp": int(existing_slot.get("hp", 0)) if isinstance(existing_slot, dict) else 0,
                "max_hp": int(existing_slot.get("max_hp", 0)) if isinstance(existing_slot, dict) else 0,
                "attack": int(existing_slot.get("attack", 0)) if isinstance(existing_slot, dict) else 0,
                "defence": int(existing_slot.get("defence", 0)) if isinstance(existing_slot, dict) else 0,
                "is_player": False,
                "is_active": bool(existing_slot.get("is_active", False)) if isinstance(existing_slot, dict) else False,
                "reserve": bool(existing_slot.get("reserve", True)) if isinstance(existing_slot, dict) else True,
            }
        )

    return slots


def normalize_events(raw_events: Any, fallback_log: list[str], round_number: int) -> list[dict[str, Any]]:
    if isinstance(raw_events, list) and raw_events:
        normalized: list[dict[str, Any]] = []
        for index, raw_event in enumerate(raw_events):
            if not isinstance(raw_event, dict):
                continue
            text = str(raw_event.get("text", "")).strip()
            if not text:
                continue
            raw_actor = raw_event.get("actor")
            actor = str(raw_actor) if raw_actor in {"player", "enemy", "ally", "system"} else "system"
            raw_emphasis = raw_event.get("emphasis")
            emphasis = str(raw_emphasis) if raw_emphasis in {"entry", "impact", "guard", "item", "system", "warning", "support", "parley"} else "system"
            event_round = int(raw_event.get("round", round_number))
            normalized.append(build_combat_event(event_round, actor, text, emphasis, index))
        if normalized:
            return normalized[-EVENT_WINDOW:]

    generated: list[dict[str, Any]] = []
    for index, line in enumerate(fallback_log):
        actor = "enemy" if index == 0 else "system"
        emphasis = "entry" if index == 0 else "system"
        generated.append(build_combat_event(round_number, actor, line, emphasis, index))
    return generated[-EVENT_WINDOW:]


def create_combat_state(world: WorldContent, state: RunState, enemy_id: str, encounter_message: str) -> dict[str, Any]:
    enemy = world.enemies[enemy_id]
    events = [build_combat_event(1, "enemy", encounter_message, "entry", 0)]
    party = build_party_slots(world, state)
    negotiation = build_negotiation_state(enemy)
    combat_state = {
        "mode": "turn-based",
        "status": "engaged",
        "round": 1,
        "enemy": {
            "id": enemy_id,
            "name": enemy["name"],
            "hp": enemy["max_hp"],
            "max_hp": enemy["max_hp"],
            "attack": enemy["damage"],
            "defence": enemy.get("defence", 0),
            "presentation": {
                "mode": "ascii",
                "ascii_art": enemy.get("ascii_art", []),
            },
        },
        "party": party,
        "events": events,
        "log": [event["text"] for event in events],
        "negotiation": negotiation,
        "enemy_id": enemy_id,
        "enemy_name": enemy["name"],
        "enemy_ascii_art": enemy.get("ascii_art", []),
        "enemy_hp": enemy["max_hp"],
        "enemy_max_hp": enemy["max_hp"],
        "enemy_damage": enemy["damage"],
        "enemy_defence": enemy.get("defence", 0),
    }
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)

    # Pinball descriptor — gives the client enough info to seed the table layout
    location = world.locations.get(state.location_id, {}) if state.location_id else {}
    biome_id = location.get("encounter_biome_id") or location.get("biome_id") or "ashen_fields"
    floor_num = int(location.get("encounter_floor", location.get("floor_number", 0) or 0) or 0)
    combat_state["pinball_descriptor"] = {
        "biome_id": str(biome_id),
        "floor_seed": (int(state.run_seed or 0) + floor_num * 10003) & 0xFFFFFFFF,
        "enemy_id": enemy_id,
        "enemy_pinball": enemy.get("pinball", {}),
    }

    return combat_state


def normalize_combat_state(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    if state.combat_state is None:
        return None

    raw_state = state.combat_state
    enemy_payload = raw_state.get("enemy") if isinstance(raw_state.get("enemy"), dict) else None
    enemy_id = str((enemy_payload or {}).get("id") or raw_state.get("enemy_id") or "").strip()
    if not enemy_id or enemy_id not in world.enemies:
        state.in_combat = False
        state.combat_state = None
        return None

    enemy_def = world.enemies[enemy_id]
    round_number = int(raw_state.get("round", 1))
    raw_log_value = raw_state.get("log")
    raw_log: list[Any] = raw_log_value if isinstance(raw_log_value, list) else []
    log = [str(line) for line in raw_log if str(line).strip()]
    events = normalize_events(raw_state.get("events"), log, round_number)
    party = build_party_slots(world, state, raw_state.get("party") if isinstance(raw_state.get("party"), list) else None)
    negotiation = build_negotiation_state(
        enemy_def,
        raw_state.get("negotiation") if isinstance(raw_state.get("negotiation"), dict) else None,
    )

    normalized = {
        "mode": "turn-based",
        "status": "engaged",
        "round": round_number,
        "enemy": {
            "id": enemy_id,
            "name": str((enemy_payload or {}).get("name") or raw_state.get("enemy_name") or enemy_def["name"]),
            "hp": int((enemy_payload or {}).get("hp", raw_state.get("enemy_hp", enemy_def["max_hp"]))),
            "max_hp": int((enemy_payload or {}).get("max_hp", raw_state.get("enemy_max_hp", enemy_def["max_hp"]))),
            "attack": int((enemy_payload or {}).get("attack", raw_state.get("enemy_damage", enemy_def["damage"]))),
            "defence": int((enemy_payload or {}).get("defence", raw_state.get("enemy_defence", enemy_def.get("defence", 0)))),
            "presentation": {
                "mode": "ascii",
                "ascii_art": list((enemy_payload or {}).get("presentation", {}).get("ascii_art", raw_state.get("enemy_ascii_art", enemy_def.get("ascii_art", [])))),
            },
        },
        "party": party,
        "events": events,
        "log": [event["text"] for event in events][-8:],
        "negotiation": negotiation,
        "enemy_id": enemy_id,
        "enemy_name": str((enemy_payload or {}).get("name") or raw_state.get("enemy_name") or enemy_def["name"]),
        "enemy_ascii_art": list((enemy_payload or {}).get("presentation", {}).get("ascii_art", raw_state.get("enemy_ascii_art", enemy_def.get("ascii_art", [])))),
        "enemy_hp": int((enemy_payload or {}).get("hp", raw_state.get("enemy_hp", enemy_def["max_hp"]))),
        "enemy_max_hp": int((enemy_payload or {}).get("max_hp", raw_state.get("enemy_max_hp", enemy_def["max_hp"]))),
        "enemy_damage": int((enemy_payload or {}).get("attack", raw_state.get("enemy_damage", enemy_def["damage"]))),
        "enemy_defence": int((enemy_payload or {}).get("defence", raw_state.get("enemy_defence", enemy_def.get("defence", 0)))),
    }
    normalized["available_actions"] = build_available_actions(world, state, normalized)
    # Preserve pinball_descriptor across round-trips (set once at combat start)
    if raw_state.get("pinball_descriptor") is not None:
        normalized["pinball_descriptor"] = raw_state["pinball_descriptor"]
    state.combat_state = normalized
    return normalized


def append_negotiation_transcript(negotiation: dict[str, Any], speaker: str, text: str) -> None:
    transcript = normalize_negotiation_transcript(negotiation.get("transcript"))
    transcript.append({"speaker": speaker, "text": text})
    negotiation["transcript"] = transcript[-6:]


def party_has_allies_in_combat(combat_state: dict[str, Any]) -> bool:
    party_value = combat_state.get("party")
    party: list[Any] = party_value if isinstance(party_value, list) else []
    return any(isinstance(slot, dict) and not slot.get("is_player") and not slot.get("reserve", True) for slot in party)


def consume_party_allies(state: RunState, combat_state: dict[str, Any]) -> None:
    if not party_has_allies_in_combat(combat_state):
        return

    remaining_allies: list[dict[str, Any]] = []
    for ally in active_party_allies(state):
        remaining_battles = int(ally.get("remaining_battles", 0)) - 1
        if remaining_battles < 1:
            continue
        refreshed_role = str(ally.get("role", "Bound ally")).split(" / ", 1)[0]
        remaining_allies.append({
            **ally,
            "remaining_battles": remaining_battles,
            "role": f"{refreshed_role} / {remaining_battles} battles",
        })
    state.party_allies = remaining_allies


def grant_recruited_ally(state: RunState, enemy_def: dict[str, Any], battles: int) -> dict[str, Any]:
    ally = {
        "ally_id": enemy_def["id"],
        "slot_id": f"ally-{enemy_def['id']}",
        "name": enemy_def["name"],
        "role": f"Bound ally / {battles} battles",
        "hp": int(enemy_def["max_hp"]),
        "max_hp": int(enemy_def["max_hp"]),
        "attack": max(1, int(enemy_def["damage"]) - 1),
        "defence": int(enemy_def.get("defence", 0)),
        "remaining_battles": battles,
    }
    allies = active_party_allies(state)
    for index, existing in enumerate(allies):
        if existing.get("ally_id") == ally["ally_id"]:
            allies[index] = ally
            state.party_allies = allies[: PARTY_SLOT_COUNT - 1]
            return ally
    allies.append(ally)
    state.party_allies = allies[: PARTY_SLOT_COUNT - 1]
    return ally


def award_tribute(world: WorldContent, state: RunState, enemy_def: dict[str, Any]) -> str:
    profile = enemy_negotiation_profile(enemy_def)
    if profile is None or not profile.get("tribute_item_id"):
        gold_min, gold_max = enemy_def.get("gold_drop", [1, 2])
        gold = deterministic_roll(state.run_seed, enemy_def["id"], state.steps_taken, "tribute-gold", low=gold_min, high=gold_max)
        state.gold += gold
        return f"{enemy_def['name']} yields {gold} gold rather than risk your blade."

    item_id = str(profile["tribute_item_id"])
    quantity = int(profile["tribute_quantity"])
    add_item(state, world, item_id, quantity)
    item_name = world.items[item_id]["name"]
    return f"{enemy_def['name']} offers {item_name} x{quantity} to end the standoff."


def parley_target_number(profile: dict[str, Any], negotiation: dict[str, Any], action: str) -> int:
    base = int(profile["difficulty"])
    modifiers = {
        "parley_recruit": 2,
        "parley_tribute": 1,
        "parley_retreat": 0,
    }
    temperament = str(profile.get("temperament", "wary"))
    temperament_penalty = {"wary": 0, "resentful": 2, "irate": 4}.get(temperament, 0)
    leverage = int(negotiation.get("leverage", 0))
    return max(2, min(10, base + modifiers.get(action, 0) + temperament_penalty + int(negotiation.get("anger", 0)) - leverage))


def update_negotiation_lock(negotiation: dict[str, Any], enemy_def: dict[str, Any]) -> None:
    profile = enemy_negotiation_profile(enemy_def)
    if profile is None:
        return
    if int(negotiation.get("anger", 0)) >= int(negotiation.get("anger_limit", profile["anger_limit"])):
        negotiation["locked"] = True
        negotiation["available"] = False
        negotiation["active"] = False
        negotiation["lock_reason"] = "The creature rejects any further terms and commits fully to violence."


def analyze_parley_message(profile: dict[str, Any], message: str, negotiation: dict[str, Any]) -> dict[str, Any]:
    lowered = message.lower()
    inferred_intent = str(negotiation.get("active_intent") or "").strip() or None
    leverage_delta = 0
    anger_delta = 0
    calming = False

    respect_terms = ("please", "peace", "terms", "listen", "parley", "spare", "understand")
    apology_terms = ("sorry", "forgive", "mean no", "no wish", "no need")
    recruit_terms = ("join", "together", "beside", "aid", "help", "with me")
    tribute_terms = ("tribute", "offer", "give", "payment", "gift", "toll")
    retreat_terms = ("retreat", "withdraw", "leave", "back away", "go now", "stand down")
    threat_terms = ("or die", "kill", "destroy", "cut you down", "burn", "end you")
    insult_terms = ("fool", "worm", "beast", "vermin", "filth", "stupid")

    if any(term in lowered for term in respect_terms):
        leverage_delta += 1
        calming = True
    if any(term in lowered for term in apology_terms):
        leverage_delta += 1
        calming = True

    if any(term in lowered for term in recruit_terms):
        inferred_intent = "recruit"
        if "recruit" in profile["outcomes"]:
            leverage_delta += 1
    if any(term in lowered for term in tribute_terms):
        inferred_intent = "tribute"
        if "tribute" in profile["outcomes"]:
            leverage_delta += 1
    if any(term in lowered for term in retreat_terms):
        inferred_intent = "retreat"
        if "retreat" in profile["outcomes"]:
            leverage_delta += 1

    if any(term in lowered for term in threat_terms):
        if inferred_intent == "retreat" and "retreat" in profile["outcomes"]:
            leverage_delta += 1
        else:
            leverage_delta -= 1
        anger_delta += 1
    if any(term in lowered for term in insult_terms):
        leverage_delta -= 1
        anger_delta += 1

    word_count = len([part for part in lowered.replace("\n", " ").split(" ") if part])
    if word_count < 3:
        leverage_delta -= 1

    temperament = str(profile.get("temperament", "wary"))
    if temperament == "resentful" and calming:
        leverage_delta += 1
    if temperament == "irate" and calming:
        leverage_delta -= 1

    leverage_delta = max(-2, min(3, leverage_delta))
    anger_delta = max(-1 if calming else 0, min(2, anger_delta))

    if leverage_delta >= 2:
        reply = "The creature stills for a moment, weighing what you said."
    elif leverage_delta == 1:
        reply = "The creature does not yield, but it keeps listening."
    elif anger_delta > 0:
        reply = "Your words bite wrong, and the creature answers with rising hostility."
    else:
        reply = "The creature hears you, but the meaning slides off without purchase."

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


def resolve_parley_action(
    world: WorldContent,
    state: RunState,
    combat_state: dict[str, Any],
    enemy_def: dict[str, Any],
    action: str,
    message: str | None = None,
    parley_service: CombatParleyService | None = None,
) -> tuple[bool, bool, list[tuple[str, str, str]]]:
    negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
    if negotiation is None:
        state.message = "This enemy cannot reason with you."
        return False, False, []

    profile = enemy_negotiation_profile(enemy_def)
    if profile is None:
        state.message = "This enemy cannot reason with you."
        return False, False, []

    if action == "parley_open":
        if not negotiation.get("available"):
            state.message = str(negotiation.get("lock_reason") or "No opening for parley.")
            return False, False, []
        negotiation["active"] = True
        line = (
            parley_service.generate_open_line(world, state, combat_state, enemy_def, negotiation)
            if parley_service is not None
            else f"You open parley. {enemy_def['name']} answers by {negotiation['communication_mode']}, waiting for your terms."
        )
        append_negotiation_transcript(negotiation, "player", "You call for terms.")
        append_negotiation_transcript(negotiation, "enemy", line)
        combat_state["available_actions"] = build_available_actions(world, state, combat_state)
        state.message = line
        return False, False, [("system", line, "parley")]

    if action == "parley_end":
        if not negotiation.get("active"):
            state.message = "No active parley to break."
            return False, False, []
        negotiation["active"] = False
        negotiation["anger"] = int(negotiation.get("anger", 0)) + 1
        append_negotiation_transcript(negotiation, "player", "You let the talks fall away.")
        update_negotiation_lock(negotiation, enemy_def)
        line = "The silence hardens the creature's posture."
        append_negotiation_transcript(negotiation, "system", line)
        combat_state["available_actions"] = build_available_actions(world, state, combat_state)
        state.message = line
        return False, True, [("system", line, "warning")]

    if action == "parley_message":
        if not negotiation.get("active"):
            state.message = "Open parley before you speak."
            return False, False, []

        text = str(message or "").strip()
        if not text:
            state.message = "Say something concrete before sending the line."
            return False, False, []

        negotiation["attempts"] = int(negotiation.get("attempts", 0)) + 1
        analysis = analyze_parley_message(profile, text, negotiation)
        leverage = int(negotiation.get("leverage", 0)) + int(analysis["leverage_delta"])
        anger = int(negotiation.get("anger", 0)) + int(analysis["anger_delta"])
        negotiation["leverage"] = max(-3, min(3, leverage))
        negotiation["anger"] = max(0, anger)
        if analysis["inferred_intent"] in profile["outcomes"]:
            negotiation["active_intent"] = analysis["inferred_intent"]
        line = (
            parley_service.generate_reply(world, state, combat_state, enemy_def, negotiation, text, analysis)
            if parley_service is not None
            else str(analysis["reply"])
        )
        append_negotiation_transcript(negotiation, "player", text)
        append_negotiation_transcript(negotiation, "enemy", line)
        update_negotiation_lock(negotiation, enemy_def)
        combat_state["available_actions"] = build_available_actions(world, state, combat_state)
        state.message = line
        return False, not bool(analysis["grants_pause"]) or bool(analysis["provoked"]), [
            ("enemy" if analysis["provoked"] else "system", line, "warning" if analysis["provoked"] else "parley")
        ]

    if not negotiation.get("active"):
        state.message = "Open parley before you press for terms."
        return False, False, []

    if action not in {"parley_recruit", "parley_tribute", "parley_retreat"}:
        state.message = f"Unknown combat action: {action}"
        return False, False, []

    requested_outcome = action.removeprefix("parley_")
    if requested_outcome not in profile["outcomes"]:
        state.message = "That demand finds no purchase with this foe."
        return False, False, []

    negotiation["attempts"] = int(negotiation.get("attempts", 0)) + 1
    negotiation["active_intent"] = requested_outcome
    roll = deterministic_roll(
        state.run_seed,
        enemy_def["id"],
        state.steps_taken,
        combat_state.get("round", 1),
        action,
        negotiation["attempts"],
        low=1,
        high=10,
    )
    target = parley_target_number(profile, negotiation, action)
    append_negotiation_transcript(negotiation, "player", NEGOTIATION_OUTCOMES[requested_outcome])

    if roll >= target:
        negotiation["outcome"] = requested_outcome
        negotiation["active"] = False
        negotiation["available"] = False
        negotiation["locked"] = True
        if action == "parley_recruit":
            ally = grant_recruited_ally(state, enemy_def, int(profile["ally_battles"]))
            line = f"{enemy_def['name']} lowers its guard and agrees to fight beside you for {ally['remaining_battles']} battles."
        elif action == "parley_tribute":
            line = award_tribute(world, state, enemy_def)
        else:
            line = f"{enemy_def['name']} yields the ground and withdraws."
        negotiation["lock_reason"] = line
        append_negotiation_transcript(negotiation, "enemy", line)
        state.in_combat = False
        state.combat_state = None
        state.message = line
        return True, False, [("enemy", line, "parley")]

    negotiation["anger"] = int(negotiation.get("anger", 0)) + 1
    update_negotiation_lock(negotiation, enemy_def)
    line = f"{enemy_def['name']} rejects the offer and grows sharper."
    append_negotiation_transcript(negotiation, "enemy", line)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    state.message = line
    return False, True, [("enemy", line, "warning")]


def resolve_ally_support(
    state: RunState,
    combat_state: dict[str, Any],
    enemy_state: dict[str, Any],
    enemy_defence: int,
) -> list[tuple[str, str, str]]:
    combat_events: list[tuple[str, str, str]] = []
    allies = active_party_allies(state)
    if not allies:
        return combat_events

    total_damage = 0
    names: list[str] = []
    round_number = int(combat_state.get("round", 1))
    for ally in allies:
        variance = deterministic_roll(state.run_seed, ally.get("ally_id", ally.get("name", "ally")), round_number, "ally", low=0, high=1)
        damage = max(1, int(ally.get("attack", 1)) + variance - enemy_defence)
        total_damage += damage
        names.append(str(ally.get("name", "Ally")))

    enemy_state["hp"] = max(0, int(enemy_state["hp"]) - total_damage)
    combat_events.append(("ally", f"{', '.join(names)} strike for {total_damage} damage.", "support"))
    return combat_events


def append_combat_events(combat_state: dict[str, Any], round_number: int, additions: list[tuple[str, str, str]]) -> None:
    existing = combat_state.get("events") if isinstance(combat_state.get("events"), list) else []
    events = normalize_events(existing, combat_state.get("log", []), round_number)
    base_index = len(events)
    for offset, (actor, text, emphasis) in enumerate(additions):
        events.append(build_combat_event(round_number, actor, text, emphasis, base_index + offset))
    combat_state["events"] = events[-EVENT_WINDOW:]
    combat_state["log"] = [event["text"] for event in combat_state["events"]][-8:]


def deterministic_roll(run_seed: int, *parts: Any, low: int, high: int) -> int:
    span = high - low + 1
    checksum = run_seed
    for part in parts:
        checksum += sum(ord(character) for character in str(part))
    return low + (checksum % span)


def maybe_start_encounter(world: WorldContent, state: RunState, moved: bool = True) -> None:
    if state.in_combat or state.run_result is not None or not moved:
        return

    location = resolve_location(world, state.location_id)
    encounter_context = encounter_context_for_location(world, location)
    if not encounter_context["enabled"]:
        return

    encounter = next(
        (
            candidate
            for candidate in world.encounters
            if candidate["biome_id"] == encounter_context["biome_id"]
            and int(candidate["floor_number"]) == int(encounter_context["floor_number"])
        ),
        None,
    )
    if encounter is None and int(encounter_context["floor_number"]) != 0:
        encounter = next(
            (
                candidate
                for candidate in world.encounters
                if candidate["biome_id"] == encounter_context["biome_id"]
                and int(candidate["floor_number"]) == 0
            ),
            None,
        )
    if encounter is None:
        return

    encounter_roll = deterministic_roll(
        state.run_seed,
        state.location_id,
        state.x,
        state.y,
        state.steps_taken,
        "encounter-rate",
        low=1,
        high=100,
    )
    if encounter_roll > int(encounter_context["encounter_rate"]):
        return

    enemy_ids = encounter["enemy_ids"]
    enemy_index = deterministic_roll(
        state.run_seed,
        state.location_id,
        state.x,
        state.y,
        state.steps_taken,
        "encounter-enemy",
        low=0,
        high=len(enemy_ids) - 1,
    )
    enemy_id = enemy_ids[enemy_index]
    enemy = world.enemies[enemy_id]
    encounter_message = encounter.get("message_by_enemy", {}).get(enemy_id)
    if encounter_message is None:
        encounter_message = encounter["message"].format(enemy_name=enemy["name"])
    state.in_combat = True
    state.combat_state = create_combat_state(world, state, enemy_id, encounter_message)
    state.message = encounter_message
    triggered = state.triggered_encounters or []
    triggered.append(f"{state.location_id}:{state.steps_taken}:{enemy_id}")
    state.triggered_encounters = triggered[-24:]


def resolve_turn(
    world: WorldContent,
    state: RunState,
    action: str,
    message: str | None = None,
    parley_service: CombatParleyService | None = None,
) -> None:
    if not state.in_combat or state.combat_state is None:
        state.message = "There is no active combat to resolve."
        return

    combat_state = normalize_combat_state(world, state)
    if combat_state is None:
        state.message = "Combat state could not be restored."
        return

    enemy_state = combat_state["enemy"]
    enemy_def = world.enemies[enemy_state["id"]]
    combat_events: list[tuple[str, str, str]] = []
    enemy_defence = int(enemy_state.get("defence", 0))
    round_number = int(combat_state.get("round", 1))
    defended = False
    enemy_should_attack = True

    if action.startswith("parley_"):
        combat_resolved, enemy_should_attack, negotiation_events = resolve_parley_action(
            world,
            state,
            combat_state,
            enemy_def,
            action,
            message=message,
            parley_service=parley_service,
        )
        if combat_resolved:
            return
        if negotiation_events:
            combat_events.extend(negotiation_events)
        combat_state["enemy_hp"] = enemy_state["hp"]
        combat_state["enemy_max_hp"] = enemy_state["max_hp"]
        combat_state["enemy_damage"] = enemy_state["attack"]
        combat_state["enemy_defence"] = enemy_state["defence"]
        if not enemy_should_attack:
            append_combat_events(combat_state, round_number, combat_events)
            combat_state["party"] = build_party_slots(world, state, combat_state.get("party"))
            combat_state["available_actions"] = build_available_actions(world, state, combat_state)
            state.combat_state = combat_state
            return

    elif action == "attack":
        negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
        if negotiation and negotiation.get("active"):
            negotiation["active"] = False
            negotiation["locked"] = True
            negotiation["available"] = False
            negotiation["lock_reason"] = "Steel ended the talk."
            append_negotiation_transcript(negotiation, "system", "Steel ends the parley.")
        base_damage = player_attack_value(world, state)
        variance = deterministic_roll(state.run_seed, combat_state["enemy_id"], round_number, action, low=0, high=2)
        damage = max(1, base_damage + variance - enemy_defence)
        enemy_state["hp"] = max(0, int(enemy_state["hp"]) - damage)
        combat_events.append(("player", f"You strike for {damage} damage.", "impact"))
    elif action.startswith("pinball_strike:"):
        try:
            score = max(0, int(action.split(":", 1)[1]))
        except ValueError:
            score = 0
        damage = max(0, score - enemy_defence)
        if damage > 0:
            enemy_state["hp"] = max(0, int(enemy_state["hp"]) - damage)
            combat_events.append(("player", f"You channel {damage} damage into {enemy_def['name']}.", "impact"))
        else:
            combat_events.append(("player", "Your strike glances off.", "guard"))
    elif action == "defend":
        defended = True
        combat_events.append(("player", "You brace for the enemy's counterattack.", "guard"))
    elif action.startswith("use_item:"):
        item_id = action.split(":", 1)[1]
        success, message = use_item(state, world, item_id)
        if not success:
            state.message = message
            combat_state["available_actions"] = build_available_actions(world, state, combat_state)
            return
        combat_events.append(("player", message, "item"))
    elif action == "flee":
        consume_party_allies(state, combat_state)
        state.in_combat = False
        state.combat_state = None
        state.message = "You break away and regain your footing."
        return
    else:
        state.message = f"Unknown combat action: {action}"
        return

    if int(enemy_state["hp"]) <= 0:
        loot_summary = apply_loot(world, state, enemy_def)
        state.enemies_defeated += 1
        consume_party_allies(state, combat_state)
        state.in_combat = False
        state.combat_state = None
        state.message = f"You defeat {enemy_def['name']}. {loot_summary}".strip()
        return

    combat_events.extend(resolve_ally_support(state, combat_state, enemy_state, enemy_defence))

    if int(enemy_state["hp"]) <= 0:
        loot_summary = apply_loot(world, state, enemy_def)
        state.enemies_defeated += 1
        consume_party_allies(state, combat_state)
        state.in_combat = False
        state.combat_state = None
        state.message = f"Your party breaks {enemy_def['name']}. {loot_summary}".strip()
        return

    if enemy_should_attack:
        negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
        anger_bonus = int(negotiation.get("anger", 0)) if negotiation else 0
        enemy_variance = deterministic_roll(state.run_seed, combat_state["enemy_id"], round_number, "enemy", low=0, high=2)
        enemy_damage = max(1, int(enemy_def["damage"]) + enemy_variance + min(2, anger_bonus) - (2 if defended else 0))
        state.hp = max(0, state.hp - enemy_damage)
        combat_events.append(("enemy", f"{enemy_def['name']} hits you for {enemy_damage} damage.", "impact"))
    combat_state["round"] = round_number + 1
    enemy_state["attack"] = int(enemy_def["damage"])
    enemy_state["defence"] = int(enemy_def.get("defence", 0))
    append_combat_events(combat_state, round_number, combat_events)
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    combat_state["enemy_hp"] = enemy_state["hp"]
    combat_state["enemy_max_hp"] = enemy_state["max_hp"]
    combat_state["enemy_damage"] = enemy_state["attack"]
    combat_state["enemy_defence"] = enemy_state["defence"]
    combat_state["party"] = build_party_slots(world, state, combat_state.get("party"))
    state.combat_state = combat_state
    state.message = combat_events[-1][1]

    if state.hp <= 0:
        state.hp = 0
        consume_party_allies(state, combat_state)
        state.in_combat = False
        state.combat_state = None
        state.run_result = "death"
        state.status = "dead"
        state.message = f"{enemy_def['name']} cuts you down in the dark."


def apply_loot(world: WorldContent, state: RunState, enemy_def: dict[str, Any]) -> str:
    gold_min, gold_max = enemy_def.get("gold_drop", [0, 0])
    gold_found = deterministic_roll(state.run_seed, enemy_def["id"], state.enemies_defeated, "gold", low=gold_min, high=gold_max)
    state.gold += gold_found

    looted_items: list[str] = []
    for loot_entry in enemy_def.get("loot_table", []):
        threshold = int(float(loot_entry.get("chance", 0)) * 100)
        roll = deterministic_roll(state.run_seed, enemy_def["id"], loot_entry["item_id"], state.enemies_defeated, low=1, high=100)
        if roll <= threshold:
            add_item(state, world, loot_entry["item_id"], int(loot_entry.get("quantity", 1)))
            looted_items.append(world.items[loot_entry["item_id"]]["name"])

    recovered_quest_items = recover_active_fetch_quest_items(world, state)
    for recovery in recovered_quest_items:
        looted_items.append(f"{recovery['item_name']} for {recovery['npc_name']}")

    if looted_items:
        return f"You recover {gold_found} gold and {', '.join(looted_items)}."
    return f"You recover {gold_found} gold."
