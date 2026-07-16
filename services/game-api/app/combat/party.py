from __future__ import annotations

from typing import Any

from ..content import WorldContent
from ..game import RunState

from .loot import inventory_quantity, player_attack_value, player_defence_value


PARTY_SLOT_COUNT = 3


def _base_combat_actions(state: RunState) -> list[dict[str, Any]]:
    potion_count = inventory_quantity(state, "health_potion")
    return [
        {"id": "attack", "label": "Attack", "kind": "attack", "enabled": True, "item_id": None},
        {"id": "defend", "label": "Defend", "kind": "defend", "enabled": True, "item_id": None},
        {
            "id": "use_item:health_potion",
            "label": f"Use potion{f' ({potion_count})' if potion_count else ''}",
            "kind": "item", "enabled": potion_count > 0, "item_id": "health_potion",
        },
        {"id": "flee", "label": "Flee", "kind": "flee", "enabled": True, "item_id": None},
    ]


def _active_parley_options(negotiation: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for option in negotiation.get("options", []):
        if isinstance(option, dict):
            result.append({
                "id": str(option.get("id", "parley_invalid")),
                "label": str(option.get("label", "Negotiate")),
                "kind": "parley",
                "enabled": bool(option.get("enabled", True)),
                "item_id": None,
            })
    result.append({
        "id": "parley_end", "label": "End communication",
        "kind": "parley", "enabled": True, "item_id": None,
    })
    return result


def _inactive_parley_action(negotiation: dict[str, Any]) -> list[dict[str, Any]]:
    mode = str(negotiation.get("communication_mode", "speech"))
    return [{
        "id": "parley_open", "label": f"Communicate ({mode})",
        "kind": "parley", "enabled": True, "item_id": None,
    }]


def _parley_actions(combat_state: dict[str, Any]) -> list[dict[str, Any]]:
    negotiation = combat_state.get("negotiation") if isinstance(combat_state.get("negotiation"), dict) else None
    if negotiation is None or not negotiation.get("available"):
        return []
    if negotiation.get("active"):
        return _active_parley_options(negotiation)
    return _inactive_parley_action(negotiation)


def build_available_actions(
    world: WorldContent,
    state: RunState,
    combat_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    actions = _base_combat_actions(state)
    if isinstance(combat_state, dict):
        actions.extend(_parley_actions(combat_state))
    return actions


def _build_player_slot(world: WorldContent, state: RunState) -> dict[str, Any]:
    return {
        "slot_id": "party-1", "name": state.player_name, "role": "Vanguard",
        "hp": state.hp, "max_hp": state.max_hp,
        "attack": player_attack_value(world, state), "defence": player_defence_value(),
        "is_player": True, "is_active": True, "reserve": False,
    }


def _build_ally_filled_slot(index: int, ally: dict[str, Any]) -> dict[str, Any]:
    return {
        "slot_id": str(ally.get("slot_id", f"ally-{ally.get('ally_id', index + 2)}")),
        "name": str(ally.get("name", "Bound ally")),
        "role": str(ally.get("role", "Bound ally")),
        "hp": int(ally.get("hp", ally.get("max_hp", 1))),
        "max_hp": int(ally.get("max_hp", 1)),
        "attack": int(ally.get("attack", 1)),
        "defence": int(ally.get("defence", 0)),
        "is_player": False, "is_active": True, "reserve": False,
    }


def _build_ally_empty_slot(index: int, existing_slot: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "slot_id": existing_slot.get("slot_id", f"party-{index + 2}") if isinstance(existing_slot, dict) else f"party-{index + 2}",
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


def _fill_ally_slot(index: int, allies: list[dict[str, Any]], existing_slot: dict[str, Any] | None) -> dict[str, Any]:
    ally = allies[index] if index < len(allies) else None
    if ally is not None:
        return _build_ally_filled_slot(index, ally)
    return _build_ally_empty_slot(index, existing_slot)


def build_party_slots(
    world: WorldContent,
    state: RunState,
    existing_party: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = [_build_player_slot(world, state)]
    allies = active_party_allies(state)
    for index in range(PARTY_SLOT_COUNT - 1):
        existing_slot = existing_party[index + 1] if existing_party and len(existing_party) > (index + 1) else None
        slots.append(_fill_ally_slot(index, allies, existing_slot))
    return slots


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


def party_has_allies_in_combat(combat_state: dict[str, Any]) -> bool:
    party_value = combat_state.get("party")
    party: list[Any] = party_value if isinstance(party_value, list) else []
    return any(
        isinstance(slot, dict) and not slot.get("is_player") and not slot.get("reserve", True)
        for slot in party
    )


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
            **ally, "remaining_battles": remaining_battles,
            "role": f"{refreshed_role} / {remaining_battles} battles",
        })
    state.party_allies = remaining_allies


def grant_recruited_ally(state: RunState, enemy_def: dict[str, Any], battles: int) -> dict[str, Any]:
    ally: dict[str, Any] = {
        "ally_id": enemy_def["id"], "slot_id": f"ally-{enemy_def['id']}",
        "name": enemy_def["name"], "role": f"Bound ally / {battles} battles",
        "hp": int(enemy_def["max_hp"]), "max_hp": int(enemy_def["max_hp"]),
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
