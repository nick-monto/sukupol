"""Inventory and progression tests.

Asserts add/inventory/equipped-weapon accessors and upsert_player_progression
totals across result types.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.content import load_world_content
from app.db.rows import PlayerProgressionRow
from app.db.runs import ensure_player_profile, upsert_player_progression
from app.game import create_run
from app.inventory import add_item, get_equipped_weapon, get_inventory_entry


def _init_db(db_path: Path):
    """Initialize a temp DB and return the world content."""
    world = load_world_content()
    from app.db.connection import initialize_database

    initialize_database(world, db_path=db_path)
    return world


# ── Inventory ──


def test_add_item_creates_entry() -> None:
    """add_item creates a new inventory entry for a fresh item."""
    world = load_world_content()
    state = create_run(world, "Wayfarer")
    assert "brine_balm" in world.items

    add_item(state, world, "brine_balm", quantity=3)
    entry = get_inventory_entry(state, "brine_balm")
    assert entry is not None
    assert entry["quantity"] == 3


def test_add_item_stacks() -> None:
    """add_item stacks quantity for stackable items already present.
    The starting inventory has health_potion × 2, so adding 2 + 3
    yields 2 + 2 + 3 = 7."""
    world = load_world_content()
    state = create_run(world, "Wayfarer")
    # health_potion IS stackable; starting qty = 2
    add_item(state, world, "health_potion", quantity=2)
    add_item(state, world, "health_potion", quantity=3)
    entry = get_inventory_entry(state, "health_potion")
    assert entry is not None
    # Starting 2 + added 2 + added 3 = 7
    assert entry["quantity"] == 7


def test_get_equipped_weapon_returns_item_dict() -> None:
    """get_equipped_weapon returns the weapon definition dict for the
    equipped item, or None if nothing is equipped."""
    world = load_world_content()
    state = create_run(world, "Wayfarer")
    # Starting inventory has shortsword equipped
    equipped = get_equipped_weapon(world, state)
    assert equipped is not None
    assert equipped["id"] == "shortsword"
    assert "damage" in equipped


def test_get_equipped_weapon_none_when_no_weapon() -> None:
    """get_equipped_weapon returns None when no weapon is equipped."""
    world = load_world_content()
    state = create_run(world, "Wayfarer")
    state.equipped_weapon = None
    result = get_equipped_weapon(world, state)
    assert result is None


# ── Progression ──


def test_upsert_player_progression_victory_first() -> None:
    """First run with 'extraction' result sets total_runs=1, victories=1."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "prog.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)

        row = upsert_player_progression(
            player_id=state.player_id,
            result="extraction",
            depth_reached=5,
            db_path=db_path,
        )
        assert isinstance(row, PlayerProgressionRow)
        assert row.total_runs == 1
        assert row.total_victories == 1
        assert row.deepest_depth == 5
        assert row.last_outcome == "extraction"


def test_upsert_player_progression_death_after_victory() -> None:
    """Second run with death increments total_runs but not victories."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "prog.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)

        upsert_player_progression(
            player_id=state.player_id,
            result="extraction",
            depth_reached=5,
            db_path=db_path,
        )
        row2 = upsert_player_progression(
            player_id=state.player_id,
            result="death",
            depth_reached=2,
            db_path=db_path,
        )
        assert row2.total_runs == 2
        assert row2.total_victories == 1  # Unchanged from first run
        assert row2.deepest_depth == 5  # Max of 5 and 2
        assert row2.last_outcome == "death"


def test_upsert_player_progression_deepest_depth() -> None:
    """Deepest_depth tracks the maximum depth reached across runs."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "prog.db"
        world = _init_db(db_path)
        state = create_run(world, "Wayfarer")
        ensure_player_profile(state.player_id, state.player_name, db_path=db_path)

        upsert_player_progression(
            player_id=state.player_id, result="death",
            depth_reached=3, db_path=db_path,
        )
        row2 = upsert_player_progression(
            player_id=state.player_id, result="extraction",
            depth_reached=10, db_path=db_path,
        )
        assert row2.deepest_depth == 10
