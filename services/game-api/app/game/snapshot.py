from __future__ import annotations

from typing import Any

from ..content import WALKABLE_MAP_GLYPHS, WorldContent
from .encounters import encounter_context_for_location
from .overworld import build_overworld_map
from .state import RunState, state_to_dict
from .traversal import resolve_location


def nearby_npcs(world: WorldContent, state: RunState) -> list[dict[str, Any]]:
    npcs: list[dict[str, Any]] = []
    for npc in world.npcs.values():
        if npc["location_id"] != state.location_id:
            continue
        distance = abs(npc["x"] - state.x) + abs(npc["y"] - state.y)
        if distance <= 1:
            npcs.append({
                "id": npc["id"],
                "display_name": npc["display_name"],
                "ascii_art": npc.get("ascii_art", []),
                "role": npc["role"],
                "distance": distance,
            })
    npcs.sort(key=lambda npc: (npc["distance"], npc["display_name"]))
    return npcs


def map_tone_for_glyph(glyph: str) -> str:
    if glyph == "#":
        return "wall"
    if glyph in {"<", "\u222a", "\u2229"}:
        return "exit"
    return "floor"


def _biome_specific_variant(biome_id: str, location_type: str, checksum: int, wall_neighbors: int) -> str | None:
    if biome_id == "whispering_caverns" and checksum % 4 == 0:
        return "wet"
    if biome_id == "ancient_halls" and wall_neighbors >= 2 and checksum % 3 == 0:
        return "rubble"
    if biome_id == "sunken_archive" and (checksum + wall_neighbors) % 3 == 0:
        return "wet"
    if location_type in {"town", "overworld"} and checksum % 6 == 0:
        return "dust"
    if wall_neighbors >= 2 and checksum % 5 == 0:
        return "moss"
    return None


def default_variant_for_feature(kind: str) -> str | None:
    feature_variants = {
        "shrine": "dust",
        "memorial_alcove": "dust",
        "watch_post": "moss",
        "collapse": "rubble",
        "chokepoint": "rubble",
        "flooded_room": "wet",
        "seep": "wet",
        "silt_cache": "dust",
        "archive_nexus": "moss",
        "quiet_room": "dust",
    }
    return feature_variants.get(kind)


def procgen_variant_for_position(location: dict[str, Any], x: int, y: int) -> str | None:
    best_match: tuple[int, str] | None = None
    for feature in location.get("procgen_features", []):
        variant = feature.get("variant") or default_variant_for_feature(feature.get("kind", ""))
        if not variant:
            continue
        radius = max(0, int(feature.get("radius", 0)))
        distance = abs(int(feature.get("x", -99)) - x) + abs(int(feature.get("y", -99)) - y)
        if distance > radius:
            continue
        if best_match is None or distance < best_match[0]:
            best_match = (distance, variant)
    return best_match[1] if best_match is not None else None


def count_adjacent_walls(rows: list[list[str]], x: int, y: int) -> int:
    height = len(rows)
    width = len(rows[0]) if height else 0
    count = 0
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        next_x = x + dx
        next_y = y + dy
        if not (0 <= next_x < width and 0 <= next_y < height):
            continue
        if rows[next_y][next_x] == "#":
            count += 1
    return count


def map_variant_for_position(
    location: dict[str, Any], rows: list[list[str]],
    x: int, y: int, glyph: str,
) -> str | None:
    if glyph not in WALKABLE_MAP_GLYPHS:
        return None
    if glyph in {"<", "\u222a", "\u2229"}:
        return "threshold"
    pv = procgen_variant_for_position(location, x, y)
    if pv is not None:
        return pv
    biome_id, location_type = location.get("biome_id", ""), location.get("location_type", "")
    checksum = sum(ord(c) for c in f"{location['id']}:{biome_id}:{location_type}") + (x * 17) + (y * 31)
    wn = count_adjacent_walls(rows, x, y)
    var = _biome_specific_variant(biome_id, location_type, checksum, wn)
    if var:
        return var
    if wn >= 1 and checksum % 4 == 0:
        return "rubble"
    return "plain"


def _build_map_cells(location: dict[str, Any], rows: list[list[str]]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for y, row in enumerate(rows):
        for x, glyph in enumerate(row):
            tone = map_tone_for_glyph(glyph)
            cell = {"x": x, "y": y, "glyph": glyph, "tone": tone}
            variant = map_variant_for_position(location, rows, x, y, glyph)
            if variant is not None:
                cell["variant"] = variant
                if tone == "floor" and variant != "plain":
                    cell["tone"] = "decor"
            cells.append(cell)
    return cells


def _overlay_npcs(rows: list[list[str]], cells: list[dict[str, Any]], world: WorldContent, state: RunState) -> None:
    for npc in world.npcs.values():
        if npc["location_id"] == state.location_id:
            npc_glyph = npc["display_name"][0].upper()
            rows[npc["y"]][npc["x"]] = npc_glyph
            cells.append({"x": npc["x"], "y": npc["y"], "glyph": npc_glyph, "tone": "npc"})


def _overlay_player(rows: list[list[str]], cells: list[dict[str, Any]], state: RunState) -> None:
    glyph = {"N": "^", "E": ">", "S": "v", "W": "<"}[state.facing]
    rows[state.y][state.x] = glyph
    cells.append({"x": state.x, "y": state.y, "glyph": glyph, "tone": "player"})


def render_map_scene(world: WorldContent, state: RunState) -> dict[str, Any]:
    location = resolve_location(world, state.location_id)
    rows = [list(row) for row in location["ascii_map"]]
    cells = _build_map_cells(location, rows)
    _overlay_npcs(rows, cells, world, state)
    _overlay_player(rows, cells, state)
    return {
        "rows": ["".join(row) for row in rows],
        "metadata": {
            "width": len(rows[0]) if rows else 0,
            "height": len(rows),
            "player_x": state.x,
            "player_y": state.y,
            "cells": cells,
        },
    }


def _normalize_combat_snapshot(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    combat_state = state.combat_state
    if state.in_combat and combat_state is not None:
        from ..combat.state import normalize_combat_state as _normalize_combat

        combat_state = _normalize_combat(world, state)
    return combat_state


def _enrich_inventory_entry(world: WorldContent, entry: dict[str, Any]) -> dict[str, Any]:
    item_id = entry.get("item_id", "")
    item = world.items.get(item_id, {})
    return {
        **entry,
        "name": item.get("name", item_id),
        "item_type": item.get("item_type", "unknown"),
        "description": item.get("description", ""),
    }


def _build_snapshot_location(location: dict[str, Any], state: RunState, encounter_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": state.location_id,
        "name": location["name"],
        "description": location["description"],
        "floor_number": location.get("floor_number"),
        "biome_id": location.get("biome_id"),
        "type": encounter_context["location_type"],
        "encounter_enabled": encounter_context["enabled"],
    }


def _build_journal_entries(player_id: str) -> list[dict[str, Any]]:
    from dataclasses import asdict
    from ..db.journal import list_player_npc_journal

    return [asdict(g) for g in list_player_npc_journal(player_id)]


def _build_quest_list(world: WorldContent, state: RunState) -> list[dict[str, Any]]:
    from ..quests import list_serialized_player_quests

    return list_serialized_player_quests(world, state)


def _build_snapshot_base(state: RunState, combat_state: dict[str, Any] | None, inventory: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_id": state.id, "player_name": state.player_name,
        "facing": state.facing, "message": state.message,
        "run_seed": state.run_seed, "equipped_weapon": state.equipped_weapon,
        "in_combat": state.in_combat, "combat_state": combat_state,
        "run_result": state.run_result, "run_depth": state.run_depth,
        "enemies_defeated": state.enemies_defeated,
        "outcome_summary": state.outcome_summary,
        "progression": state.progression,
        "inventory": inventory,
    }


def build_snapshot(world: WorldContent, state: RunState) -> dict[str, Any]:
    combat_state = _normalize_combat_snapshot(world, state)
    location = resolve_location(world, state.location_id)
    map_scene = render_map_scene(world, state)
    encounter_context = encounter_context_for_location(world, location)
    inventory = [_enrich_inventory_entry(world, e) for e in (state.inventory or [])]
    return {
        **_build_snapshot_base(state, combat_state, inventory),
        "location": _build_snapshot_location(location, state, encounter_context),
        "position": {"x": state.x, "y": state.y},
        "stats": {"hp": state.hp, "max_hp": state.max_hp, "gold": state.gold},
        "map_view": map_scene["rows"],
        "map_metadata": map_scene["metadata"],
        "nearby_npcs": nearby_npcs(world, state),
        "overworld_map": build_overworld_map(world, state),
        "journal": _build_journal_entries(state.player_id),
        "quests": _build_quest_list(world, state),
        "serialized_state": state_to_dict(state),
    }
