from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..content import WorldContent
from ..game import RunState, nearby_npcs, resolve_location
from .registry import register_tool_builder


@dataclass(frozen=True)
class NpcDialogueToolContext:
    world: WorldContent
    state: RunState
    npc: dict[str, Any]
    player_memory: dict[str, str]
    shared_knowledge: list[dict[str, Any]]


def build_npc_dialogue_tools(context: NpcDialogueToolContext) -> tuple[Any, ...]:
    def get_player_run_context() -> str:
        """Get the player's exact current run state, location, and nearby NPCs."""
        location = resolve_location(context.world, context.state.location_id)
        payload = {
            "player": {
                "id": context.state.player_id,
                "name": context.state.player_name,
                "hp": context.state.hp,
                "max_hp": context.state.max_hp,
                "gold": context.state.gold,
                "facing": context.state.facing,
                "run_depth": context.state.run_depth,
                "status": context.state.status,
                "in_combat": context.state.in_combat,
            },
            "location": {
                "id": location["id"],
                "name": location["name"],
                "description": location["description"],
                "type": location.get("location_type"),
                "biome_id": location.get("biome_id"),
                "floor_number": location.get("floor_number"),
            },
            "nearby_npcs": [
                {
                    "id": nearby_npc["id"],
                    "display_name": nearby_npc["display_name"],
                    "role": nearby_npc["role"],
                    "distance": nearby_npc["distance"],
                }
                for nearby_npc in nearby_npcs(context.world, context.state)
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    def get_player_inventory() -> str:
        """Get the player's current inventory with exact item names, quantities, and equipped state."""
        payload = {
            "equipped_weapon": context.state.equipped_weapon,
            "inventory": [
                {
                    "item_id": entry["item_id"],
                    "name": context.world.items.get(entry["item_id"], {}).get("name", entry["item_id"]),
                    "item_type": context.world.items.get(entry["item_id"], {}).get("item_type"),
                    "quantity": entry.get("quantity", 1),
                    "equipped": bool(entry.get("equipped", False)),
                    "description": context.world.items.get(entry["item_id"], {}).get("description", ""),
                }
                for entry in context.state.inventory or []
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    def get_conversation_context() -> str:
        """Get the NPC's remembered player summary and current shared knowledge facts."""
        payload = {
            "prior_memory": context.player_memory.get("summary", "") or "none",
            "shared_knowledge": [
                {
                    "category": entry.get("category", "conversation"),
                    "content": entry.get("content", ""),
                }
                for entry in context.shared_knowledge[:8]
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    return (
        get_player_run_context,
        get_player_inventory,
        get_conversation_context,
    )


register_tool_builder("dialogue.reply", build_npc_dialogue_tools)
register_tool_builder("dialogue.stream", build_npc_dialogue_tools)