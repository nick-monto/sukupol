from __future__ import annotations

from typing import Any

from ..content import WorldContent
from ..db.rows import QuestRow
from ..game.state import RunState
from ..inventory import get_inventory_entry

from .profiles import (
    QuestProfile,
    _pick,
    _profile_for_template,
    _safe_int,
    _select_profile,
    _template_id,
)
from .profiles_data import SUMMARY_TEMPLATES, TITLE_TEMPLATES


def _parse_template_id(template_id: str) -> dict[str, Any]:
    parts = template_id.split("|")
    if len(parts) != 6 or parts[0] != "fetch":
        raise ValueError(f"Unsupported quest template id: {template_id}")
    return {
        "kind": parts[0],
        "npc_id": parts[1],
        "target_biome_id": parts[2],
        "target_floor_number": _safe_int(parts[3]),
        "item_id": parts[4],
        "reward_gold": _safe_int(parts[5]),
    }


def _format_quest_title_summary(
    npc: dict[str, Any], item: dict[str, Any], biome: dict[str, Any], state: Any,
) -> tuple[str, str, str]:
    """Build title, summary, and objective text for a quest."""
    title = _pick(TITLE_TEMPLATES, state.run_seed, npc["id"], item["id"]).format(
        item_name=item["name"],
        npc_name=npc["display_name"],
    )
    summary = _pick(SUMMARY_TEMPLATES, npc["id"], state.run_seed, biome["id"]).format(
        npc_name=npc["display_name"],
        item_name=item["name"],
        biome_name=biome["name"],
    )
    objective_text = f"Recover the {item['name']} in {biome['name']} and bring it back to {npc['display_name']}."
    return title, summary, objective_text


def _build_quest_payload_dict(
    profile: QuestProfile, npc: dict[str, Any],
    item: dict[str, Any], title: str, summary: str, objective_text: str,
) -> dict[str, Any]:
    return {
        "template_id": _template_id(npc["id"], profile), "title": title,
        "summary": summary, "objective_text": objective_text,
        "objective_kind": "fetch", "target_location_id": None,
        "target_biome_id": profile.target_biome_id,
        "target_floor_number": profile.target_floor_number,
        "target_count": 1, "progress_value": 0, "progress_target": 1,
        "status": "offered", "item_id": item["id"],
        "item_name": item["name"], "reward_gold": profile.reward_gold,
        "hint": profile.hint, "offer_templates": profile.offer_templates,
        "accept_templates": profile.accept_templates,
        "complete_templates": profile.complete_templates,
    }


def _quest_payload(
    world: Any, npc: dict[str, Any], state: Any, player_message: str,
) -> dict[str, Any] | None:
    profile = _select_profile(world, npc, state, player_message)
    if profile is None:
        return None
    biome = world.dungeon_biomes[profile.target_biome_id]
    item = world.items[profile.item_id]
    title, summary, objective_text = _format_quest_title_summary(npc, item, biome, state)
    return _build_quest_payload_dict(profile, npc, item, title, summary, objective_text)


def list_serialized_player_quests(world: WorldContent, state: RunState) -> list[dict[str, Any]]:
    from ..db.quests import list_player_quests  # noqa: PLC0415

    rows = list_player_quests(state.player_id)
    payload = [_serialize_quest_row(world, state, row) for row in rows]
    status_rank = {"offered": 0, "active": 1, "completed": 2, "declined": 3}
    payload.sort(key=lambda quest: (status_rank.get(quest["status"], 9), -(quest["updated_sort"])))
    for quest in payload:
        quest.pop("updated_sort", None)
    return payload


def _resolve_quest_objective(
    row: QuestRow, item: dict[str, Any], npc: dict[str, Any],
    biome: dict[str, Any] | None, has_item: bool,
) -> str:
    """Determine the objective text based on quest status."""
    if row.status == "offered":
        return row.objective_text or f"Accept {npc['display_name']}'s request to recover the {item['name']}."
    elif row.status == "active" and has_item:
        return f"Return the {item['name']} to {npc['display_name']}."
    elif row.status == "active":
        biome_name = biome["name"] if biome else "the dungeon"
        return f"Recover the {item['name']} in {biome_name} and bring it back to {npc['display_name']}."
    elif row.status == "completed" and row.completion_summary:
        return str(row.completion_summary)
    return row.objective_text


def _iso_sort_key(value: str) -> int:
    digits = "".join(c for c in value if c.isdigit())
    return _safe_int(digits, 0)


def _serialize_quest_row(world: Any, state: Any, row: QuestRow) -> dict[str, Any]:
    template = _parse_template_id(row.template_id)
    item = world.items.get(template["item_id"], {"name": template["item_id"]})
    npc = world.npcs.get(row.offered_by_npc_id, {"display_name": row.offered_by_npc_id})
    profile = _profile_for_template(row.offered_by_npc_id, template["item_id"])
    biome = (
        world.dungeon_biomes.get(row.target_biome_id, {"name": row.target_biome_id})
        if row.target_biome_id else None
    )
    has_item = get_inventory_entry(state, template["item_id"]) is not None
    progress_value = 1 if has_item and row.status == "active" else _safe_int(row.progress_value, 0)
    objective_text = _resolve_quest_objective(row, item, npc, biome, has_item)
    updated_sort = _iso_sort_key(row.updated_at or row.offered_at or "")
    return {
        "id": row.id,
        "title": row.title,
        "summary": row.summary,
        "objective_text": objective_text,
        "objective_kind": row.objective_kind,
        "status": row.status,
        "offered_by_npc_id": row.offered_by_npc_id,
        "offered_by_npc_name": npc["display_name"],
        "target_biome_id": row.target_biome_id,
        "target_biome_name": biome["name"] if biome else None,
        "target_floor_number": row.target_floor_number,
        "target_count": _safe_int(row.target_count, 1),
        "progress_value": progress_value,
        "progress_target": _safe_int(row.progress_target, 1),
        "target_item_id": template["item_id"],
        "target_item_name": item["name"],
        "reward_gold": template["reward_gold"],
        "completion_summary": row.completion_summary,
        "can_turn_in": row.status == "active" and has_item,
        "hint": profile.hint if profile else "",
        "offered_at": row.offered_at,
        "accepted_at": row.accepted_at,
        "completed_at": row.completed_at,
        "declined_at": row.declined_at,
        "updated_at": row.updated_at,
        "updated_sort": updated_sort,
    }
