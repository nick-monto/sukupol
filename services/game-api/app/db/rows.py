"""Typed DB row dataclasses.

Every table in the schema gets a frozen dataclass so DB-boundary
functions return typed objects instead of raw dicts.

load_run_snapshot is exempted (it round-trips JSON state). Internal
simulation code (game/, combat/) keeps dicts per the user decision.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerProfileRow:
    id: str
    name: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class RunSessionRow:
    id: str
    player_id: str
    player_name: str
    location_id: str
    player_x: int
    player_y: int
    facing: str
    hp: int
    max_hp: int
    gold: int
    status: str
    snapshot_json: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ConversationSummaryRow:
    player_id: str
    npc_instance_id: str
    summary: str
    updated_at: str


@dataclass(frozen=True)
class NpcPlayerMemoryRow:
    summary: str
    last_player_message: str
    last_npc_reply: str
    updated_at: str


@dataclass(frozen=True)
class NpcSharedKnowledgeRow:
    category: str
    content: str
    source: str
    updated_at: str


@dataclass(frozen=True)
class NpcJournalEntryRow:
    id: str
    player_id: str
    npc_id: str  # npc_instance_id aliased to npc_id in SQL
    run_id: str
    turn_count: int
    visit_started_at: str
    visit_ended_at: str
    summary: str
    created_at: str


@dataclass(frozen=True)
class NpcJournalEntryItem:
    id: str
    run_id: str
    turn_count: int
    visit_started_at: str
    visit_ended_at: str
    summary: str
    created_at: str


@dataclass(frozen=True)
class NpcJournalGroup:
    npc_id: str
    npc_name: str
    entries: list[NpcJournalEntryItem]


@dataclass(frozen=True)
class DungeonInstanceRow:
    id: str
    biome_id: str
    run_seed: int
    procgen_version: str
    created_at: str


@dataclass(frozen=True)
class DungeonFloorRow:
    id: str
    dungeon_instance_id: str
    biome_id: str
    floor_number: int
    floor_seed: int
    location_id: str
    name: str
    description: str
    ascii_map_json: str
    exits_json: str
    entry_x: int
    entry_y: int
    procgen_features_json: str
    generation_json: str
    validation_json: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class RunOutcomeRow:
    id: str
    run_id: str
    player_id: str
    result: str
    depth_reached: int
    enemies_defeated: int
    gold_earned: int
    items_json: str
    created_at: str


@dataclass(frozen=True)
class PlayerProgressionRow:
    total_runs: int
    total_victories: int
    deepest_depth: int
    last_outcome: str | None = None


@dataclass(frozen=True)
class QuestRow:
    id: str
    player_id: str
    template_id: str
    run_id: str
    offered_by_npc_id: str
    title: str
    summary: str
    objective_text: str
    objective_kind: str
    status: str
    offered_at: str
    updated_at: str
    target_location_id: str | None = None
    target_biome_id: str | None = None
    target_floor_number: int | None = None
    target_count: int = 0
    progress_value: int = 0
    progress_target: int = 1
    completion_summary: str | None = None
    accepted_at: str | None = None
    completed_at: str | None = None
    declined_at: str | None = None
