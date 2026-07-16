from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..content import DEFAULT_DB_PATH, SCHEMA_DIR, WorldContent

logger = logging.getLogger(__name__)


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
    from .seed import seed_npc_content, seed_gameplay_content

    logger.info("Initializing database at %s", db_path or resolve_db_path())
    with connect(db_path) as connection:
        # 1. Always ensure schema_version table exists (000 migration)
        connection.executescript(
            (SCHEMA_DIR / "000_schema_version.sql").read_text(encoding="utf-8")
        )
        # 2. Read already-applied migrations
        applied = {
            row["applied"]
            for row in connection.execute("SELECT applied FROM schema_version").fetchall()
        }
        # 3. Backfill for existing DBs (already migrated, version table was empty):
        #    record all migration files older than 006 as applied so they are never re-run.
        if not applied:
            has_tables = bool(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='run_sessions'"
                ).fetchone()
            )
            if has_tables:
                for p in sorted(SCHEMA_DIR.glob("*.sql")):
                    name = p.name
                    if name < "006_dungeon_floor_procgen_columns.sql":
                        connection.execute(
                            "INSERT OR IGNORE INTO schema_version (applied) VALUES (?)",
                            (name,),
                        )
                applied = {
                    row["applied"]
                    for row in connection.execute("SELECT applied FROM schema_version").fetchall()
                }
        # 4. Apply unapplied migrations
        for schema_path in sorted(SCHEMA_DIR.glob("*.sql")):
            name = schema_path.name
            if name in applied:
                continue
            if name == "006_dungeon_floor_procgen_columns.sql":
                # Idempotency guard: only ALTER if the target columns are absent
                cols = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(dungeon_floors)").fetchall()
                }
                if cols:  # table exists
                    if "procgen_features_json" not in cols:
                        connection.execute(
                            "ALTER TABLE dungeon_floors ADD COLUMN procgen_features_json TEXT NOT NULL DEFAULT '[]'"
                        )
                    if "generation_json" not in cols:
                        connection.execute(
                            "ALTER TABLE dungeon_floors ADD COLUMN generation_json TEXT NOT NULL DEFAULT '{}'"
                        )
                connection.execute(
                    "INSERT OR IGNORE INTO schema_version (applied) VALUES (?)", (name,)
                )
            else:
                connection.executescript(schema_path.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT OR IGNORE INTO schema_version (applied) VALUES (?)", (name,)
                )
        # 5. Seed content
        seed_npc_content(connection, world)
        seed_gameplay_content(connection, world)
        connection.commit()
    logger.info("Database initialized successfully")
