from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import uuid4

from .connection import connect, utc_now
from .rows import DungeonInstanceRow


logger = logging.getLogger(__name__)


def get_dungeon_instance_for_run(run_id: str, db_path: Path | None = None) -> DungeonInstanceRow | None:
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, biome_id, run_seed, procgen_version, created_at
            FROM dungeon_instances
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    return DungeonInstanceRow(**dict(row)) if row else None


def create_dungeon_instance(
    run_id: str,
    biome_id: str,
    run_seed: int,
    procgen_version: str,
    db_path: Path | None = None,
) -> DungeonInstanceRow:
    existing = get_dungeon_instance_for_run(run_id, db_path=db_path)
    if existing is not None:
        return existing
    instance_id = str(uuid4())
    logger.info("Creating dungeon instance %s for run %s, biome %s", instance_id, run_id, biome_id)
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

    return DungeonInstanceRow(**payload)


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
    procgen_features: list[dict],
    generation: dict,
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
                            procgen_features_json,
                            generation_json,
              validation_json,
              created_at,
              updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(location_id) DO UPDATE SET
              ascii_map_json = excluded.ascii_map_json,
              exits_json = excluded.exits_json,
              name = excluded.name,
              description = excluded.description,
              entry_x = excluded.entry_x,
              entry_y = excluded.entry_y,
                            procgen_features_json = excluded.procgen_features_json,
                            generation_json = excluded.generation_json,
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
                json.dumps(procgen_features, sort_keys=True),
                json.dumps(generation, sort_keys=True),
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
                 ascii_map_json, exits_json, entry_x, entry_y,
                 procgen_features_json, generation_json, validation_json
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
        "encounter_biome_id": row["biome_id"],
        "encounter_enabled": True,
        "encounter_floor": row["floor_number"],
        "floor_number": row["floor_number"],
        "location_type": "dungeon",
        "floor_seed": row["floor_seed"],
        "entry_x": row["entry_x"],
        "entry_y": row["entry_y"],
        "procgen_features": json.loads(row["procgen_features_json"]),
        "procgen_generation": json.loads(row["generation_json"]),
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
