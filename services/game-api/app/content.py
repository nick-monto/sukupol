from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTENT_PATH = REPO_ROOT / "packages" / "content" / "world" / "bootstrap.json"
SCHEMA_DIR = REPO_ROOT / "packages" / "schema" / "sql"
DEFAULT_DB_PATH = REPO_ROOT / "services" / "game-api" / "data" / "sukupol.db"
DECORATIVE_FLOOR_GLYPHS = frozenset({",", ";"})
SUPPORTED_MAP_GLYPHS = frozenset({"#", ".", ">", "<", *DECORATIVE_FLOOR_GLYPHS})
WALKABLE_MAP_GLYPHS = frozenset({".", ">", "<", *DECORATIVE_FLOOR_GLYPHS})


@dataclass(frozen=True)
class WorldContent:
    player_spawn: dict[str, Any]
    locations: dict[str, dict[str, Any]]
    npcs: dict[str, dict[str, Any]]
    dungeon_biomes: dict[str, dict[str, Any]]
    items: dict[str, dict[str, Any]]
    enemies: dict[str, dict[str, Any]]
    encounters: list[dict[str, Any]]
    starting_inventory: list[dict[str, Any]]


def load_world_content(path: Path = CONTENT_PATH) -> WorldContent:
    raw = json.loads(path.read_text(encoding="utf-8"))
    validate_world_content(raw)
    locations = {location["id"]: location for location in raw["locations"]}
    npcs = {npc["id"]: npc for npc in raw["npcs"]}
    dungeon_biomes = {biome["id"]: biome for biome in raw.get("dungeon_biomes", [])}
    items = {item["id"]: item for item in raw.get("items", [])}
    enemies = {enemy["id"]: enemy for enemy in raw.get("enemies", [])}
    encounters = raw.get("encounters", [])
    return WorldContent(
        player_spawn=raw["player_spawn"],
        locations=locations,
        npcs=npcs,
        dungeon_biomes=dungeon_biomes,
        items=items,
        enemies=enemies,
        encounters=encounters,
        starting_inventory=raw.get("starting_inventory", []),
    )


def validate_world_content(raw: dict[str, Any]) -> None:
    locations = raw.get("locations", [])
    location_by_id = {location["id"]: location for location in locations}
    biome_by_id = {biome["id"]: biome for biome in raw.get("dungeon_biomes", [])}
    enemy_by_id = {enemy["id"]: enemy for enemy in raw.get("enemies", [])}

    for location in locations:
        rows = validate_ascii_map(location)
        for exit_node in location.get("exits", []):
            label = f"location {location['id']} exit at ({exit_node['x']}, {exit_node['y']})"
            validate_walkable_position(rows, exit_node["x"], exit_node["y"], label)

    spawn = raw["player_spawn"]
    spawn_location = require_location(location_by_id, spawn["location_id"], "player spawn")
    validate_walkable_position(
        spawn_location["ascii_map"],
        spawn["x"],
        spawn["y"],
        f"player spawn in {spawn['location_id']}",
    )

    for npc in raw.get("npcs", []):
        validate_ascii_art(npc.get("ascii_art", []), f"npc {npc['id']}")
        npc_location = require_location(location_by_id, npc["location_id"], f"npc {npc['id']}")
        validate_walkable_position(
            npc_location["ascii_map"],
            npc["x"],
            npc["y"],
            f"npc {npc['id']} in {npc['location_id']}",
        )

    for enemy in raw.get("enemies", []):
        validate_ascii_art(enemy.get("ascii_art", []), f"enemy {enemy['id']}")

    for encounter in raw.get("encounters", []):
        validate_encounter(encounter, biome_by_id, enemy_by_id)


def validate_ascii_map(location: dict[str, Any]) -> list[str]:
    rows = location.get("ascii_map", [])
    if not rows or not all(isinstance(row, str) and row for row in rows):
        raise ValueError(f"Location {location['id']} must define a non-empty ascii_map of strings")

    width = len(rows[0])
    for index, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(
                f"Location {location['id']} has inconsistent map width at row {index}: expected {width}, got {len(row)}"
            )
        unsupported = sorted({glyph for glyph in row if glyph not in SUPPORTED_MAP_GLYPHS})
        if unsupported:
            glyphs = ", ".join(repr(glyph) for glyph in unsupported)
            raise ValueError(f"Location {location['id']} uses unsupported map glyphs: {glyphs}")

    return rows


def validate_ascii_art(lines: list[str], label: str) -> None:
    if not isinstance(lines, list) or not lines or not all(isinstance(line, str) and line for line in lines):
        raise ValueError(f"{label} must define a non-empty ascii_art list of strings")


def validate_walkable_position(rows: list[str], x: int, y: int, label: str) -> None:
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[0]):
        raise ValueError(f"{label} is out of bounds")
    if rows[y][x] not in WALKABLE_MAP_GLYPHS:
        raise ValueError(f"{label} must be placed on a walkable tile")


def require_location(
    locations: dict[str, dict[str, Any]],
    location_id: str,
    label: str,
) -> dict[str, Any]:
    try:
        return locations[location_id]
    except KeyError as error:
        raise ValueError(f"{label} references unknown location {location_id}") from error


def validate_encounter(
    encounter: dict[str, Any],
    biomes: dict[str, dict[str, Any]],
    enemies: dict[str, dict[str, Any]],
) -> None:
    biome_id = encounter.get("biome_id")
    if biome_id not in biomes:
        raise ValueError(f"Encounter {encounter.get('id', '<unknown>')} references unknown biome {biome_id}")

    enemy_ids = encounter.get("enemy_ids", [])
    if not isinstance(enemy_ids, list) or not enemy_ids:
        raise ValueError(f"Encounter {encounter.get('id', '<unknown>')} must define at least one enemy_id")

    unknown_enemy_ids = [enemy_id for enemy_id in enemy_ids if enemy_id not in enemies]
    if unknown_enemy_ids:
        raise ValueError(
            f"Encounter {encounter.get('id', '<unknown>')} references unknown enemies: {', '.join(unknown_enemy_ids)}"
        )

    message_by_enemy = encounter.get("message_by_enemy", {})
    if not isinstance(message_by_enemy, dict):
        raise ValueError(f"Encounter {encounter.get('id', '<unknown>')} message_by_enemy must be an object")

    unknown_message_keys = [enemy_id for enemy_id in message_by_enemy if enemy_id not in enemy_ids]
    if unknown_message_keys:
        raise ValueError(
            f"Encounter {encounter.get('id', '<unknown>')} has message_by_enemy keys not present in enemy_ids: "
            f"{', '.join(unknown_message_keys)}"
        )
