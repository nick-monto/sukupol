from __future__ import annotations
from pathlib import Path
from typing import Any
from uuid import uuid4

from .connection import connect, utc_now
from .rows import NpcJournalEntryRow, NpcJournalEntryItem, NpcJournalGroup



def create_npc_journal_entry(
    player_id: str,
    npc_id: str,
    run_id: str,
    summary: str,
    visit_started_at: str,
    visit_ended_at: str,
    turn_count: int,
    db_path: Path | None = None,
) -> NpcJournalEntryRow:
    entry_id = str(uuid4())
    created_at = utc_now()
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO npc_journal_entries (
              id,
              player_id,
              npc_instance_id,
              run_id,
              turn_count,
              visit_started_at,
              visit_ended_at,
              summary,
              created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                player_id,
                npc_id,
                run_id,
                max(turn_count, 0),
                visit_started_at,
                visit_ended_at,
                summary.strip(),
                created_at,
            ),
        )
        row = connection.execute(
            """
            SELECT journal.id, journal.npc_instance_id AS npc_id, defs.display_name AS npc_name,
                   journal.run_id, journal.turn_count, journal.visit_started_at,
                   journal.visit_ended_at, journal.summary, journal.created_at
            FROM npc_journal_entries AS journal
            JOIN npc_instances AS instances ON instances.id = journal.npc_instance_id
            JOIN npc_definitions AS defs ON defs.id = instances.definition_id
            WHERE journal.id = ?
            """,
            (entry_id,),
        ).fetchone()
        connection.commit()

    return NpcJournalEntryRow(
        id=entry_id,
        npc_id=npc_id,
        run_id=run_id,
        turn_count=max(turn_count, 0),
        visit_started_at=visit_started_at,
        visit_ended_at=visit_ended_at,
        summary=summary.strip(),
        created_at=created_at,
        player_id=player_id,
    )


def list_player_npc_journal(player_id: str, db_path: Path | None = None) -> list[NpcJournalGroup]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT journal.id, journal.npc_instance_id AS npc_id, defs.display_name AS npc_name,
                   journal.run_id, journal.turn_count, journal.visit_started_at,
                   journal.visit_ended_at, journal.summary, journal.created_at
            FROM npc_journal_entries AS journal
            JOIN npc_instances AS instances ON instances.id = journal.npc_instance_id
            JOIN npc_definitions AS defs ON defs.id = instances.definition_id
            WHERE journal.player_id = ?
            ORDER BY journal.visit_ended_at DESC, journal.created_at DESC
            """,
            (player_id,),
        ).fetchall()
    raw_groups: dict[str, dict[str, Any]] = {}
    ordered_raw: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        group = raw_groups.get(payload["npc_id"])
        if group is None:
            group = {
                "npc_id": payload["npc_id"],
                "npc_name": payload["npc_name"],
                "entries": [],
            }
            raw_groups[payload["npc_id"]] = group
            ordered_raw.append(group)

        group["entries"].append(
            {
                "id": payload["id"],
                "run_id": payload["run_id"],
                "turn_count": payload["turn_count"],
                "visit_started_at": payload["visit_started_at"],
                "visit_ended_at": payload["visit_ended_at"],
                "summary": payload["summary"],
                "created_at": payload["created_at"],
            }
        )

    return [
        NpcJournalGroup(
            npc_id=g["npc_id"],
            npc_name=g["npc_name"],
            entries=[NpcJournalEntryItem(**e) for e in g["entries"]],
        )
        for g in ordered_raw
    ]
