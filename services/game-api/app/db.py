from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .content import DEFAULT_DB_PATH, SCHEMA_DIR, WorldContent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_db_path() -> Path:
    configured = os.getenv("SUKUPOL_DB_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(world: WorldContent, db_path: Path | None = None) -> None:
    with connect(db_path) as connection:
        for schema_path in sorted(SCHEMA_DIR.glob("*.sql")):
            connection.executescript(schema_path.read_text(encoding="utf-8"))
        seed_npc_content(connection, world)
        seed_gameplay_content(connection, world)
        connection.commit()


def seed_npc_content(connection: sqlite3.Connection, world: WorldContent) -> None:
    definitions: dict[str, dict[str, str]] = {}
    for npc in world.npcs.values():
        definition_id = npc["definition_id"]
        if definition_id not in definitions:
            definitions[definition_id] = {
                "display_name": npc["display_name"],
                "role": npc["role"],
                "system_prompt": npc["system_prompt"],
            }

    for definition_id, definition in definitions.items():
        connection.execute(
            """
            INSERT INTO npc_definitions (id, display_name, role, system_prompt)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              display_name = excluded.display_name,
              role = excluded.role,
              system_prompt = excluded.system_prompt
            """,
            (
                definition_id,
                definition["display_name"],
                definition["role"],
                definition["system_prompt"],
            ),
        )


def seed_npc_knowledge(connection: sqlite3.Connection, world: WorldContent) -> None:
    for npc in world.npcs.values():
        now = utc_now()
        knowledge_entries = [
            ("persona", npc["system_prompt"]),
            ("town", npc["town_hint"]),
            ("dungeon", npc["dungeon_hint"]),
            ("supply", npc["supply_hint"]),
        ]
        for category, content in knowledge_entries:
            connection.execute(
                """
                INSERT INTO npc_shared_knowledge (id, npc_instance_id, category, content, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(npc_instance_id, category, content) DO UPDATE SET
                  source = excluded.source,
                  updated_at = excluded.updated_at
                """,
                (str(uuid4()), npc["id"], category, content, "seed", now, now),
            )


def seed_gameplay_content(connection: sqlite3.Connection, world: WorldContent) -> None:
    for item in world.items.values():
        connection.execute(
            """
            INSERT INTO item_definitions (id, name, item_type, damage, healing, stackable, value, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name,
              item_type = excluded.item_type,
              damage = excluded.damage,
              healing = excluded.healing,
              stackable = excluded.stackable,
              value = excluded.value,
              description = excluded.description
            """,
            (
                item["id"],
                item["name"],
                item["item_type"],
                item.get("damage", 0),
                item.get("healing", 0),
                int(bool(item.get("stackable", False))),
                item.get("value", 0),
                item.get("description", ""),
            ),
        )

    for enemy in world.enemies.values():
        connection.execute(
            """
            INSERT INTO enemy_definitions (id, name, max_hp, damage, defence, gold_min, gold_max, loot_json, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              name = excluded.name,
              max_hp = excluded.max_hp,
              damage = excluded.damage,
              defence = excluded.defence,
              gold_min = excluded.gold_min,
              gold_max = excluded.gold_max,
              loot_json = excluded.loot_json,
              description = excluded.description
            """,
            (
                enemy["id"],
                enemy["name"],
                enemy["max_hp"],
                enemy["damage"],
                enemy.get("defence", 0),
                enemy.get("gold_drop", [0, 0])[0],
                enemy.get("gold_drop", [0, 0])[1],
                json.dumps(enemy.get("loot_table", []), sort_keys=True),
                enemy.get("description", ""),
            ),
        )

    for encounter in world.encounters:
        connection.execute(
            """
            INSERT INTO encounter_definitions (id, biome_id, floor_number, enemy_ids_json, message)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              biome_id = excluded.biome_id,
              floor_number = excluded.floor_number,
              enemy_ids_json = excluded.enemy_ids_json,
              message = excluded.message
            """,
            (
                encounter["id"],
                encounter["biome_id"],
                encounter["floor_number"],
                json.dumps(encounter["enemy_ids"], sort_keys=True),
                encounter["message"],
            ),
        )

    for npc in world.npcs.values():
        connection.execute(
            """
            INSERT INTO npc_instances (id, definition_id, location_id, x, y, relationship)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              definition_id = excluded.definition_id,
              location_id = excluded.location_id,
              x = excluded.x,
              y = excluded.y
            """,
            (
                npc["id"],
                npc["definition_id"],
                npc["location_id"],
                npc["x"],
                npc["y"],
                0,
            ),
        )

    seed_npc_knowledge(connection, world)


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


def load_run_snapshot(run_id: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT snapshot_json FROM run_sessions WHERE id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row["snapshot_json"])


def get_dungeon_instance_for_run(run_id: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, biome_id, run_seed, procgen_version, created_at
            FROM dungeon_instances
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    return dict(row) if row else None


def create_dungeon_instance(
    run_id: str,
    biome_id: str,
    run_seed: int,
    procgen_version: str,
    db_path: Path | None = None,
) -> dict:
    existing = get_dungeon_instance_for_run(run_id, db_path=db_path)
    if existing is not None:
        return existing

    instance_id = str(uuid4())
    payload = {
        "id": instance_id,
        "biome_id": biome_id,
        "run_seed": run_seed,
        "procgen_version": procgen_version,
        "created_at": utc_now(),
    }
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO dungeon_instances (id, run_id, biome_id, run_seed, procgen_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                instance_id,
                run_id,
                biome_id,
                run_seed,
                procgen_version,
                payload["created_at"],
            ),
        )
        connection.commit()

    return payload


def persist_dungeon_floor(
    dungeon_instance_id: str,
    biome_id: str,
    floor_number: int,
    floor_seed: int,
    location_id: str,
    name: str,
    description: str,
    ascii_map: list[str],
    exits: list[dict],
    entry_x: int,
    entry_y: int,
    validation: dict,
    db_path: Path | None = None,
) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO dungeon_floors (
              id,
              dungeon_instance_id,
              biome_id,
              floor_number,
              floor_seed,
              location_id,
              name,
              description,
              ascii_map_json,
              exits_json,
              entry_x,
              entry_y,
              validation_json,
              created_at,
              updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location_id) DO UPDATE SET
              ascii_map_json = excluded.ascii_map_json,
              exits_json = excluded.exits_json,
              name = excluded.name,
              description = excluded.description,
              entry_x = excluded.entry_x,
              entry_y = excluded.entry_y,
              validation_json = excluded.validation_json,
              updated_at = excluded.updated_at
            """,
            (
                str(uuid4()),
                dungeon_instance_id,
                biome_id,
                floor_number,
                floor_seed,
                location_id,
                name,
                description,
                json.dumps(ascii_map),
                json.dumps(exits),
                entry_x,
                entry_y,
                json.dumps(validation, sort_keys=True),
                utc_now(),
                utc_now(),
            ),
        )
        connection.commit()


def load_dungeon_floor(location_id: str, db_path: Path | None = None) -> dict | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT biome_id, floor_number, floor_seed, location_id, name, description,
                   ascii_map_json, exits_json, entry_x, entry_y, validation_json
            FROM dungeon_floors
            WHERE location_id = ?
            """,
            (location_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["location_id"],
        "name": row["name"],
        "description": row["description"],
        "ascii_map": json.loads(row["ascii_map_json"]),
        "exits": json.loads(row["exits_json"]),
        "biome_id": row["biome_id"],
        "floor_number": row["floor_number"],
        "floor_seed": row["floor_seed"],
        "entry_x": row["entry_x"],
        "entry_y": row["entry_y"],
        "validation": json.loads(row["validation_json"]),
    }


def load_dungeon_floor_for_instance(
    dungeon_instance_id: str,
    floor_number: int,
    db_path: Path | None = None,
) -> dict | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT location_id
            FROM dungeon_floors
            WHERE dungeon_instance_id = ? AND floor_number = ?
            """,
            (dungeon_instance_id, floor_number),
        ).fetchone()

    if row is None:
        return None

    return load_dungeon_floor(row["location_id"], db_path=db_path)


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


def load_npc_player_memory(player_id: str, npc_id: str, db_path: Path | None = None) -> dict:
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
        return {
            "summary": legacy_summary,
            "last_player_message": "",
            "last_npc_reply": "",
            "updated_at": "",
        }

    return dict(row)


def create_npc_journal_entry(
    player_id: str,
    npc_id: str,
    run_id: str,
    summary: str,
    visit_started_at: str,
    visit_ended_at: str,
    turn_count: int,
    db_path: Path | None = None,
) -> dict:
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

    return dict(row) if row else {
        "id": entry_id,
        "npc_id": npc_id,
        "npc_name": npc_id,
        "run_id": run_id,
        "turn_count": max(turn_count, 0),
        "visit_started_at": visit_started_at,
        "visit_ended_at": visit_ended_at,
        "summary": summary.strip(),
        "created_at": created_at,
    }


def list_player_npc_journal(player_id: str, db_path: Path | None = None) -> list[dict]:
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

    groups: dict[str, dict] = {}
    ordered_groups: list[dict] = []
    for row in rows:
        payload = dict(row)
        group = groups.get(payload["npc_id"])
        if group is None:
            group = {
                "npc_id": payload["npc_id"],
                "npc_name": payload["npc_name"],
                "entries": [],
            }
            groups[payload["npc_id"]] = group
            ordered_groups.append(group)

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

    return ordered_groups


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


def list_npc_shared_knowledge(npc_id: str, limit: int = 8, db_path: Path | None = None) -> list[dict]:
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

    return [dict(row) for row in rows]


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
) -> dict:
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

    return {
        "total_runs": total_runs,
        "total_victories": total_victories,
        "deepest_depth": deepest_depth,
        "last_outcome": result,
    }


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
