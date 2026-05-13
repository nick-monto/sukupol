from __future__ import annotations

from typing import Any

from .content import WorldContent
from .game import RunState, encounter_context_for_location, resolve_location
from .inventory import add_item, get_equipped_weapon, use_item
from .quests import recover_active_fetch_quest_items


PARTY_SLOT_COUNT = 3
EVENT_WINDOW = 12


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


def build_available_actions(state: RunState) -> list[dict[str, Any]]:
    potion_count = inventory_quantity(state, "health_potion")
    return [
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
    for index in range(placeholder_count):
        existing_slot = existing_party[index + 1] if existing_party and len(existing_party) > (index + 1) else None
        slot_number = index + 2
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
            actor = raw_event.get("actor") if raw_event.get("actor") in {"player", "enemy", "system"} else "system"
            emphasis = raw_event.get("emphasis") if raw_event.get("emphasis") in {"entry", "impact", "guard", "item", "system", "warning"} else "system"
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
    combat_state = {
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
        "available_actions": build_available_actions(state),
        "events": events,
        "log": [event["text"] for event in events],
        "enemy_id": enemy_id,
        "enemy_name": enemy["name"],
        "enemy_ascii_art": enemy.get("ascii_art", []),
        "enemy_hp": enemy["max_hp"],
        "enemy_max_hp": enemy["max_hp"],
        "enemy_damage": enemy["damage"],
        "enemy_defence": enemy.get("defence", 0),
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
    raw_log = raw_state.get("log") if isinstance(raw_state.get("log"), list) else []
    log = [str(line) for line in raw_log if str(line).strip()]
    events = normalize_events(raw_state.get("events"), log, round_number)
    party = build_party_slots(world, state, raw_state.get("party") if isinstance(raw_state.get("party"), list) else None)

    normalized = {
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
        "available_actions": build_available_actions(state),
        "events": events,
        "log": [event["text"] for event in events][-8:],
        "enemy_id": enemy_id,
        "enemy_name": str((enemy_payload or {}).get("name") or raw_state.get("enemy_name") or enemy_def["name"]),
        "enemy_ascii_art": list((enemy_payload or {}).get("presentation", {}).get("ascii_art", raw_state.get("enemy_ascii_art", enemy_def.get("ascii_art", [])))),
        "enemy_hp": int((enemy_payload or {}).get("hp", raw_state.get("enemy_hp", enemy_def["max_hp"]))),
        "enemy_max_hp": int((enemy_payload or {}).get("max_hp", raw_state.get("enemy_max_hp", enemy_def["max_hp"]))),
        "enemy_damage": int((enemy_payload or {}).get("attack", raw_state.get("enemy_damage", enemy_def["damage"]))),
        "enemy_defence": int((enemy_payload or {}).get("defence", raw_state.get("enemy_defence", enemy_def.get("defence", 0)))),
    }
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


def resolve_turn(world: WorldContent, state: RunState, action: str) -> None:
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

    if action == "attack":
        base_damage = player_attack_value(world, state)
        variance = deterministic_roll(state.run_seed, combat_state["enemy_id"], round_number, action, low=0, high=2)
        damage = max(1, base_damage + variance - enemy_defence)
        enemy_state["hp"] = max(0, int(enemy_state["hp"]) - damage)
        combat_events.append(("player", f"You strike for {damage} damage.", "impact"))
    elif action == "defend":
        defended = True
        combat_events.append(("player", "You brace for the enemy's counterattack.", "guard"))
    elif action.startswith("use_item:"):
        item_id = action.split(":", 1)[1]
        success, message = use_item(state, world, item_id)
        if not success:
            state.message = message
            combat_state["available_actions"] = build_available_actions(state)
            return
        combat_events.append(("player", message, "item"))
    elif action == "flee":
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
        state.in_combat = False
        state.combat_state = None
        state.message = f"You defeat {enemy_def['name']}. {loot_summary}".strip()
        return

    enemy_variance = deterministic_roll(state.run_seed, combat_state["enemy_id"], round_number, "enemy", low=0, high=2)
    enemy_damage = max(1, int(enemy_def["damage"]) + enemy_variance - (2 if defended else 0))
    state.hp = max(0, state.hp - enemy_damage)
    combat_events.append(("enemy", f"{enemy_def['name']} hits you for {enemy_damage} damage.", "impact"))
    combat_state["round"] = round_number + 1
    enemy_state["attack"] = int(enemy_def["damage"])
    enemy_state["defence"] = int(enemy_def.get("defence", 0))
    append_combat_events(combat_state, round_number, combat_events)
    combat_state["available_actions"] = build_available_actions(state)
    combat_state["enemy_hp"] = enemy_state["hp"]
    combat_state["enemy_max_hp"] = enemy_state["max_hp"]
    combat_state["enemy_damage"] = enemy_state["attack"]
    combat_state["enemy_defence"] = enemy_state["defence"]
    combat_state["party"] = build_party_slots(world, state, combat_state.get("party"))
    state.message = combat_events[-1][1]

    if state.hp <= 0:
        state.hp = 0
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
