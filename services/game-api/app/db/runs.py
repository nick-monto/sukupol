from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

from .connection import connect, utc_now
from .rows import PlayerProgressionRow

logger = logging.getLogger(__name__)


def ensure_player_profile(player_id: str, player_name: str, db_path: Path | None = None) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO player_profiles (id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name,
              updated_at = excluded.updated_at
            """,
            (player_id, player_name, utc_now(), utc_now()),
        )
        connection.commit()


def save_run_snapshot(run_state: dict, db_path: Path | None = None) -> None:
    snapshot_json = json.dumps(run_state, sort_keys=True)
    run_id = run_state.get("id", "<unknown>")
    try:
        with connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO run_sessions (
                  id,
                  player_id,
                  player_name,
                  location_id,
                  player_x,
                  player_y,
                  facing,
                  hp,
                  max_hp,
                  gold,
                  status,
                  snapshot_json,
                  created_at,
                  updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  player_id = excluded.player_id,
                  player_name = excluded.player_name,
                  location_id = excluded.location_id,
                  player_x = excluded.player_x,
                  player_y = excluded.player_y,
                  facing = excluded.facing,
                  hp = excluded.hp,
                  max_hp = excluded.max_hp,
                  gold = excluded.gold,
                  status = excluded.status,
                  snapshot_json = excluded.snapshot_json,
                  updated_at = excluded.updated_at
                """,
                (
                    run_state["id"],
                    run_state["player_id"],
                    run_state["player_name"],
                    run_state["location_id"],
                    run_state["x"],
                    run_state["y"],
                    run_state["facing"],
                    run_state["hp"],
                    run_state["max_hp"],
                    run_state["gold"],
                    run_state["status"],
                    snapshot_json,
                    run_state["created_at"],
                    utc_now(),
                ),
            )
            connection.commit()
    except Exception:
        logger.exception("Failed to save run snapshot for run %s", run_id)
        raise


def load_run_snapshot(run_id: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT snapshot_json FROM run_sessions WHERE id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row["snapshot_json"])


def save_run_outcome(
    run_id: str,
    player_id: str,
    result: str,
    depth_reached: int,
    enemies_defeated: int,
    gold_earned: int,
    items_json: str,
    db_path: Path | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO run_outcomes (id, run_id, player_id, result, depth_reached, enemies_defeated, gold_earned, items_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
              result = excluded.result,
              depth_reached = excluded.depth_reached,
              enemies_defeated = excluded.enemies_defeated,
              gold_earned = excluded.gold_earned,
              items_json = excluded.items_json
            """,
            (
                str(uuid4()),
                run_id,
                player_id,
                result,
                depth_reached,
                enemies_defeated,
                gold_earned,
                items_json,
                utc_now(),
            ),
        )
        connection.commit()


def upsert_player_progression(
    player_id: str,
    result: str,
    depth_reached: int,
    db_path: Path | None = None,
) -> PlayerProgressionRow:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT total_runs, total_victories, deepest_depth
            FROM player_progression
            WHERE player_id = ?
            """,
            (player_id,),
        ).fetchone()

        total_runs = (row["total_runs"] if row else 0) + 1
        total_victories = (row["total_victories"] if row else 0) + (1 if result == "extraction" else 0)
        deepest_depth = max(row["deepest_depth"] if row else 0, depth_reached)

        connection.execute(
            """
            INSERT INTO player_progression (player_id, total_runs, total_victories, deepest_depth, last_outcome, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
              total_runs = excluded.total_runs,
              total_victories = excluded.total_victories,
              deepest_depth = excluded.deepest_depth,
              last_outcome = excluded.last_outcome,
              updated_at = excluded.updated_at
            """,
            (player_id, total_runs, total_victories, deepest_depth, result, utc_now()),
        )
        connection.commit()

    return PlayerProgressionRow(
        total_runs=total_runs,
        total_victories=total_victories,
        deepest_depth=deepest_depth,
        last_outcome=result,
    )
