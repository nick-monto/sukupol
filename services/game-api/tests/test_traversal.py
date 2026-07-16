"""Traversal tests — perform_action movement, walls, exits, unknown action.

Every test uses real WorldContent + RunState (no DB needed for traversal
itself). Exits and generated-dungeon transitions use in-memory state only.
"""

from __future__ import annotations

from app.content import load_world_content
from app.game import create_run, perform_action

# Player spawns in town_square at (3,5). The ASCII map:
#   0: #########
#   1: #.......#
#   2: #.#...#.#
#   3: #.......#
#   4: #........
#   5: #.......#
#   6: #.......#
#   7: #.#...#.#
#   8: #########
# Exit at (8,4) → outer_fields


def _load_world():
    return load_world_content()


def test_move_north() -> None:
    """move_north advances y by -1."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.y = 5  # explicitly at spawn y
    perform_action(world, state, "move_north")
    assert state.y == 4
    assert "north" in state.message.lower()


def test_move_east() -> None:
    """move_east advances x by +1."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.x = 1
    state.y = 1
    perform_action(world, state, "move_east")
    assert state.x == 2
    assert "east" in state.message.lower()


def test_move_south() -> None:
    """move_south advances y by +1."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.y = 1
    state.x = 1
    perform_action(world, state, "move_south")
    assert state.y == 2
    assert "south" in state.message.lower()


def test_move_west() -> None:
    """move_west advances x by -1."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.x = 2
    state.y = 1
    perform_action(world, state, "move_west")
    assert state.x == 1
    assert "west" in state.message.lower()


def test_forward_follows_facing() -> None:
    """forward moves in the direction the player faces."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.facing = "E"
    state.x = 1
    state.y = 1
    perform_action(world, state, "forward")
    assert state.x == 2  # moved east
    assert state.y == 1


def test_backward_reverses_facing() -> None:
    """backward moves opposite to facing."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.facing = "N"
    state.x = 1
    state.y = 2
    perform_action(world, state, "backward")
    assert state.y == 3  # moved south (reverse of N)


def test_turn_left_rotates() -> None:
    """turn_left rotates facing counter-clockwise."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.facing = "N"
    perform_action(world, state, "turn_left")
    assert state.facing == "W"
    assert "pivot" in state.message


def test_turn_right_rotates() -> None:
    """turn_right rotates facing clockwise."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    state.facing = "N"
    perform_action(world, state, "turn_right")
    assert state.facing == "E"
    assert "pivot" in state.message


def test_walkable_vs_wall() -> None:
    """Moving onto a wall tile sets a blocked message."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    # town_square row 2: #.#...#.#
    # Place player at (1,2) which is walkable '.'.
    # Moving east → (2,2) which is '#' (wall).
    state.x = 1
    state.y = 2
    perform_action(world, state, "move_east")
    assert "blocks" in state.message.lower() or "Stone" in state.message


def test_exit_transition_changes_location() -> None:
    """Walking onto a regular exit transitions to the target location."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    # town_square exit at (8,4) → outer_fields
    # Place player at (7,4) which is walkable (row 4: #........, index 7 = '.')
    state.y = 4
    state.x = 7
    perform_action(world, state, "move_east")
    assert state.location_id == "outer_fields", (
        f"Expected outer_fields, got {state.location_id}"
    )
    assert "outer fields" in state.message.lower()


def test_generated_dungeon_transition() -> None:
    """A 'generated_dungeon' exit invokes the transition handler."""
    world = _load_world()
    state = create_run(world, "Wayfarer")

    # Inject a generated_dungeon exit at (2,5) in town_square
    loc = world.locations[state.location_id]
    exits = list(loc.get("exits", []))
    exits.append({
        "x": 2,
        "y": 5,
        "transition": "generated_dungeon",
        "target_location_id": "dungeon:entrance",
        "target_x": 1,
        "target_y": 1,
        "target_facing": "S",
        "message": "You descend into the dark.",
    })
    loc["exits"] = exits

    # Place player at (1,5), moving east hits the exit at (2,5)
    state.x = 1
    state.y = 5

    handler_called = False

    def fake_handler(_state, exit_node):
        nonlocal handler_called
        handler_called = True
        _state.location_id = exit_node["target_location_id"]
        _state.x = exit_node["target_x"]
        _state.y = exit_node["target_y"]
        _state.facing = exit_node.get("target_facing", _state.facing)
        _state.message = exit_node["message"]
        return True

    perform_action(world, state, "move_east", transition_handler=fake_handler)

    assert handler_called, "transition_handler was not invoked"
    assert state.location_id == "dungeon:entrance"
    assert "descend" in state.message.lower()


def test_generated_dungeon_no_handler_fallback() -> None:
    """Without a handler, generated_dungeon sets a sealed-path message."""
    world = _load_world()
    state = create_run(world, "Wayfarer")

    loc = world.locations[state.location_id]
    exits = list(loc.get("exits", []))
    exits.append({
        "x": 2,
        "y": 5,
        "transition": "generated_dungeon",
        "target_location_id": "dungeon:entrance",
        "target_x": 1,
        "target_y": 1,
        "target_facing": "S",
        "message": "You descend into the dark.",
    })
    loc["exits"] = exits

    state.x = 1
    state.y = 5

    perform_action(world, state, "move_east")  # no transition_handler

    assert "sealed" in state.message.lower(), (
        f"Expected sealed message, got: {state.message}"
    )


def test_unknown_action_fallback() -> None:
    """perform_action with a nonsense action returns state with a message,
    and does NOT raise — this defends the in-sim fallback even though
    the API rejects unknown actions at 422."""
    world = _load_world()
    state = create_run(world, "Wayfarer")
    result = perform_action(world, state, "nonsense")
    assert result is state
    assert "Unknown action" in result.message
