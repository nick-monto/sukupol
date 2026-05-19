from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..content import WorldContent
from ..game import RunState, resolve_location
from .registry import register_tool_builder


@dataclass(frozen=True)
class CombatParleyToolContext:
    world: WorldContent
    state: RunState
    combat_state: dict[str, Any]
    enemy_def: dict[str, Any]
    negotiation: dict[str, Any]


def build_combat_parley_tools(context: CombatParleyToolContext) -> tuple[Any, ...]:
    def get_negotiation_context() -> str:
        """Get the exact active combat and negotiation context for the current parley."""
        location = resolve_location(context.world, context.state.location_id)
        payload = {
            "player": {
                "name": context.state.player_name,
                "hp": context.state.hp,
                "max_hp": context.state.max_hp,
                "gold": context.state.gold,
                "status": context.state.status,
            },
            "location": {
                "id": location["id"],
                "name": location["name"],
                "description": location["description"],
            },
            "enemy": {
                "id": context.enemy_def["id"],
                "name": context.enemy_def["name"],
                "description": context.enemy_def.get("description", ""),
                "communication_mode": context.negotiation.get("communication_mode"),
                "temperament": context.negotiation.get("temperament"),
            },
            "negotiation": {
                "attempts": context.negotiation.get("attempts", 0),
                "anger": context.negotiation.get("anger", 0),
                "anger_limit": context.negotiation.get("anger_limit", 0),
                "leverage": context.negotiation.get("leverage", 0),
                "active_intent": context.negotiation.get("active_intent"),
                "outcome": context.negotiation.get("outcome"),
                "locked": context.negotiation.get("locked", False),
                "available": context.negotiation.get("available", False),
                "transcript": context.negotiation.get("transcript", []),
            },
        }
        return json.dumps(payload, ensure_ascii=True)

    return (get_negotiation_context,)


register_tool_builder("combat.parley_open", build_combat_parley_tools)
register_tool_builder("combat.parley_reply", build_combat_parley_tools)