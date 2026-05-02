from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from .content import WorldContent


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
    return tile in {".", ">", "<"}


def action_delta(facing: str, reverse: bool = False) -> tuple[int, int]:
    dx, dy = FACING_DELTAS[facing]
    return (-dx, -dy) if reverse else (dx, dy)


def try_move(
    world: WorldContent,
    state: RunState,
    reverse: bool = False,
    transition_handler: TransitionHandler | None = None,
) -> RunState:
    dx, dy = action_delta(state.facing, reverse=reverse)
    next_x = state.x + dx
    next_y = state.y + dy
    tile = tile_at(world, state.location_id, next_x, next_y)
    if not is_walkable(tile):
        state.message = "Stone blocks your path."
        return state

    state.x = next_x
    state.y = next_y
    state.message = "You advance with measured steps." if not reverse else "You fall back and keep your stance."
    apply_exit(world, state, transition_handler=transition_handler)
    return state


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
                    "role": npc["role"],
                    "distance": distance,
                }
            )
    npcs.sort(key=lambda npc: (npc["distance"], npc["display_name"]))
    return npcs


def render_minimap(world: WorldContent, state: RunState) -> list[str]:
    location = resolve_location(world, state.location_id)
    rows = [list(row) for row in location["ascii_map"]]

    for npc in world.npcs.values():
        if npc["location_id"] == state.location_id:
            rows[npc["y"]][npc["x"]] = npc["display_name"][0].upper()

    rows[state.y][state.x] = {"N": "^", "E": ">", "S": "v", "W": "<"}[state.facing]
    return ["".join(row) for row in rows]


def render_first_person(world: WorldContent, state: RunState) -> list[str]:
    width = 27
    height = 13
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    frames = {
        1: (1, 1, 25, 11),
        2: (5, 3, 21, 9),
        3: (9, 5, 17, 7),
    }

    def set_cell(x: int, y: int, value: str) -> None:
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x] = value

    def draw_box(bounds: tuple[int, int, int, int], edge: str) -> None:
        left, top, right, bottom = bounds
        for x in range(left, right + 1):
            set_cell(x, top, edge)
            set_cell(x, bottom, edge)
        for y in range(top, bottom + 1):
            set_cell(left, y, edge)
            set_cell(right, y, edge)

    def draw_side(depth: int, side: str, edge: str) -> None:
        left, top, right, bottom = frames[depth]
        next_bounds = frames.get(depth + 1)
        if side == "left":
            for y in range(top, bottom + 1):
                set_cell(left, y, edge)
            if next_bounds:
                next_left, next_top, _, next_bottom = next_bounds
                for offset in range(next_top - top + 1):
                    set_cell(left + offset, top + offset, "/")
                    set_cell(left + offset, bottom - offset, "\\")
                for y in range(next_top, next_bottom + 1):
                    set_cell(next_left, y, edge)
        else:
            for y in range(top, bottom + 1):
                set_cell(right, y, edge)
            if next_bounds:
                _, next_top, next_right, next_bottom = next_bounds
                for offset in range(next_top - top + 1):
                    set_cell(right - offset, top + offset, "\\")
                    set_cell(right - offset, bottom - offset, "/")
                for y in range(next_top, next_bottom + 1):
                    set_cell(next_right, y, edge)

    left_facing = turn_left(state.facing)
    right_facing = turn_right(state.facing)
    for depth in range(1, 4):
        dx, dy = FACING_DELTAS[state.facing]
        tile_x = state.x + dx * depth
        tile_y = state.y + dy * depth
        front_tile = tile_at(world, state.location_id, tile_x, tile_y)
        left_dx, left_dy = FACING_DELTAS[left_facing]
        right_dx, right_dy = FACING_DELTAS[right_facing]
        left_tile = tile_at(world, state.location_id, tile_x + left_dx, tile_y + left_dy)
        right_tile = tile_at(world, state.location_id, tile_x + right_dx, tile_y + right_dy)

        if front_tile == "#":
            draw_box(frames[depth], "#")
            break

        draw_side(depth, "left", "|") if left_tile == "#" else None
        draw_side(depth, "right", "|") if right_tile == "#" else None

        if depth == 3:
            set_cell(width // 2, height // 2, ".")

    horizon = height // 2 + 3
    for x in range(width):
        set_cell(x, horizon, "_")
    return ["".join(row).rstrip() for row in canvas]


def build_snapshot(world: WorldContent, state: RunState) -> dict[str, Any]:
    location = resolve_location(world, state.location_id)
    return {
        "run_id": state.id,
        "player_name": state.player_name,
        "location": {
            "id": state.location_id,
            "name": location["name"],
            "description": location["description"],
            "floor_number": location.get("floor_number"),
            "biome_id": location.get("biome_id"),
        },
        "stats": {
            "hp": state.hp,
            "max_hp": state.max_hp,
            "gold": state.gold,
        },
        "facing": state.facing,
        "message": state.message,
        "first_person_view": render_first_person(world, state),
        "minimap": render_minimap(world, state),
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
        "serialized_state": state_to_dict(state),
    }
