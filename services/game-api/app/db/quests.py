from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .connection import connect, utc_now
from .rows import QuestRow



def create_player_quest(
    player_id: str,
    template_id: str,
    run_id: str,
    offered_by_npc_id: str,
    title: str,
    summary: str,
    objective_text: str,
    objective_kind: str,
    target_location_id: str | None,
    target_biome_id: str | None,
    target_floor_number: int | None,
    target_count: int,
    progress_value: int,
    progress_target: int,
    status: str,
    db_path: Path | None = None,
) -> QuestRow:
    quest_id = str(uuid4())
    now = utc_now()
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO player_quests (
              id, player_id, template_id, run_id, offered_by_npc_id,
              title, summary, objective_text, objective_kind,
              target_location_id, target_biome_id, target_floor_number,
              target_count, progress_value, progress_target, status,
              completion_summary, offered_at, accepted_at, completed_at,
              declined_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quest_id,
                player_id,
                template_id,
                run_id,
                offered_by_npc_id,
                title,
                summary,
                objective_text,
                objective_kind,
                target_location_id,
                target_biome_id,
                target_floor_number,
                target_count,
                progress_value,
                progress_target,
                status,
                None,
                now,
                None,
                None,
                None,
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT id, player_id, template_id, run_id, offered_by_npc_id,
                   title, summary, objective_text, objective_kind,
                   target_location_id, target_biome_id, target_floor_number,
                   target_count, progress_value, progress_target, status,
                   completion_summary, offered_at, accepted_at, completed_at,
                   declined_at, updated_at
            FROM player_quests
            WHERE id = ?
            """,
            (quest_id,),
        ).fetchone()
        connection.commit()
    return QuestRow(**row) if row else QuestRow(**{  
        "id": quest_id, "player_id": player_id, "template_id": template_id, "run_id": run_id,
        "offered_by_npc_id": offered_by_npc_id, "title": title, "summary": summary,
        "objective_text": objective_text, "objective_kind": objective_kind,
        "target_location_id": target_location_id, "target_biome_id": target_biome_id,
        "target_floor_number": target_floor_number, "target_count": target_count,
        "progress_value": progress_value, "progress_target": progress_target, "status": status,
        "completion_summary": None, "offered_at": now, "accepted_at": None,
        "completed_at": None, "declined_at": None, "updated_at": now,
    })


def list_player_quests(player_id: str, db_path: Path | None = None) -> list[QuestRow]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, player_id, template_id, run_id, offered_by_npc_id,
                   title, summary, objective_text, objective_kind,
                   target_location_id, target_biome_id, target_floor_number,
                   target_count, progress_value, progress_target, status,
                   completion_summary, offered_at, accepted_at, completed_at,
                   declined_at, updated_at
            FROM player_quests
            WHERE player_id = ?
            ORDER BY updated_at DESC, offered_at DESC
            """,
            (player_id,),
        ).fetchall()
    return [QuestRow(**dict(row)) for row in rows]


def load_player_quest(player_id: str, quest_id: str, db_path: Path | None = None) -> QuestRow | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, player_id, template_id, run_id, offered_by_npc_id,
                   title, summary, objective_text, objective_kind,
                   target_location_id, target_biome_id, target_floor_number,
                   target_count, progress_value, progress_target, status,
                   completion_summary, offered_at, accepted_at, completed_at,
                   declined_at, updated_at
            FROM player_quests
            WHERE player_id = ? AND id = ?
            """,
            (player_id, quest_id),
        ).fetchone()
    return QuestRow(**dict(row)) if row else None


def set_player_quest_status(
    quest_id: str,
    status: str,
    completion_summary: str | None = None,
    db_path: Path | None = None,
) -> None:
    now = utc_now()
    accepted_at = now if status == "active" else None
    completed_at = now if status == "completed" else None
    declined_at = now if status == "declined" else None
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE player_quests
            SET status = ?,
                completion_summary = COALESCE(?, completion_summary),
                accepted_at = COALESCE(?, accepted_at),
                completed_at = COALESCE(?, completed_at),
                declined_at = COALESCE(?, declined_at),
                updated_at = ?
            WHERE id = ?
            """,
            (status, completion_summary, accepted_at, completed_at, declined_at, now, quest_id),
        )
        connection.commit()


def set_player_quest_progress(
    quest_id: str,
    progress_value: int,
    objective_text: str | None = None,
    db_path: Path | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            UPDATE player_quests
            SET progress_value = ?,
                objective_text = COALESCE(?, objective_text),
                updated_at = ?
            WHERE id = ?
            """,
            (progress_value, objective_text, utc_now(), quest_id),
        )
        connection.commit()
