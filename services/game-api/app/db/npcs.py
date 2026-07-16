from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .connection import connect, utc_now
from .rows import NpcPlayerMemoryRow, NpcSharedKnowledgeRow



def load_conversation_summary(player_id: str, npc_id: str, db_path: Path | None = None) -> str:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT summary
            FROM conversation_summaries
            WHERE player_id = ? AND npc_instance_id = ?
            """,
            (player_id, npc_id),
        ).fetchone()

    return row["summary"] if row else ""


def load_npc_player_memory(player_id: str, npc_id: str, db_path: Path | None = None) -> NpcPlayerMemoryRow:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT summary, last_player_message, last_npc_reply, updated_at
            FROM npc_player_memories
            WHERE player_id = ? AND npc_instance_id = ?
            """,
            (player_id, npc_id),
        ).fetchone()

    if row is None:
        legacy_summary = load_conversation_summary(player_id, npc_id, db_path=db_path)
        return NpcPlayerMemoryRow(
            summary=legacy_summary,
            last_player_message="",
            last_npc_reply="",
            updated_at="",
        )

    return NpcPlayerMemoryRow(**dict(row))


def upsert_npc_player_memory(
    player_id: str,
    npc_id: str,
    summary: str,
    last_player_message: str,
    last_npc_reply: str,
    db_path: Path | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO npc_player_memories (player_id, npc_instance_id, summary, last_player_message, last_npc_reply, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id, npc_instance_id) DO UPDATE SET
              summary = excluded.summary,
              last_player_message = excluded.last_player_message,
              last_npc_reply = excluded.last_npc_reply,
              updated_at = excluded.updated_at
            """,
            (player_id, npc_id, summary, last_player_message, last_npc_reply, utc_now()),
        )
        connection.commit()


def list_npc_shared_knowledge(npc_id: str, limit: int = 8, db_path: Path | None = None) -> list[NpcSharedKnowledgeRow]:
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT category, content, source, updated_at
            FROM npc_shared_knowledge
            WHERE npc_instance_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (npc_id, limit),
        ).fetchall()

    return [NpcSharedKnowledgeRow(**dict(row)) for row in rows]


def upsert_npc_shared_knowledge(
    npc_id: str,
    category: str,
    content: str,
    source: str,
    db_path: Path | None = None,
) -> None:
    if not content.strip():
        return

    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO npc_shared_knowledge (id, npc_instance_id, category, content, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(npc_instance_id, category, content) DO UPDATE SET
              source = excluded.source,
              updated_at = excluded.updated_at
            """,
            (str(uuid4()), npc_id, category, content.strip(), source, utc_now(), utc_now()),
        )
        connection.commit()


def upsert_conversation_summary(
    player_id: str,
    npc_id: str,
    summary: str,
    db_path: Path | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO conversation_summaries (player_id, npc_instance_id, summary, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id, npc_instance_id) DO UPDATE SET
              summary = excluded.summary,
              updated_at = excluded.updated_at
            """,
            (player_id, npc_id, summary, utc_now()),
        )
        connection.commit()
