from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from .content import DECORATIVE_FLOOR_GLYPHS, WALKABLE_MAP_GLYPHS, WorldContent
from .db import list_player_npc_journal


FACING_ORDER = ("N", "E", "S", "W")
FACING_DELTAS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}


TransitionHandler = Callable[["RunState", dict[str, Any]], bool]


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_run(world: WorldContent, player_name: str) -> RunState:
    player_id = str(uuid4())
    run_id = str(uuid4())
    run_seed = int(uuid4().hex[:12], 16)
    spawn = world.player_spawn
    starting_inventory = [dict(item) for item in world.starting_inventory]
    equipped_weapon = next((item["item_id"] for item in starting_inventory if item.get("equipped")), None)
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
    )


def state_to_dict(state: RunState) -> dict[str, Any]:
    return asdict(state)


def state_from_dict(payload: dict[str, Any]) -> RunState:
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
    )


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
    enabled = bool(location.get("encounter_enabled", False))
    floor_number = int(location.get("encounter_floor", location.get("floor_number", 0) or 0))
    encounter_rate = int(location.get("encounter_rate", biome.get("encounter_rate", 0) if biome else 0))
    return {
        "enabled": enabled and biome_id is not None and encounter_rate > 0,
        "biome_id": biome_id,
        "floor_number": floor_number,
        "encounter_rate": encounter_rate,
        "location_type": str(location.get("location_type", "site")),
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
            cells.append({"x": x, "y": y, "glyph": glyph, "tone": tone})

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
    if glyph in {">", "<"}:
        return "exit"
    if glyph in DECORATIVE_FLOOR_GLYPHS:
        return "decor"
    return "floor"


def build_snapshot(world: WorldContent, state: RunState) -> dict[str, Any]:
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
        "inventory": state.inventory or [],
        "equipped_weapon": state.equipped_weapon,
        "in_combat": state.in_combat,
        "combat_state": state.combat_state,
        "run_result": state.run_result,
        "run_depth": state.run_depth,
        "enemies_defeated": state.enemies_defeated,
        "outcome_summary": state.outcome_summary,
        "progression": state.progression,
        "journal": list_player_npc_journal(state.player_id),
        "serialized_state": state_to_dict(state),
    }
