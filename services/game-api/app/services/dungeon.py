from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from ..content import WorldContent
from ..db.dungeons import (
    create_dungeon_instance,
    load_dungeon_floor,
    load_dungeon_floor_for_instance,
    persist_dungeon_floor,
)
from ..game import RunState
from ..procgen.generator import generate_floor

logger = logging.getLogger(__name__)


def hydrate_dungeon_location(
    location_id: str, world: WorldContent,
) -> dict[str, Any] | None:
    """Load a dungeon floor into the world location cache if not already present."""
    if location_id in world.locations:
        return world.locations[location_id]
    floor = load_dungeon_floor(location_id)
    if floor is not None:
        world.locations[location_id] = floor
    return floor


def _ensure_dungeon_instance(
    state: RunState, biome_id: str, world: WorldContent,
) -> None:
    """Create a dungeon instance for the run if one doesn't exist."""
    if state.dungeon_instance_id is not None:
        return
    biome = world.dungeon_biomes[biome_id]
    instance = create_dungeon_instance(
        run_id=state.id,
        biome_id=biome_id,
        run_seed=state.run_seed,
        procgen_version=biome["procgen_version"],
    )
    state.dungeon_instance_id = instance.id
    state.procgen_version = instance.procgen_version


def _generate_and_persist_floor(
    state: RunState, biome_id: str, floor_number: int, world: WorldContent,
) -> dict[str, Any]:
    biome = world.dungeon_biomes[biome_id]
    layout = generate_floor(run_seed=state.run_seed, biome=biome, floor_number=floor_number)
    assert state.dungeon_instance_id is not None  # ensured by caller
    persist_dungeon_floor(
        dungeon_instance_id=state.dungeon_instance_id, biome_id=biome_id,
        floor_number=floor_number, floor_seed=layout.floor_seed,
        location_id=layout.location_id, name=layout.name,
        description=layout.description, ascii_map=layout.ascii_map,
        exits=layout.exits, entry_x=layout.entry_x, entry_y=layout.entry_y,
        procgen_features=layout.features, generation=layout.generation,
        validation=layout.validation,
    )
    floor = load_dungeon_floor(layout.location_id)
    if floor is None:
        logger.error("Failed to load generated floor", extra={"biome_id": biome_id, "floor_number": floor_number})
        raise HTTPException(status_code=500, detail="Failed to load generated floor")
    return floor


def ensure_generated_floor(
    state: RunState, biome_id: str, floor_number: int, world: WorldContent,
) -> dict[str, Any]:
    """Ensure a dungeon floor exists, generating and persisting it if necessary."""
    _ensure_dungeon_instance(state, biome_id, world)
    if state.dungeon_instance_id is None:
        raise RuntimeError("dungeon instance ID was not set after creation")
    floor = load_dungeon_floor_for_instance(
        state.dungeon_instance_id, floor_number,
    )
    if floor is None:
        floor = _generate_and_persist_floor(state, biome_id, floor_number, world)
    world.locations[floor["id"]] = floor
    return floor


def handle_transition(state: RunState, exit_node: dict[str, Any]) -> bool:
    if exit_node.get("transition") != "generated_dungeon":
        return False
    biome_id = exit_node["biome_id"]
    try:
        floor_number = int(exit_node.get("floor_number", 1))
    except (ValueError, TypeError):
        floor_number = 1
    from app.main import get_world  # noqa: PLC0415

    world = get_world()
    floor = ensure_generated_floor(state, biome_id=biome_id, floor_number=floor_number, world=world)
    state.location_id = floor["id"]
    state.x = floor["entry_x"]
    state.y = floor["entry_y"]
    state.facing = exit_node.get("target_facing", "N")
    state.floor_number = floor_number
    state.run_depth = max(state.run_depth, floor_number)
    state.message = exit_node["message"]
    return True
