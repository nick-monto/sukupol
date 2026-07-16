"""Database persistence tests.

Asserts that DB CRUD operations behave correctly, use isolated temp DB paths,
and fail on plausible bugs (FK off, idempotency, etc.).
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.content import load_world_content
from app.db.connection import connect, initialize_database, resolve_db_path
from app.db.dungeons import (
    create_dungeon_instance,
    load_dungeon_floor,
    persist_dungeon_floor,
)
from app.db.quests import (
    create_player_quest,
    load_player_quest,
    set_player_quest_status,
)
from app.db.rows import PlayerProgressionRow, QuestRow
from app.db.runs import (
    ensure_player_profile,
    load_run_snapshot,
    save_run_snapshot,
    upsert_player_progression,
)
from app.game import create_run, state_to_dict


def _init_db(db_path: Path) -> None:
    """Initialize a full temp DB with schema + seed data.
    Return value is the WorldContent for test reuse.
    """
    world = load_world_content()
    initialize_database(world, db_path=db_path)
    return world


def test_initialize_database_idempotent() -> None:
    """initialize_database can be called twice without error;
    schema_version row count stays stable."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sukupol.db"
        world = _init_db(db_path)

        with connect(db_path) as conn:
            count_before = conn.execute(
                "SELECT COUNT(*) FROM schema_version"
            ).fetchone()[0]

        # Second call — must not duplicate rows
        initialize_database(world, db_path=db_path)

        with connect(db_path) as conn:
            count_after = conn.execute(
                "SELECT COUNT(*) FROM schema_version"
            ).fetchone()[0]

        assert count_before == count_after, (
            f"schema_version rows changed: {count_before} -> {count_after}"
        )


def test_save_and_load_run_snapshot_roundtrip() -> None:
    """save_run_snapshot then load_run_snapshot returns matching key fields."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sukupol.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)

        exported = state_to_dict(state)
        save_run_snapshot(exported, db_path=db_path)

        loaded = load_run_snapshot(state.id, db_path=db_path)
        assert loaded is not None
        assert loaded["id"] == state.id
        assert loaded["player_name"] == "Wayfarer"
        assert loaded["hp"] == state.hp
        assert loaded["location_id"] == state.location_id


def test_dungeon_floor_roundtrip() -> None:
    """create_dungeon_instance + persist_dungeon_floor + load_dungeon_floor."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sukupol.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)
        save_run_snapshot(state_to_dict(state), db_path=db_path)

        instance = create_dungeon_instance(
            run_id=state.id,
            biome_id="ancient_halls",
            run_seed=state.run_seed,
            procgen_version="1.0",
            db_path=db_path,
        )
        # DungeonInstanceRow has no run_id field — check biome_id instead
        assert instance.biome_id == "ancient_halls"
        assert instance.id is not None

        # Persist a floor
        location_id = "dungeon:test-floor:1"
        persist_dungeon_floor(
            dungeon_instance_id=instance.id,
            biome_id="ancient_halls",
            floor_number=1,
            floor_seed=12345,
            location_id=location_id,
            name="Ancient Halls Test Floor",
            description="A recovered dungeon floor for persistence tests.",
            ascii_map=["#####", "#...#", "#.@.#", "#...#", "#####"],
            exits=[],
            entry_x=2,
            entry_y=2,
            procgen_features=[],
            generation={"profile": "halls"},
            validation={"is_valid": True},
            db_path=db_path,
        )

        # Load the floor back
        loaded = load_dungeon_floor(location_id, db_path=db_path)
        assert loaded is not None
        assert loaded["id"] == location_id
        assert loaded["name"] == "Ancient Halls Test Floor"
        assert loaded["floor_number"] == 1
        assert loaded["encounter_enabled"]
        assert loaded["location_type"] == "dungeon"
        assert loaded["entry_x"] == 2


def test_quest_lifecycle() -> None:
    """create_player_quest → load_player_quest → set_player_quest_status."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sukupol.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)
        save_run_snapshot(state_to_dict(state), db_path=db_path)

        # Create
        quest = create_player_quest(
            player_id=state.player_id,
            template_id="test_template",
            run_id=state.id,
            offered_by_npc_id="marta-innkeeper",
            title="Rat Extermination",
            summary="Clear the cellar of vermin.",
            objective_text="Kill 5 rats",
            objective_kind="kill",
            target_location_id=None,
            target_biome_id=None,
            target_floor_number=None,
            target_count=5,
            progress_value=0,
            progress_target=5,
            status="offered",
            db_path=db_path,
        )
        assert isinstance(quest, QuestRow)
        assert quest.title == "Rat Extermination"
        assert quest.status == "offered"

        # Load
        loaded = load_player_quest(state.player_id, quest.id, db_path=db_path)
        assert loaded is not None
        assert isinstance(loaded, QuestRow)
        # Change status — function takes (quest_id, status, ...), NOT player_id
        set_player_quest_status(quest.id, "active", db_path=db_path)

        # Reload and verify
        after = load_player_quest(state.player_id, quest.id, db_path=db_path)
        assert after is not None
        assert after.status == "active"


def test_quest_fk_enforcement() -> None:
    """Inserting a quest with a bogus run_id raises IntegrityError.

    This fails if PRAGMA foreign_keys is OFF — the test defends the FK
    guarantee set by connect().
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sukupol.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)
        # Intentionally do NOT save a run snapshot — run_sessions row is missing.
        # The quest's FK on run_id → run_sessions(id) will therefore fail.

        with pytest.raises(sqlite3.IntegrityError):
            create_player_quest(
                player_id=state.player_id,
                template_id="test_template",
                run_id=state.id,  # Does not exist in run_sessions
                offered_by_npc_id="marta-innkeeper",
                title="FK Violation",
                summary="Should fail FK check",
                objective_text="None",
                objective_kind="kill",
                target_location_id=None,
                target_biome_id=None,
                target_floor_number=None,
                target_count=1,
                progress_value=0,
                progress_target=1,
                status="offered",
                db_path=db_path,
            )


def test_resolve_db_path_honors_env() -> None:
    """resolve_db_path returns SUKUPOL_DB_PATH when the env var is set."""
    with tempfile.TemporaryDirectory() as tmp:
        custom = Path(tmp) / "custom" / "test.db"
        old = os.environ.get("SUKUPOL_DB_PATH")
        try:
            os.environ["SUKUPOL_DB_PATH"] = str(custom)
            result = resolve_db_path()
            assert result == custom
        finally:
            if old is None:
                del os.environ["SUKUPOL_DB_PATH"]
            else:
                os.environ["SUKUPOL_DB_PATH"] = old
