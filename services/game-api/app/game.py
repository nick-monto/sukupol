from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from .content import WALKABLE_MAP_GLYPHS, WorldContent
from .db import list_player_npc_journal
from .quests import list_serialized_player_quests


FACING_ORDER = ("N", "E", "S", "W")
FACING_DELTAS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}


TransitionHandler = Callable[["RunState", dict[str, Any]], bool]


ConnectionPair = list[str]


@dataclass
class RunState:
    id: str
    player_id: str
    player_name: str
    location_id: str
    x: int
    y: int
    facing: str
    hp: int
    max_hp: int
    gold: int
    status: str
    message: str
    created_at: str
    run_seed: int
    steps_taken: int = 0
    dungeon_instance_id: str | None = None
    floor_number: int | None = None
    procgen_version: str | None = None
    inventory: list[dict[str, Any]] | None = None
    equipped_weapon: str | None = None
    in_combat: bool = False
    combat_state: dict[str, Any] | None = None
    run_result: str | None = None
    run_depth: int = 0
    enemies_defeated: int = 0
    triggered_encounters: list[str] | None = None
    outcome_summary: dict[str, Any] | None = None
    progression: dict[str, Any] | None = None
    active_dialogue_visits: dict[str, dict[str, Any]] | None = None
    party_allies: list[dict[str, Any]] | None = None
    discovered_overworld_locations: list[str] | None = None
    discovered_overworld_connections: list[ConnectionPair] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run(world: WorldContent, player_name: str) -> RunState:
    player_id = str(uuid4())
    run_id = str(uuid4())
    run_seed = int(uuid4().hex[:12], 16)
    spawn = world.player_spawn
    starting_inventory = [dict(item) for item in world.starting_inventory]
    equipped_weapon = next((item["item_id"] for item in starting_inventory if item.get("equipped")), None)
    discovered_locations = [spawn["location_id"]] if is_overworld_mapped_location(world, spawn["location_id"]) else []
    return RunState(
        id=run_id,
        player_id=player_id,
        player_name=player_name,
        location_id=spawn["location_id"],
        x=spawn["x"],
        y=spawn["y"],
        facing=spawn.get("facing", "N"),
        hp=12,
        max_hp=12,
        gold=4,
        status="active",
        message="You arrive in Sukupol and steady yourself before the first descent.",
        created_at=utc_now(),
        run_seed=run_seed,
        steps_taken=0,
        inventory=starting_inventory,
        equipped_weapon=equipped_weapon,
        triggered_encounters=[],
        discovered_overworld_locations=discovered_locations,
        discovered_overworld_connections=[],
    )


def state_to_dict(state: RunState) -> dict[str, Any]:
    return asdict(state)


def state_from_dict(payload: dict[str, Any]) -> RunState:
    discovered_locations = normalize_overworld_locations(payload.get("discovered_overworld_locations", []))
    discovered_connections = normalize_overworld_connections(payload.get("discovered_overworld_connections", []))
    return RunState(
        id=payload["id"],
        player_id=payload["player_id"],
        player_name=payload["player_name"],
        location_id=payload["location_id"],
        x=payload["x"],
        y=payload["y"],
        facing=payload["facing"],
        hp=payload["hp"],
        max_hp=payload["max_hp"],
        gold=payload["gold"],
        status=payload["status"],
        message=payload["message"],
        created_at=payload["created_at"],
        run_seed=payload.get("run_seed", 0),
        steps_taken=payload.get("steps_taken", 0),
        dungeon_instance_id=payload.get("dungeon_instance_id"),
        floor_number=payload.get("floor_number"),
        procgen_version=payload.get("procgen_version"),
        inventory=payload.get("inventory", []),
        equipped_weapon=payload.get("equipped_weapon"),
        in_combat=payload.get("in_combat", False),
        combat_state=payload.get("combat_state"),
        run_result=payload.get("run_result"),
        run_depth=payload.get("run_depth", 0),
        enemies_defeated=payload.get("enemies_defeated", 0),
        triggered_encounters=payload.get("triggered_encounters", []),
        outcome_summary=payload.get("outcome_summary"),
        progression=payload.get("progression"),
        active_dialogue_visits=payload.get("active_dialogue_visits", {}),
        party_allies=payload.get("party_allies", []),
        discovered_overworld_locations=discovered_locations,
        discovered_overworld_connections=discovered_connections,
    )


def overworld_map_data(location: dict[str, Any]) -> dict[str, int] | None:
    raw = location.get("overworld_map")
    if not isinstance(raw, dict):
        return None

    x = raw.get("x")
    y = raw.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return None

    return {"x": x, "y": y}


def is_overworld_mapped_location(world: WorldContent, location_id: str) -> bool:
    location = world.locations.get(location_id)
    if location is None:
        return False
    return overworld_map_data(location) is not None


def normalize_connection_pair(location_a: Any, location_b: Any) -> ConnectionPair | None:
    if not isinstance(location_a, str) or not isinstance(location_b, str):
        return None

    first = location_a.strip()
    second = location_b.strip()
    if not first or not second or first == second:
        return None

    return sorted((first, second))


def normalize_overworld_locations(raw_locations: Any) -> list[str]:
    if not isinstance(raw_locations, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for location_id in raw_locations:
        if not isinstance(location_id, str):
            continue
        candidate = location_id.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def normalize_overworld_connections(raw_connections: Any) -> list[ConnectionPair]:
    if not isinstance(raw_connections, list):
        return []

    normalized: list[ConnectionPair] = []
    seen: set[tuple[str, str]] = set()
    for candidate in raw_connections:
        if not isinstance(candidate, (list, tuple)) or len(candidate) != 2:
            continue
        pair = normalize_connection_pair(candidate[0], candidate[1])
        if pair is None:
            continue
        pair_key = (pair[0], pair[1])
        if pair_key in seen:
            continue
        seen.add(pair_key)
        normalized.append(pair)
    return normalized


def reveal_overworld_location(world: WorldContent, state: RunState, location_id: str) -> None:
    if not is_overworld_mapped_location(world, location_id):
        return

    locations = normalize_overworld_locations(state.discovered_overworld_locations or [])
    if location_id not in locations:
        locations.append(location_id)
    state.discovered_overworld_locations = locations


def reveal_overworld_connection(world: WorldContent, state: RunState, location_a: str, location_b: str) -> None:
    if not is_overworld_mapped_location(world, location_a) or not is_overworld_mapped_location(world, location_b):
        return

    pair = normalize_connection_pair(location_a, location_b)
    if pair is None:
        return

    reveal_overworld_location(world, state, pair[0])
    reveal_overworld_location(world, state, pair[1])
    connections = normalize_overworld_connections(state.discovered_overworld_connections or [])
    if pair not in connections:
        connections.append(pair)
    state.discovered_overworld_connections = connections


def build_overworld_map(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    nodes: list[dict[str, Any]] = []
    connections_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    discovered_locations = set(normalize_overworld_locations(state.discovered_overworld_locations or []))
    discovered_connections = {
        tuple(pair)
        for pair in normalize_overworld_connections(state.discovered_overworld_connections or [])
    }

    for location in world.locations.values():
        map_position = overworld_map_data(location)
        if map_position is None:
            continue
        nodes.append(
            {
                "id": location["id"],
                "name": location["name"],
                "x": map_position["x"],
                "y": map_position["y"],
                "discovered": location["id"] in discovered_locations,
            }
        )
        for exit_node in location.get("exits", []):
            if exit_node.get("transition"):
                continue
            target_location_id = exit_node.get("target_location_id")
            if not isinstance(target_location_id, str) or not is_overworld_mapped_location(world, target_location_id):
                continue
            pair = normalize_connection_pair(location["id"], target_location_id)
            if pair is None:
                continue
            pair_key = (pair[0], pair[1])
            if pair_key not in connections_by_key:
                connections_by_key[pair_key] = {
                    "location_ids": pair,
                    "discovered": pair_key in discovered_connections,
                }

    if not nodes:
        return None

    nodes.sort(key=lambda node: (node["y"], node["x"], node["id"]))
    connections = sorted(
        connections_by_key.values(),
        key=lambda connection: (connection["location_ids"][0], connection["location_ids"][1]),
    )
    current_location_id = state.location_id if is_overworld_mapped_location(world, state.location_id) else None
    return {
        "current_location_id": current_location_id,
        "nodes": nodes,
        "connections": connections,
    }


def turn_left(facing: str) -> str:
    return FACING_ORDER[(FACING_ORDER.index(facing) - 1) % len(FACING_ORDER)]


def turn_right(facing: str) -> str:
    return FACING_ORDER[(FACING_ORDER.index(facing) + 1) % len(FACING_ORDER)]


def tile_at(world: WorldContent, location_id: str, x: int, y: int) -> str:
    location = resolve_location(world, location_id)
    rows = location["ascii_map"]
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[0]):
        return "#"
    return rows[y][x]


def resolve_location(world: WorldContent, location_id: str) -> dict[str, Any]:
    try:
        return world.locations[location_id]
    except KeyError as error:
        raise KeyError(f"Unknown location: {location_id}") from error


def is_walkable(tile: str) -> bool:
    return tile in WALKABLE_MAP_GLYPHS


def direction_for_delta(dx: int, dy: int) -> str:
    for facing, delta in FACING_DELTAS.items():
        if delta == (dx, dy):
            return facing
    return "N"


def encounter_context_for_location(world: WorldContent, location: dict[str, Any]) -> dict[str, Any]:
    biome_id = location.get("encounter_biome_id") or location.get("biome_id")
    biome = world.dungeon_biomes.get(biome_id) if biome_id else None
    location_type = str(location.get("location_type", "site")).strip().lower() or "site"
    explicit_enabled = location.get("encounter_enabled")
    enabled = bool(explicit_enabled) if explicit_enabled is not None else location_type not in {"town", "city"}
    floor_number = int(location.get("encounter_floor", location.get("floor_number", 0) or 0))
    encounter_rate = int(location.get("encounter_rate", biome.get("encounter_rate", 0) if biome else 0))
    return {
        "enabled": enabled and biome_id is not None and encounter_rate > 0,
        "biome_id": biome_id,
        "floor_number": floor_number,
        "encounter_rate": encounter_rate,
        "location_type": location_type,
    }


def action_delta(facing: str, reverse: bool = False) -> tuple[int, int]:
    dx, dy = FACING_DELTAS[facing]
    return (-dx, -dy) if reverse else (dx, dy)


def try_move_delta(
    world: WorldContent,
    state: RunState,
    dx: int,
    dy: int,
    message: str,
    transition_handler: TransitionHandler | None = None,
) -> RunState:
    next_x = state.x + dx
    next_y = state.y + dy
    tile = tile_at(world, state.location_id, next_x, next_y)
    if not is_walkable(tile):
        state.message = "Stone blocks your path."
        return state

    state.x = next_x
    state.y = next_y
    state.facing = direction_for_delta(dx, dy)
    state.steps_taken += 1
    state.message = message
    apply_exit(world, state, transition_handler=transition_handler)
    return state


def try_move(
    world: WorldContent,
    state: RunState,
    reverse: bool = False,
    transition_handler: TransitionHandler | None = None,
) -> RunState:
    dx, dy = action_delta(state.facing, reverse=reverse)
    return try_move_delta(
        world,
        state,
        dx,
        dy,
        "You advance with measured steps." if not reverse else "You fall back and keep your stance.",
        transition_handler=transition_handler,
    )


def apply_exit(
    world: WorldContent,
    state: RunState,
    transition_handler: TransitionHandler | None = None,
) -> None:
    location = resolve_location(world, state.location_id)
    previous_location_id = state.location_id
    for exit_node in location.get("exits", []):
        if exit_node["x"] == state.x and exit_node["y"] == state.y:
            if exit_node.get("transition") == "generated_dungeon":
                if transition_handler is None or not transition_handler(state, exit_node):
                    state.message = "The path below is sealed until the dungeon service responds."
                return
            state.location_id = exit_node["target_location_id"]
            state.x = exit_node["target_x"]
            state.y = exit_node["target_y"]
            state.facing = exit_node.get("target_facing", state.facing)
            if state.location_id in world.locations and "floor_number" in world.locations[state.location_id]:
                state.floor_number = world.locations[state.location_id]["floor_number"]
                state.run_depth = max(state.run_depth, int(state.floor_number or 0))
            elif state.location_id in world.locations:
                state.floor_number = None
            state.message = exit_node["message"]
            reveal_overworld_location(world, state, state.location_id)
            reveal_overworld_connection(world, state, previous_location_id, state.location_id)
            return


def perform_action(
    world: WorldContent,
    state: RunState,
    action: str,
    transition_handler: TransitionHandler | None = None,
) -> RunState:
    if state.run_result is not None:
        state.message = "This run has ended. Start a new run to continue."
        return state
    if state.in_combat:
        state.message = "You cannot move while locked in combat."
        return state
    cardinal_moves = {
        "move_north": (0, -1, "You move north across the map."),
        "move_east": (1, 0, "You move east across the map."),
        "move_south": (0, 1, "You move south across the map."),
        "move_west": (-1, 0, "You move west across the map."),
    }
    if action in cardinal_moves:
        dx, dy, message = cardinal_moves[action]
        return try_move_delta(world, state, dx, dy, message, transition_handler=transition_handler)
    if action == "forward":
        return try_move(world, state, transition_handler=transition_handler)
    if action == "backward":
        return try_move(world, state, reverse=True, transition_handler=transition_handler)
    if action == "turn_left":
        state.facing = turn_left(state.facing)
        state.message = "You pivot left."
        return state
    if action == "turn_right":
        state.facing = turn_right(state.facing)
        state.message = "You pivot right."
        return state

    state.message = f"Unknown action: {action}"
    return state


def nearby_npcs(world: WorldContent, state: RunState) -> list[dict[str, Any]]:
    npcs: list[dict[str, Any]] = []
    for npc in world.npcs.values():
        if npc["location_id"] != state.location_id:
            continue
        distance = abs(npc["x"] - state.x) + abs(npc["y"] - state.y)
        if distance <= 1:
            npcs.append(
                {
                    "id": npc["id"],
                    "display_name": npc["display_name"],
                    "ascii_art": npc.get("ascii_art", []),
                    "role": npc["role"],
                    "distance": distance,
                }
            )
    npcs.sort(key=lambda npc: (npc["distance"], npc["display_name"]))
    return npcs


def render_map_scene(world: WorldContent, state: RunState) -> dict[str, Any]:
    location = resolve_location(world, state.location_id)
    rows = [list(row) for row in location["ascii_map"]]
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

    for npc in world.npcs.values():
        if npc["location_id"] == state.location_id:
            rows[npc["y"]][npc["x"]] = npc["display_name"][0].upper()
            cells.append(
                {
                    "x": npc["x"],
                    "y": npc["y"],
                    "glyph": npc["display_name"][0].upper(),
                    "tone": "npc",
                }
            )

    rows[state.y][state.x] = {"N": "^", "E": ">", "S": "v", "W": "<"}[state.facing]
    cells.append(
        {
            "x": state.x,
            "y": state.y,
            "glyph": {"N": "^", "E": ">", "S": "v", "W": "<"}[state.facing],
            "tone": "player",
        }
    )
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


def map_tone_for_glyph(glyph: str) -> str:
    if glyph == "#":
        return "wall"
    if glyph in {"<", "∪", "∩"}:
        return "exit"
    return "floor"


def map_variant_for_position(
    location: dict[str, Any],
    rows: list[list[str]],
    x: int,
    y: int,
    glyph: str,
) -> str | None:
    if glyph not in WALKABLE_MAP_GLYPHS:
        return None
    if glyph in {"<", "∪", "∩"}:
        return "threshold"

    procgen_variant = procgen_variant_for_position(location, x, y)
    if procgen_variant is not None:
        return procgen_variant

    biome_id = location.get("biome_id", "")
    location_type = location.get("location_type", "")
    checksum = sum(ord(character) for character in f"{location['id']}:{biome_id}:{location_type}") + (x * 17) + (y * 31)
    wall_neighbors = count_adjacent_walls(rows, x, y)

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
    if wall_neighbors >= 1 and checksum % 4 == 0:
        return "rubble"
    return "plain"


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


def build_snapshot(world: WorldContent, state: RunState) -> dict[str, Any]:
    combat_state = state.combat_state
    if state.in_combat and combat_state is not None:
        from .combat import normalize_combat_state

        combat_state = normalize_combat_state(world, state)

    location = resolve_location(world, state.location_id)
    map_scene = render_map_scene(world, state)
    encounter_context = encounter_context_for_location(world, location)
    return {
        "run_id": state.id,
        "player_name": state.player_name,
        "location": {
            "id": state.location_id,
            "name": location["name"],
            "description": location["description"],
            "floor_number": location.get("floor_number"),
            "biome_id": location.get("biome_id"),
            "type": encounter_context["location_type"],
            "encounter_enabled": encounter_context["enabled"],
        },
        "position": {
            "x": state.x,
            "y": state.y,
        },
        "stats": {
            "hp": state.hp,
            "max_hp": state.max_hp,
            "gold": state.gold,
        },
        "facing": state.facing,
        "message": state.message,
        "map_view": map_scene["rows"],
        "map_metadata": map_scene["metadata"],
        "nearby_npcs": nearby_npcs(world, state),
        "run_seed": state.run_seed,
        "inventory": [
            {
                **entry,
                "name": world.items.get(entry["item_id"], {}).get("name", entry["item_id"]),
                "item_type": world.items.get(entry["item_id"], {}).get("item_type", "unknown"),
                "description": world.items.get(entry["item_id"], {}).get("description", ""),
            }
            for entry in (state.inventory or [])
        ],
        "equipped_weapon": state.equipped_weapon,
        "in_combat": state.in_combat,
        "combat_state": combat_state,
        "run_result": state.run_result,
        "run_depth": state.run_depth,
        "enemies_defeated": state.enemies_defeated,
        "outcome_summary": state.outcome_summary,
        "progression": state.progression,
        "overworld_map": build_overworld_map(world, state),
        "journal": list_player_npc_journal(state.player_id),
        "quests": list_serialized_player_quests(world, state),
        "serialized_state": state_to_dict(state),
    }
