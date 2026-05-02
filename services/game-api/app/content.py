from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTENT_PATH = REPO_ROOT / "packages" / "content" / "world" / "bootstrap.json"
SCHEMA_DIR = REPO_ROOT / "packages" / "schema" / "sql"
DEFAULT_DB_PATH = REPO_ROOT / "services" / "game-api" / "data" / "sukupol.db"


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
