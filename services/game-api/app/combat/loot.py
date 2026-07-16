from __future__ import annotations

from typing import Any

from ..content import WorldContent
from ..game import RunState
from ..inventory import add_item, get_equipped_weapon
from ..quests import recover_active_fetch_quest_items


ENCOUNTER_RATE_LOW = 1
ENCOUNTER_RATE_HIGH = 100


def deterministic_roll(run_seed: int, *parts: Any, low: int, high: int) -> int:
    span = high - low + 1
    checksum = run_seed
    for part in parts:
        checksum += sum(ord(character) for character in str(part))
    return low + (checksum % span)


def player_attack_value(world: WorldContent, state: RunState) -> int:
    weapon = get_equipped_weapon(world, state)
    return int(weapon.get("damage", 1)) if weapon else 1


def player_defence_value() -> int:
    return 0


def inventory_quantity(state: RunState, item_id: str) -> int:
    for entry in state.inventory or []:
        if entry.get("item_id") == item_id:
            return int(entry.get("quantity", 0))
    return 0


def _roll_gold(state: RunState, enemy_def: dict[str, Any]) -> int:
    gold_min, gold_max = enemy_def.get("gold_drop", [0, 0])
    gold = deterministic_roll(
        state.run_seed, enemy_def["id"], state.enemies_defeated, "gold",
        low=gold_min, high=gold_max,
    )
    state.gold += gold
    return gold


def _roll_loot_items(world: WorldContent, state: RunState, enemy_def: dict[str, Any]) -> list[str]:
    looted: list[str] = []
    for entry in enemy_def.get("loot_table", []):
        threshold = int(float(entry.get("chance", 0)) * 100)
        roll = deterministic_roll(
            state.run_seed, enemy_def["id"], entry["item_id"],
            state.enemies_defeated, low=ENCOUNTER_RATE_LOW, high=ENCOUNTER_RATE_HIGH,
        )
        if roll <= threshold:
            add_item(state, world, entry["item_id"], int(entry.get("quantity", 1)))
            looted.append(world.items[entry["item_id"]]["name"])

    for recovery in recover_active_fetch_quest_items(world, state):
        looted.append(f"{recovery['item_name']} for {recovery['npc_name']}")
    return looted


def apply_loot(world: WorldContent, state: RunState, enemy_def: dict[str, Any]) -> str:
    gold_found = _roll_gold(state, enemy_def)
    looted_items = _roll_loot_items(world, state, enemy_def)
    if looted_items:
        return f"You recover {gold_found} gold and {', '.join(looted_items)}."
    return f"You recover {gold_found} gold."
