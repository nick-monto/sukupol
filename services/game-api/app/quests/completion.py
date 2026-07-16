from __future__ import annotations

from typing import Any

from ..agents.quest_agents import QuestResponseContext
from ..agents.quest_generation import QuestGenerationService
from ..content import WorldContent
from ..db.quests import (
    list_player_quests,
    load_player_quest,
    set_player_quest_progress,
    set_player_quest_status,
)
from ..db.rows import QuestRow
from ..game.state import RunState
from ..inventory import add_item, get_inventory_entry, remove_item
from .profiles import _item_label, _pick, _profile_for_template, _safe_int
from .profiles_data import COMPLETE_TEMPLATES
from .template import _iso_sort_key, _parse_template_id, _serialize_quest_row


def _format_completion_response(
    serialized: dict[str, Any], row: QuestRow,
    template: dict[str, Any], npc: dict[str, Any],
    reward_gold: int, item_name: str, state: Any,
    quest_generation_service: QuestGenerationService | None,
) -> str:
    """Generate the NPC's response to quest completion."""
    profile = _profile_for_template(row.offered_by_npc_id, template["item_id"])
    templates = profile.complete_templates if profile and profile.complete_templates else COMPLETE_TEMPLATES
    fallback_text = _pick(templates, state.run_seed, row.id).format(
        item_name=item_name,
        item_label=_item_label(item_name),
        npc_name=npc["display_name"],
        biome_name=serialized.get("target_biome_name") or template["target_biome_id"],
        reward_gold=reward_gold,
    )
    if quest_generation_service is None:
        return fallback_text
    generated_text = quest_generation_service.generate_response(
        QuestResponseContext(
            npc_name=npc["display_name"],
            biome_name=serialized.get("target_biome_name") or template["target_biome_id"],
            item_name=item_name,
            reward_gold=reward_gold,
            hint=serialized.get("hint", ""),
            stance="complete",
        )
    )
    return generated_text or fallback_text


def _complete_quest(
    world: Any, state: Any, row: QuestRow,
    template: dict[str, Any],
    quest_generation_service: QuestGenerationService | None,
) -> dict[str, Any]:
    """Complete a single quest: award gold, remove item, generate response."""
    npc = world.npcs[row.offered_by_npc_id]
    reward_gold = template["reward_gold"]
    remove_item(state, template["item_id"], quantity=1)
    state.gold += reward_gold
    item_name = world.items.get(template["item_id"], {"name": template["item_id"]})["name"]
    completion_summary = f"Returned the {item_name} to {npc['display_name']} for {reward_gold} gold."
    set_player_quest_progress(quest_id=row.id, progress_value=1, objective_text=completion_summary)
    set_player_quest_status(quest_id=row.id, status="completed", completion_summary=completion_summary)

    refreshed = load_player_quest(state.player_id, row.id)
    if refreshed is None:
        raise ValueError("Quest disappeared during completion")

    serialized = _serialize_quest_row(world, state, refreshed)
    serialized["response_text"] = _format_completion_response(
        serialized, row, template, npc, reward_gold, item_name, state, quest_generation_service,
    )
    return serialized


def maybe_complete_quest_turn_in(
    world: WorldContent,
    state: RunState,
    npc_id: str,
    quest_generation_service: QuestGenerationService | None = None,
) -> dict[str, Any] | None:
    for row in list_player_quests(state.player_id):
        if row.offered_by_npc_id != npc_id or row.status != "active":
            continue
        template = _parse_template_id(row.template_id)
        if get_inventory_entry(state, template["item_id"]) is None:
            continue
        return _complete_quest(world, state, row, template, quest_generation_service)
    return None


def _find_eligible_quests(state: Any, biome_id: str, floor_number: int) -> list[QuestRow]:
    eligible_rows: list[QuestRow] = []
    for row in list_player_quests(state.player_id):
        if row.status != "active" or row.objective_kind != "fetch":
            continue
        template = _parse_template_id(row.template_id)
        if template["target_biome_id"] != biome_id or floor_number < template["target_floor_number"]:
            continue
        if get_inventory_entry(state, template["item_id"]) is not None:
            continue
        eligible_rows.append(row)
    if not eligible_rows:
        return []
    eligible_rows.sort(key=lambda r: (_iso_sort_key(r.accepted_at or r.offered_at or ""), r.id))
    return eligible_rows


def _award_quest_item(state: Any, world: Any, row: QuestRow) -> list[dict[str, Any]]:
    template = _parse_template_id(row.template_id)
    add_item(state, world, template["item_id"], quantity=1)
    item_name = world.items.get(template["item_id"], {"name": template["item_id"]})["name"]
    quest_npc_name = world.npcs.get(row.offered_by_npc_id, {"display_name": row.offered_by_npc_id})["display_name"]
    objective_text = f"Return the {item_name} to {quest_npc_name}."
    set_player_quest_progress(quest_id=row.id, progress_value=1, objective_text=objective_text)
    return [
        {
            "quest_id": row.id,
            "item_id": template["item_id"],
            "item_name": item_name,
            "npc_name": quest_npc_name,
        }
    ]


def recover_active_fetch_quest_items(world: WorldContent, state: RunState) -> list[dict[str, Any]]:
    location = world.locations.get(state.location_id)
    if location is None:
        return []
    biome_id = location.get("biome_id")
    floor_number = _safe_int(location.get("floor_number") or state.floor_number, 0)
    if biome_id is None:
        return []
    eligible = _find_eligible_quests(state, biome_id, floor_number)
    if not eligible:
        return []
    return _award_quest_item(state, world, eligible[0])
