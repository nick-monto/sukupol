from __future__ import annotations

from typing import Any

from ..content import WorldContent
from ..game import RunState

from .negotiation import build_negotiation_state
from .party import build_available_actions, build_party_slots


EVENT_WINDOW = 12
FLOOR_SEED_MULTIPLIER = 10003


def build_combat_event(round_number: int, actor: str, text: str, emphasis: str, index: int) -> dict[str, Any]:
    return {
        "id": f"round-{round_number}-{actor}-{index}",
        "round": round_number, "actor": actor, "text": text, "emphasis": emphasis,
    }

def _normalize_single_event(index: int, raw_event: dict[str, Any], round_number: int) -> dict[str, Any] | None:
    text = str(raw_event.get("text", "")).strip()
    if not text:
        return None
    raw_actor = raw_event.get("actor")
    actor = str(raw_actor) if raw_actor in {"player", "enemy", "ally", "system"} else "system"
    valid_emphases = {"entry", "impact", "guard", "item", "system", "warning", "support", "parley"}
    raw_emphasis = raw_event.get("emphasis")
    emphasis = str(raw_emphasis) if raw_emphasis in valid_emphases else "system"
    event_round = int(raw_event.get("round", round_number))
    return build_combat_event(event_round, actor, text, emphasis, index)

def normalize_events(raw_events: Any, fallback_log: list[str], round_number: int) -> list[dict[str, Any]]:
    if isinstance(raw_events, list) and raw_events:
        normalized: list[dict[str, Any]] = []
        for index, raw_event in enumerate(raw_events):
            if isinstance(raw_event, dict):
                event = _normalize_single_event(index, raw_event, round_number)
                if event is not None:
                    normalized.append(event)
        if normalized:
            return normalized[-EVENT_WINDOW:]
    generated: list[dict[str, Any]] = []
    for index, line in enumerate(fallback_log):
        actor = "enemy" if index == 0 else "system"
        emphasis = "entry" if index == 0 else "system"
        generated.append(build_combat_event(round_number, actor, line, emphasis, index))
    return generated[-EVENT_WINDOW:]

def _build_combat_enemy_state(enemy_def: dict[str, Any], enemy_id: str) -> dict[str, Any]:
    return {
        "id": enemy_id, "name": enemy_def["name"],
        "hp": enemy_def["max_hp"], "max_hp": enemy_def["max_hp"],
        "attack": enemy_def["damage"], "defence": enemy_def.get("defence", 0),
        "presentation": {"mode": "ascii", "ascii_art": enemy_def.get("ascii_art", [])},
    }

def _build_pinball_descriptor(world: WorldContent, state: RunState, enemy_id: str) -> dict[str, Any]:
    location = world.locations.get(state.location_id, {}) if state.location_id else {}
    biome_id = location.get("encounter_biome_id") or location.get("biome_id") or "ashen_fields"
    floor_num = int(location.get("encounter_floor", location.get("floor_number", 0) or 0) or 0)
    return {
        "biome_id": str(biome_id),
        "floor_seed": (int(state.run_seed or 0) + floor_num * FLOOR_SEED_MULTIPLIER) & 0xFFFFFFFF,
        "enemy_id": enemy_id,
        "enemy_pinball": world.enemies[enemy_id].get("pinball", {}),
    }

def create_combat_state(world: WorldContent, state: RunState, enemy_id: str, encounter_message: str) -> dict[str, Any]:
    enemy = world.enemies[enemy_id]
    events = [build_combat_event(1, "enemy", encounter_message, "entry", 0)]
    party = build_party_slots(world, state)
    negotiation = build_negotiation_state(enemy)
    enemy_state = _build_combat_enemy_state(enemy, enemy_id)
    combat_state: dict[str, Any] = {
        "mode": "turn-based", "status": "engaged", "round": 1,
        "enemy": enemy_state, "party": party, "events": events,
        "log": [event["text"] for event in events],
        "negotiation": negotiation,
        "enemy_id": enemy_id, "enemy_name": enemy["name"],
        "enemy_ascii_art": enemy.get("ascii_art", []),
        "enemy_hp": enemy["max_hp"], "enemy_max_hp": enemy["max_hp"],
        "enemy_damage": enemy["damage"], "enemy_defence": enemy.get("defence", 0),
    }
    combat_state["available_actions"] = build_available_actions(world, state, combat_state)
    combat_state["pinball_descriptor"] = _build_pinball_descriptor(world, state, enemy_id)
    return combat_state

def _normalized_enemy_state(
    raw_state: dict[str, Any], enemy_def: dict[str, Any], enemy_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    ep = enemy_payload or {}
    return {
        "id": str(ep.get("id") or raw_state.get("enemy_id") or enemy_def["id"]),
        "name": str(ep.get("name") or raw_state.get("enemy_name") or enemy_def["name"]),
        "hp": int(ep.get("hp", raw_state.get("enemy_hp", enemy_def["max_hp"]))),
        "max_hp": int(ep.get("max_hp", raw_state.get("enemy_max_hp", enemy_def["max_hp"]))),
        "attack": int(ep.get("attack", raw_state.get("enemy_damage", enemy_def["damage"]))),
        "defence": int(ep.get("defence", raw_state.get("enemy_defence", enemy_def.get("defence", 0)))),
        "presentation": {
            "mode": "ascii",
            "ascii_art": list(ep.get("presentation", {}).get("ascii_art", raw_state.get("enemy_ascii_art", enemy_def.get("ascii_art", [])))),
        },
    }

def _validate_raw_combat_state(world: WorldContent, state: RunState) -> tuple[dict[str, Any], dict[str, Any], int] | None:
    if state.combat_state is None:
        return None
    raw = state.combat_state
    ep = raw.get("enemy") if isinstance(raw.get("enemy"), dict) else None
    eid = str((ep or {}).get("id") or raw.get("enemy_id") or "").strip()
    if not eid or eid not in world.enemies:
        state.in_combat = False
        state.combat_state = None
        return None
    return raw, world.enemies[eid], int(raw.get("round", 1))

def _build_normalized_dict(
    raw: dict[str, Any], enemy_def: dict[str, Any],
    round_number: int, events: list[dict[str, Any]],
    party: list[dict[str, Any]], negotiation: dict[str, Any] | None,
    ep: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "mode": "turn-based", "status": "engaged", "round": round_number,
        "enemy": _normalized_enemy_state(raw, enemy_def, ep),
        "party": party, "events": events,
        "log": [event["text"] for event in events][-8:],
        "negotiation": negotiation,
        "enemy_id": raw.get("enemy_id", ""),
        "enemy_name": str((ep or {}).get("name") or raw.get("enemy_name") or enemy_def["name"]),
        "enemy_ascii_art": list((ep or {}).get("presentation", {}).get("ascii_art", raw.get("enemy_ascii_art", enemy_def.get("ascii_art", [])))),
        "enemy_hp": int((ep or {}).get("hp", raw.get("enemy_hp", enemy_def["max_hp"]))),
        "enemy_max_hp": int((ep or {}).get("max_hp", raw.get("enemy_max_hp", enemy_def["max_hp"]))),
        "enemy_damage": int((ep or {}).get("attack", raw.get("enemy_damage", enemy_def["damage"]))),
        "enemy_defence": int((ep or {}).get("defence", raw.get("enemy_defence", enemy_def.get("defence", 0)))),
    }


def normalize_combat_state(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    result = _validate_raw_combat_state(world, state)
    if result is None:
        return None
    raw, enemy_def, round_number = result
    ep = raw.get("enemy") if isinstance(raw.get("enemy"), dict) else None
    raw_log_value = raw.get("log")
    raw_log: list[Any] = raw_log_value if isinstance(raw_log_value, list) else []
    log = [str(l) for l in raw_log if str(l).strip()]
    events = normalize_events(raw.get("events"), log, round_number)
    party = build_party_slots(world, state, raw.get("party") if isinstance(raw.get("party"), list) else None)
    negotiation = build_negotiation_state(enemy_def, raw.get("negotiation") if isinstance(raw.get("negotiation"), dict) else None)
    normalized = _build_normalized_dict(raw, enemy_def, round_number, events, party, negotiation, ep)
    normalized["available_actions"] = build_available_actions(world, state, normalized)
    if raw.get("pinball_descriptor") is not None:
        normalized["pinball_descriptor"] = raw["pinball_descriptor"]
    state.combat_state = normalized
    return normalized

def append_combat_events(combat_state: dict[str, Any], round_number: int, additions: list[tuple[str, str, str]]) -> None:
    existing = combat_state.get("events") if isinstance(combat_state.get("events"), list) else []
    events = normalize_events(existing, combat_state.get("log", []), round_number)
    base_index = len(events)
    for offset, (actor, text, emphasis) in enumerate(additions):
        events.append(build_combat_event(round_number, actor, text, emphasis, base_index + offset))
    combat_state["events"] = events[-EVENT_WINDOW:]
    combat_state["log"] = [event["text"] for event in combat_state["events"]][-8:]
