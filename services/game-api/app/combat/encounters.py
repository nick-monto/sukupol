from __future__ import annotations

from typing import Any

from ..content import WorldContent
from ..game import RunState, encounter_context_for_location, resolve_location

from .loot import deterministic_roll
from .state import create_combat_state


ENCOUNTER_RATE_LOW = 1
ENCOUNTER_RATE_HIGH = 100


def _find_encounter(world: WorldContent, encounter_context: dict[str, Any]) -> dict[str, Any] | None:
    biome_id = encounter_context["biome_id"]
    floor_number = int(encounter_context["floor_number"])
    encounter = next(
        (c for c in world.encounters if c["biome_id"] == biome_id and int(c["floor_number"]) == floor_number),
        None,
    )
    if encounter is None and floor_number != 0:
        encounter = next(
            (c for c in world.encounters if c["biome_id"] == biome_id and int(c["floor_number"]) == 0),
            None,
        )
    return encounter


def _pick_enemy(state: RunState, encounter: dict[str, Any]) -> str:
    enemy_ids = encounter["enemy_ids"]
    index = deterministic_roll(
        state.run_seed, state.location_id, state.x, state.y,
        state.steps_taken, "encounter-enemy", low=0, high=len(enemy_ids) - 1,
    )
    return enemy_ids[index]


def _activate_combat(
    world: WorldContent, state: RunState, encounter: dict[str, Any], enemy_id: str,
) -> None:
    enemy = world.enemies[enemy_id]
    msg = encounter.get("message_by_enemy", {}).get(enemy_id)
    if msg is None:
        msg = encounter["message"].format(enemy_name=enemy["name"])
    state.in_combat = True
    state.combat_state = create_combat_state(world, state, enemy_id, msg)
    state.message = msg
    triggered = state.triggered_encounters or []
    triggered.append(f"{state.location_id}:{state.steps_taken}:{enemy_id}")
    state.triggered_encounters = triggered[-24:]


def _roll_encounter_rate(state: RunState, encounter_context: dict[str, Any]) -> bool:
    roll = deterministic_roll(
        state.run_seed, state.location_id, state.x, state.y, state.steps_taken,
        "encounter-rate", low=ENCOUNTER_RATE_LOW, high=ENCOUNTER_RATE_HIGH,
    )
    return roll <= int(encounter_context["encounter_rate"])


def maybe_start_encounter(world: WorldContent, state: RunState, moved: bool = True) -> None:
    if state.in_combat or state.run_result is not None or not moved:
        return
    location = resolve_location(world, state.location_id)
    encounter_context = encounter_context_for_location(world, location)
    if not encounter_context["enabled"]:
        return
    encounter = _find_encounter(world, encounter_context)
    if encounter is None:
        return
    if not _roll_encounter_rate(state, encounter_context):
        return
    enemy_id = _pick_enemy(state, encounter)
    _activate_combat(world, state, encounter, enemy_id)
