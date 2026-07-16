from __future__ import annotations

import json
import sqlite3
from uuid import uuid4

from ..content import WorldContent
from .connection import utc_now


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
