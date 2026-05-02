from __future__ import annotations

from typing import Any

from .content import WorldContent
from .game import RunState, resolve_location
from .inventory import add_item, get_equipped_weapon, use_item


def deterministic_roll(run_seed: int, *parts: Any, low: int, high: int) -> int:
    span = high - low + 1
    checksum = run_seed
    for part in parts:
        checksum += sum(ord(character) for character in str(part))
    return low + (checksum % span)


def maybe_start_encounter(world: WorldContent, state: RunState) -> None:
    if state.in_combat or state.run_result is not None:
        return
    if not state.location_id.startswith("dungeon:"):
        return
    triggered = state.triggered_encounters or []
    if state.location_id in triggered:
        return

    location = resolve_location(world, state.location_id)
    encounter = next(
        (
            candidate
            for candidate in world.encounters
            if candidate["biome_id"] == location.get("biome_id")
            and int(candidate["floor_number"]) == int(location.get("floor_number", 1))
        ),
        None,
    )
    if encounter is None:
        triggered.append(state.location_id)
        state.triggered_encounters = triggered
        return

    enemy_id = encounter["enemy_ids"][0]
    enemy = world.enemies[enemy_id]
    state.in_combat = True
    state.combat_state = {
        "enemy_id": enemy_id,
        "enemy_name": enemy["name"],
        "enemy_hp": enemy["max_hp"],
        "enemy_max_hp": enemy["max_hp"],
        "enemy_damage": enemy["damage"],
        "enemy_defence": enemy.get("defence", 0),
        "round": 1,
        "log": [encounter["message"]],
    }
    state.message = encounter["message"]
    triggered.append(state.location_id)
    state.triggered_encounters = triggered


def resolve_turn(world: WorldContent, state: RunState, action: str) -> None:
    if not state.in_combat or state.combat_state is None:
        state.message = "There is no active combat to resolve."
        return

    combat_state = state.combat_state
    enemy_def = world.enemies[combat_state["enemy_id"]]
    combat_log: list[str] = []
    enemy_defence = int(combat_state.get("enemy_defence", 0))
    round_number = int(combat_state.get("round", 1))
    defended = False

    if action == "attack":
        weapon = get_equipped_weapon(world, state)
        base_damage = int(weapon.get("damage", 1)) if weapon else 1
        variance = deterministic_roll(state.run_seed, combat_state["enemy_id"], round_number, action, low=0, high=2)
        damage = max(1, base_damage + variance - enemy_defence)
        combat_state["enemy_hp"] = max(0, int(combat_state["enemy_hp"]) - damage)
        combat_log.append(f"You strike for {damage} damage.")
    elif action == "defend":
        defended = True
        combat_log.append("You brace for the enemy's counterattack.")
    elif action.startswith("use_item:"):
        item_id = action.split(":", 1)[1]
        success, message = use_item(state, world, item_id)
        if not success:
            state.message = message
            return
        combat_log.append(message)
    elif action == "flee":
        state.in_combat = False
        state.combat_state = None
        state.message = "You break away and regain your footing."
        return
    else:
        state.message = f"Unknown combat action: {action}"
        return

    if int(combat_state["enemy_hp"]) <= 0:
        loot_summary = apply_loot(world, state, enemy_def)
        state.enemies_defeated += 1
        state.in_combat = False
        state.combat_state = None
        state.message = f"You defeat {enemy_def['name']}. {loot_summary}".strip()
        return

    enemy_variance = deterministic_roll(state.run_seed, combat_state["enemy_id"], round_number, "enemy", low=0, high=2)
    enemy_damage = max(1, int(enemy_def["damage"]) + enemy_variance - (2 if defended else 0))
    state.hp = max(0, state.hp - enemy_damage)
    combat_log.append(f"{enemy_def['name']} hits you for {enemy_damage} damage.")
    combat_state["round"] = round_number + 1
    combat_state["log"] = (combat_state.get("log", []) + combat_log)[-8:]
    state.message = combat_log[-1]

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

    if looted_items:
        return f"You recover {gold_found} gold and {', '.join(looted_items)}."
    return f"You recover {gold_found} gold."
