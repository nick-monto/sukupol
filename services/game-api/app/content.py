from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTENT_PATH = REPO_ROOT / "packages" / "content" / "world" / "bootstrap.json"
SCHEMA_DIR = REPO_ROOT / "packages" / "schema" / "sql"
DEFAULT_DB_PATH = REPO_ROOT / "services" / "game-api" / "data" / "sukupol.db"
SUPPORTED_MAP_GLYPHS = frozenset({"#", ".", "∪", "∩"})
WALKABLE_MAP_GLYPHS = frozenset({".", "<", "∪", "∩"})


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
    item_by_id = {item["id"]: item for item in raw.get("items", [])}
    enemy_by_id = {enemy["id"]: enemy for enemy in raw.get("enemies", [])}
    overworld_positions: set[tuple[int, int]] = set()

    for location in locations:
        rows = validate_ascii_map(location)
        validate_overworld_map(location, overworld_positions)
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

    for biome in raw.get("dungeon_biomes", []):
        validate_procgen_biome(biome, location_by_id)

    for enemy in raw.get("enemies", []):
        validate_ascii_art(enemy.get("ascii_art", []), f"enemy {enemy['id']}")
        validate_enemy(enemy, item_by_id)

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


def validate_enemy(enemy: dict[str, Any], items: dict[str, dict[str, Any]]) -> None:
    for loot_entry in enemy.get("loot_table", []):
        item_id = loot_entry.get("item_id")
        if item_id not in items:
            raise ValueError(f"Enemy {enemy.get('id', '<unknown>')} references unknown loot item {item_id}")

    communication_mode = enemy.get("communication_mode")
    if communication_mode is not None and communication_mode not in {"speech", "telepathy"}:
        raise ValueError(
            f"Enemy {enemy.get('id', '<unknown>')} communication_mode must be speech or telepathy"
        )

    negotiation = enemy.get("negotiation")
    if negotiation is None:
        return

    if communication_mode not in {"speech", "telepathy"}:
        raise ValueError(
            f"Enemy {enemy.get('id', '<unknown>')} negotiation requires communication_mode"
        )

    if not isinstance(negotiation, dict):
        raise ValueError(f"Enemy {enemy.get('id', '<unknown>')} negotiation must be an object")

    temperament = negotiation.get("temperament", "wary")
    if temperament not in {"wary", "resentful", "irate"}:
        raise ValueError(
            f"Enemy {enemy.get('id', '<unknown>')} negotiation temperament must be wary, resentful, or irate"
        )

    can_negotiate = bool(negotiation.get("can_negotiate", True))
    outcomes = negotiation.get("outcomes", [])
    if not isinstance(outcomes, list):
        raise ValueError(f"Enemy {enemy.get('id', '<unknown>')} negotiation outcomes must be a list")

    invalid_outcomes = [outcome for outcome in outcomes if outcome not in {"recruit", "tribute", "retreat"}]
    if invalid_outcomes:
        raise ValueError(
            f"Enemy {enemy.get('id', '<unknown>')} negotiation has unsupported outcomes: {', '.join(invalid_outcomes)}"
        )

    if can_negotiate and not outcomes:
        raise ValueError(
            f"Enemy {enemy.get('id', '<unknown>')} must define at least one negotiation outcome when can_negotiate is true"
        )

    difficulty = int(negotiation.get("difficulty", 5))
    anger_limit = int(negotiation.get("anger_limit", 2))
    if not 1 <= difficulty <= 10:
        raise ValueError(f"Enemy {enemy.get('id', '<unknown>')} negotiation difficulty must be between 1 and 10")
    if anger_limit < 1:
        raise ValueError(f"Enemy {enemy.get('id', '<unknown>')} negotiation anger_limit must be at least 1")

    if "recruit" in outcomes:
        ally_battles = int(negotiation.get("ally_battles", 0))
        if ally_battles < 1:
            raise ValueError(
                f"Enemy {enemy.get('id', '<unknown>')} must define ally_battles >= 1 for recruit outcomes"
            )

    tribute_item_id = negotiation.get("tribute_item_id")
    if tribute_item_id is not None:
        if tribute_item_id not in items:
            raise ValueError(
                f"Enemy {enemy.get('id', '<unknown>')} negotiation references unknown tribute item {tribute_item_id}"
            )
        tribute_quantity = int(negotiation.get("tribute_quantity", 1))
        if tribute_quantity < 1:
            raise ValueError(
                f"Enemy {enemy.get('id', '<unknown>')} negotiation tribute_quantity must be at least 1"
            )


def validate_procgen_biome(
    biome: dict[str, Any],
    locations: dict[str, dict[str, Any]],
) -> None:
    for field_name in ("floor_name_prefixes", "floor_description_templates", "floor_description_features"):
        field_value = biome.get(field_name)
        if field_value is None:
            continue
        if not isinstance(field_value, list) or not field_value or not all(isinstance(entry, str) and entry for entry in field_value):
            raise ValueError(f"Biome {biome.get('id', '<unknown>')} must define {field_name} as a non-empty list of strings")

    generation_profile = biome.get("generation_profile")
    if generation_profile is not None and (not isinstance(generation_profile, str) or not generation_profile):
        raise ValueError(f"Biome {biome.get('id', '<unknown>')} generation_profile must be a non-empty string")

    for mapping_name in ("generation_settings", "depth_progression"):
        mapping = biome.get(mapping_name)
        if mapping is None:
            continue
        if not isinstance(mapping, dict):
            raise ValueError(f"Biome {biome.get('id', '<unknown>')} {mapping_name} must be an object")
        for key, value in mapping.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"Biome {biome.get('id', '<unknown>')} {mapping_name} contains an invalid key")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Biome {biome.get('id', '<unknown>')} {mapping_name}.{key} must be numeric")

    for field_name in ("landmark_types", "hazard_types"):
        feature_pool = biome.get(field_name)
        if feature_pool is None:
            continue
        validate_procgen_feature_pool(feature_pool, f"Biome {biome.get('id', '<unknown>')} {field_name}")

    return_exit = biome.get("return_exit")
    if return_exit is None:
        return

    if not isinstance(return_exit, dict):
        raise ValueError(f"Biome {biome.get('id', '<unknown>')} return_exit must be an object")

    target_location = require_location(
        locations,
        return_exit["target_location_id"],
        f"biome {biome.get('id', '<unknown>')} return_exit",
    )
    validate_walkable_position(
        target_location["ascii_map"],
        int(return_exit["target_x"]),
        int(return_exit["target_y"]),
        f"biome {biome.get('id', '<unknown>')} return_exit",
    )

    if not isinstance(return_exit.get("message"), str) or not return_exit["message"]:
        raise ValueError(f"Biome {biome.get('id', '<unknown>')} return_exit must define a non-empty message")


def validate_procgen_feature_pool(feature_pool: Any, label: str) -> None:
    if not isinstance(feature_pool, list) or not feature_pool:
        raise ValueError(f"{label} must be a non-empty list")

    for entry in feature_pool:
        if isinstance(entry, str):
            if not entry:
                raise ValueError(f"{label} cannot include an empty feature kind")
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"{label} entries must be strings or objects")
        if not isinstance(entry.get("kind"), str) or not entry["kind"]:
            raise ValueError(f"{label} object entries must define a non-empty kind")
        if "variant" in entry and (not isinstance(entry["variant"], str) or not entry["variant"]):
            raise ValueError(f"{label} entry {entry['kind']} has an invalid variant")
        if "detail" in entry and (not isinstance(entry["detail"], str) or not entry["detail"]):
            raise ValueError(f"{label} entry {entry['kind']} has an invalid detail")
        for numeric_field in ("weight", "radius", "min_floor", "max_floor"):
            if numeric_field not in entry:
                continue
            value = entry[numeric_field]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{label} entry {entry['kind']} field {numeric_field} must be an integer")
        if int(entry.get("weight", 1)) < 1:
            raise ValueError(f"{label} entry {entry['kind']} weight must be at least 1")
        if int(entry.get("radius", 0)) < 0:
            raise ValueError(f"{label} entry {entry['kind']} radius must be zero or greater")
        min_floor = int(entry.get("min_floor", 1))
        max_floor = int(entry.get("max_floor", min_floor))
        if min_floor < 1 or max_floor < min_floor:
            raise ValueError(f"{label} entry {entry['kind']} must define a valid min/max floor range")
        tags = entry.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag for tag in tags):
            raise ValueError(f"{label} entry {entry['kind']} tags must be a list of non-empty strings")


def validate_overworld_map(location: dict[str, Any], used_positions: set[tuple[int, int]]) -> None:
    overworld_map = location.get("overworld_map")
    if overworld_map is None:
        return

    if not isinstance(overworld_map, dict):
        raise ValueError(f"Location {location['id']} overworld_map must be an object")

    x = overworld_map.get("x")
    y = overworld_map.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError(f"Location {location['id']} overworld_map must define integer x and y coordinates")

    position = (x, y)
    if position in used_positions:
        raise ValueError(f"Location {location['id']} reuses overworld map position {position}")

    used_positions.add(position)


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
