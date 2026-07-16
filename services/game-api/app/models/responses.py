from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    dialogue_mode: str
    dialogue_provider_base_url: str | None = None
    dialogue_provider_model: str | None = None


class BootstrapBiome(BaseModel):
    id: str
    name: str
    procgen_version: str


class BootstrapLocation(BaseModel):
    id: str
    name: str


class BootstrapResponse(BaseModel):
    title: str
    dialogue_mode: str
    dungeon_biomes: list[BootstrapBiome]
    locations: list[BootstrapLocation]


class RunSnapshotLocation(BaseModel):
    id: str
    name: str
    description: str
    floor_number: int | None = None
    biome_id: str | None = None
    type: str
    encounter_enabled: bool


class RunSnapshot(BaseModel):
    """Authoritative snapshot of the current run state.

    Mirrors the fields produced by build_snapshot(). Optional/None fields
    use defaults so the model tolerates states where a field is not yet set.
    """

    run_id: str
    player_name: str
    facing: str
    message: str
    run_seed: int
    equipped_weapon: str | None = None
    in_combat: bool = False
    combat_state: dict[str, Any] | None = None
    run_result: str | None = None
    run_depth: int = 0
    enemies_defeated: int = 0
    outcome_summary: dict[str, Any] | None = None
    progression: dict[str, Any] | None = None
    inventory: list[dict[str, Any]] = []
    location: RunSnapshotLocation
    position: dict[str, int]
    stats: dict[str, int]
    map_view: list[str]
    map_metadata: dict[str, Any]
    nearby_npcs: list[dict[str, Any]]
    overworld_map: dict[str, Any] | None = None
    journal: list[dict[str, Any]]
    quests: list[dict[str, Any]]
    serialized_state: dict[str, Any]
    dialogue: dict[str, str] | None = None
