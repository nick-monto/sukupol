from __future__ import annotations

from typing import Any
import logging

from ..content import WALKABLE_MAP_GLYPHS, WorldContent
from .overworld import reveal_overworld_connection, reveal_overworld_location
from .state import FACING_DELTAS, FACING_ORDER, RunState, TransitionHandler


logger = logging.getLogger(__name__)


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


def action_delta(facing: str, reverse: bool = False) -> tuple[int, int]:
    dx, dy = FACING_DELTAS[facing]
    return (-dx, -dy) if reverse else (dx, dy)


def try_move_delta(
    world: WorldContent, state: RunState,
    dx: int, dy: int, message: str,
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
        world, state, dx, dy,
        "You advance with measured steps." if not reverse else "You fall back and keep your stance.",
        transition_handler=transition_handler,
    )


def _handle_generated_dungeon_exit(
    state: RunState, exit_node: dict[str, Any],
    transition_handler: TransitionHandler | None,
) -> bool:
    if transition_handler is None or not transition_handler(state, exit_node):
        state.message = "The path below is sealed until the dungeon service responds."
        return True
    return False


def _apply_exit_transition(
    world: WorldContent, state: RunState,
    exit_node: dict[str, Any], previous_location_id: str,
) -> None:
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


def apply_exit(
    world: WorldContent, state: RunState,
    transition_handler: TransitionHandler | None = None,
) -> None:
    location = resolve_location(world, state.location_id)
    previous_location_id = state.location_id
    for exit_node in location.get("exits", []):
        if exit_node["x"] == state.x and exit_node["y"] == state.y:
            if exit_node.get("transition") == "generated_dungeon":
                if _handle_generated_dungeon_exit(state, exit_node, transition_handler):
                    return
            _apply_exit_transition(world, state, exit_node, previous_location_id)
            return

_CARDINAL_MOVES: dict[str, tuple[int, int, str]] = {
    "move_north": (0, -1, "You move north across the map."),
    "move_east": (1, 0, "You move east across the map."),
    "move_south": (0, 1, "You move south across the map."),
    "move_west": (-1, 0, "You move west across the map."),
}


def _is_action_blocked(state: RunState) -> bool:
    if state.run_result is not None:
        logger.warning("Action received on ended run %s", state.id)
        state.message = "This run has ended. Start a new run to continue."
        return True
    if state.in_combat:
        state.message = "You cannot move while locked in combat."
        return True
    return False


def _execute_directional_action(
    world: WorldContent, state: RunState, action: str,
    transition_handler: TransitionHandler | None = None,
) -> RunState | None:
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
    return None


def perform_action(
    world: WorldContent, state: RunState, action: str,
    transition_handler: TransitionHandler | None = None,
) -> RunState:
    if _is_action_blocked(state):
        return state
    if action in _CARDINAL_MOVES:
        dx, dy, msg = _CARDINAL_MOVES[action]
        return try_move_delta(world, state, dx, dy, msg, transition_handler=transition_handler)
    result = _execute_directional_action(world, state, action, transition_handler)
    if result is not None:
        return result
    logger.warning("Unknown action reached perform_action fallback: %s", action)
    state.message = f"Unknown action: {action}"
    return state
