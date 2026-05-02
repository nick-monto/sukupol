from __future__ import annotations

from typing import Any

from .content import WorldContent
from .game import RunState


def get_inventory_entry(state: RunState, item_id: str) -> dict[str, Any] | None:
    for entry in state.inventory or []:
        if entry["item_id"] == item_id:
            return entry
    return None


def add_item(state: RunState, world: WorldContent, item_id: str, quantity: int = 1) -> None:
    item_def = world.items[item_id]
    inventory = state.inventory or []
    existing = get_inventory_entry(state, item_id)
    if existing and item_def.get("stackable", False):
        existing["quantity"] += quantity
    else:
        inventory.append({"item_id": item_id, "quantity": quantity, "equipped": False})
    state.inventory = inventory


def use_item(state: RunState, world: WorldContent, item_id: str) -> tuple[bool, str]:
    entry = get_inventory_entry(state, item_id)
    if entry is None or entry["quantity"] <= 0:
        return False, "You do not have that item."

    item_def = world.items[item_id]
    healing = int(item_def.get("healing", 0))
    if healing <= 0:
        return False, "That item cannot be used right now."

    state.hp = min(state.max_hp, state.hp + healing)
    entry["quantity"] -= 1
    if entry["quantity"] <= 0:
        state.inventory = [inventory_item for inventory_item in state.inventory or [] if inventory_item["item_id"] != item_id]
    return True, f"You use {item_def['name']} and recover {healing} health."


def get_equipped_weapon(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    if not state.equipped_weapon:
        return None
    return world.items.get(state.equipped_weapon)
