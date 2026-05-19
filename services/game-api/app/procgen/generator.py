from __future__ import annotations

import random
from typing import Any

from .models import FloorLayout, RectRoom
from .validator import validate_floor


PROFILE_DEFAULTS: dict[str, dict[str, float | int]] = {
    "rooms": {
        "connection_window": 3,
        "branch_chance": 0.35,
        "extra_loops": 1,
        "max_room_placement_tries": 30,
        "base_landmarks": 1,
        "base_hazards": 1,
    },
    "halls": {
        "connection_window": 4,
        "branch_chance": 0.45,
        "extra_loops": 2,
        "max_room_placement_tries": 36,
        "base_landmarks": 2,
        "base_hazards": 2,
    },
    "flooded_archive": {
        "connection_window": 5,
        "branch_chance": 0.6,
        "extra_loops": 3,
        "max_room_placement_tries": 42,
        "base_landmarks": 2,
        "base_hazards": 3,
    },
}


def carve_room(grid: list[list[str]], room: RectRoom) -> None:
    for y in range(room.y, room.y + room.height):
        for x in range(room.x, room.x + room.width):
            grid[y][x] = "."


def carve_h_corridor(grid: list[list[str]], x1: int, x2: int, y: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        grid[y][x] = "."


def carve_v_corridor(grid: list[list[str]], y1: int, y2: int, x: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        grid[y][x] = "."


def room_overlaps(room: RectRoom, other: RectRoom) -> bool:
    return not (
        room.x + room.width + 1 < other.x
        or other.x + other.width + 1 < room.x
        or room.y + room.height + 1 < other.y
        or other.y + other.height + 1 < room.y
    )


def derive_floor_seed(run_seed: int, floor_number: int, biome_id: str, attempt: int) -> int:
    biome_hash = sum(ord(character) for character in biome_id)
    return run_seed + (floor_number * 10_003) + biome_hash + attempt * 97


def build_floor_name(biome: dict, floor_number: int, randomizer: random.Random) -> str:
    prefixes = biome.get("floor_name_prefixes", [])
    if not prefixes:
        return f"{biome['name']} F{floor_number}"
    return f"{biome['name']}: {randomizer.choice(prefixes)} F{floor_number}"


def build_floor_description(biome: dict, floor_number: int, randomizer: random.Random) -> str:
    templates = biome.get("floor_description_templates", [])
    if not templates:
        return biome["description"]

    features = biome.get("floor_description_features", [])
    feature = randomizer.choice(features) if features else biome["description"].lower()
    template = randomizer.choice(templates)
    return template.format(
        biome_name=biome["name"],
        floor_number=floor_number,
        feature=feature,
    )


def build_return_exit(biome: dict, entry_x: int, entry_y: int) -> dict:
    return_exit = biome.get("return_exit", {})
    return {
        "x": entry_x,
        "y": entry_y,
        "target_location_id": return_exit.get("target_location_id", "dungeon_approach"),
        "target_x": int(return_exit.get("target_x", 4)),
        "target_y": int(return_exit.get("target_y", 5)),
        "target_facing": return_exit.get("target_facing", "S"),
        "message": return_exit.get(
            "message",
            biome.get("return_message", "You retrace your steps to the surface."),
        ),
    }


def scaled_value(base: int, floor_number: int, progression: dict[str, Any], prefix: str) -> int:
    every = int(progression.get(f"{prefix}_growth_every", 0) or 0)
    amount = int(progression.get(f"{prefix}_growth_amount", 1) or 1)
    max_bonus = progression.get(f"max_{prefix}_bonus")
    if every <= 0 or amount <= 0 or floor_number <= 1:
        return base

    bonus = ((floor_number - 1) // every) * amount
    if max_bonus is not None:
        bonus = min(bonus, int(max_bonus))
    return base + bonus


def resolve_generation_settings(biome: dict[str, Any], floor_number: int) -> dict[str, Any]:
    profile = biome.get("generation_profile") or "rooms"
    settings = dict(PROFILE_DEFAULTS.get(profile, PROFILE_DEFAULTS["rooms"]))
    settings.update(biome.get("generation_settings", {}))
    progression = biome.get("depth_progression", {})

    width = scaled_value(int(biome.get("floor_width", 19)), floor_number, progression, "width")
    height = scaled_value(int(biome.get("floor_height", 19)), floor_number, progression, "height")
    max_rooms = scaled_value(int(biome.get("max_rooms", 6)), floor_number, progression, "room")
    landmark_count = scaled_value(int(settings.get("base_landmarks", 1)), floor_number, progression, "landmark")
    hazard_count = scaled_value(int(settings.get("base_hazards", 1)), floor_number, progression, "hazard")
    extra_loops = scaled_value(int(settings.get("extra_loops", 1)), floor_number, progression, "loop")

    room_max_size = min(int(biome.get("room_max_size", 5)), max(3, min(width, height) - 4))
    room_min_size = min(int(biome.get("room_min_size", 3)), room_max_size)

    return {
        "profile": profile,
        "width": max(11, width),
        "height": max(11, height),
        "max_rooms": max(3, max_rooms),
        "room_min_size": max(3, room_min_size),
        "room_max_size": max(3, room_max_size),
        "connection_window": max(2, int(settings.get("connection_window", 3))),
        "branch_chance": max(0.0, min(1.0, float(settings.get("branch_chance", 0.35)))),
        "extra_loops": max(0, extra_loops),
        "max_room_placement_tries": max(20, int(settings.get("max_room_placement_tries", 30))),
        "landmark_count": max(0, landmark_count),
        "hazard_count": max(0, hazard_count),
    }


def connect_rooms(grid: list[list[str]], room_a: RectRoom, room_b: RectRoom, randomizer: random.Random) -> None:
    x1, y1 = room_a.center
    x2, y2 = room_b.center
    if randomizer.random() < 0.5:
        carve_h_corridor(grid, x1, x2, y1)
        carve_v_corridor(grid, y1, y2, x2)
    else:
        carve_v_corridor(grid, y1, y2, x1)
        carve_h_corridor(grid, x1, x2, y2)


def choose_anchor_room(room_count: int, settings: dict[str, Any], randomizer: random.Random) -> int:
    if room_count <= 1:
        return 0

    profile = settings["profile"]
    if profile == "flooded_archive" and randomizer.random() < 0.3:
        return randomizer.randint(0, room_count - 1)

    if randomizer.random() < settings["branch_chance"]:
        start = max(0, room_count - settings["connection_window"])
        return randomizer.randint(start, room_count - 1)
    return room_count - 1


def room_distance(room_a: RectRoom, room_b: RectRoom) -> int:
    ax, ay = room_a.center
    bx, by = room_b.center
    return abs(ax - bx) + abs(ay - by)


def add_loop_connections(
    grid: list[list[str]],
    rooms: list[RectRoom],
    connected_pairs: set[tuple[int, int]],
    extra_loops: int,
    randomizer: random.Random,
) -> int:
    if extra_loops <= 0:
        return 0

    candidate_pairs = [
        (left_index, right_index)
        for left_index in range(len(rooms))
        for right_index in range(left_index + 1, len(rooms))
        if (left_index, right_index) not in connected_pairs
    ]
    randomizer.shuffle(candidate_pairs)
    candidate_pairs.sort(key=lambda pair: room_distance(rooms[pair[0]], rooms[pair[1]]))

    loops_added = 0
    for left_index, right_index in candidate_pairs:
        connect_rooms(grid, rooms[left_index], rooms[right_index], randomizer)
        connected_pairs.add((left_index, right_index))
        loops_added += 1
        if loops_added >= extra_loops:
            break
    return loops_added


def normalize_feature_pool(entries: list[Any], floor_number: int) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        feature = {"kind": entry} if isinstance(entry, str) else dict(entry)
        min_floor = int(feature.get("min_floor", 1))
        max_floor = int(feature.get("max_floor", floor_number))
        if min_floor <= floor_number <= max_floor:
            normalized.append(feature)
    return normalized


def choose_weighted_feature(pool: list[dict[str, Any]], randomizer: random.Random) -> dict[str, Any]:
    weights = [max(1, int(entry.get("weight", 1))) for entry in pool]
    return randomizer.choices(pool, weights=weights, k=1)[0]


def feature_tile_candidates(room: RectRoom, randomizer: random.Random) -> list[tuple[int, int]]:
    center = room.center
    tiles = [(x, y) for y in range(room.y, room.y + room.height) for x in range(room.x, room.x + room.width)]
    randomizer.shuffle(tiles)
    if center in tiles:
        tiles.remove(center)
    return [center, *tiles]


def place_feature_batch(
    category: str,
    count: int,
    pool: list[dict[str, Any]],
    rooms: list[RectRoom],
    available_room_indexes: list[int],
    occupied_tiles: set[tuple[int, int]],
    randomizer: random.Random,
    start_index: int,
) -> list[dict[str, Any]]:
    if count <= 0 or not pool or not available_room_indexes:
        return []

    room_indexes = list(available_room_indexes)
    randomizer.shuffle(room_indexes)
    placed: list[dict[str, Any]] = []
    for offset in range(count):
        room_index = room_indexes[offset % len(room_indexes)]
        room = rooms[room_index]
        position = next(
            (tile for tile in feature_tile_candidates(room, randomizer) if tile not in occupied_tiles),
            None,
        )
        if position is None:
            continue
        feature_definition = choose_weighted_feature(pool, randomizer)
        x, y = position
        feature = {
            "id": f"{category}:{start_index + len(placed)}:{feature_definition['kind']}",
            "category": category,
            "kind": feature_definition["kind"],
            "x": x,
            "y": y,
            "room_index": room_index,
            "radius": max(0, int(feature_definition.get("radius", 0))),
            "tags": list(feature_definition.get("tags", [])),
        }
        if feature_definition.get("variant"):
            feature["variant"] = feature_definition["variant"]
        if feature_definition.get("detail"):
            feature["detail"] = feature_definition["detail"]
        placed.append(feature)
        occupied_tiles.add((x, y))
    return placed


def generate_floor(run_seed: int, biome: dict, floor_number: int) -> FloorLayout:
    settings = resolve_generation_settings(biome, floor_number=floor_number)
    for attempt in range(12):
        floor_seed = derive_floor_seed(run_seed, floor_number, biome["id"], attempt)
        try:
            layout = _generate_candidate(
                floor_seed=floor_seed,
                biome=biome,
                floor_number=floor_number,
                settings=settings,
            )
        except ValueError:
            continue
        if layout.validation["is_valid"]:
            return layout

    raise ValueError(f"Unable to generate a valid floor for biome {biome['id']} after repeated attempts")


def _generate_candidate(floor_seed: int, biome: dict, floor_number: int, settings: dict[str, Any]) -> FloorLayout:
    width = settings["width"]
    height = settings["height"]
    max_rooms = settings["max_rooms"]
    room_min_size = settings["room_min_size"]
    room_max_size = settings["room_max_size"]
    randomizer = random.Random(floor_seed)
    grid = [["#" for _ in range(width)] for _ in range(height)]

    rooms: list[RectRoom] = []
    connected_pairs: set[tuple[int, int]] = set()
    placement_tries = max(settings["max_room_placement_tries"], max_rooms * 5)
    for _ in range(placement_tries):
        if len(rooms) >= max_rooms:
            break
        room_width = randomizer.randint(room_min_size, room_max_size)
        room_height = randomizer.randint(room_min_size, room_max_size)
        room_x = randomizer.randint(1, width - room_width - 2)
        room_y = randomizer.randint(1, height - room_height - 2)
        candidate = RectRoom(room_x, room_y, room_width, room_height)
        if any(room_overlaps(candidate, existing) for existing in rooms):
            continue

        carve_room(grid, candidate)
        if rooms:
            anchor_index = choose_anchor_room(len(rooms), settings, randomizer)
            connect_rooms(grid, rooms[anchor_index], candidate, randomizer)
            connected_pairs.add(tuple(sorted((anchor_index, len(rooms)))))
        rooms.append(candidate)

    if len(rooms) < 2:
        raise ValueError("Procgen candidate did not produce enough rooms")

    loops_added = add_loop_connections(
        grid,
        rooms,
        connected_pairs,
        extra_loops=settings["extra_loops"],
        randomizer=randomizer,
    )

    entry_room_index = 0
    entry_x, entry_y = rooms[entry_room_index].center
    exit_room_index = max(range(len(rooms)), key=lambda index: room_distance(rooms[entry_room_index], rooms[index]))
    exit_x, exit_y = rooms[exit_room_index].center
    protected_tiles = {(entry_x, entry_y), (exit_x, exit_y)}
    for origin_x, origin_y in ((entry_x, entry_y), (exit_x, exit_y)):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tile_x = origin_x + dx
            tile_y = origin_y + dy
            if 0 <= tile_x < width and 0 <= tile_y < height:
                protected_tiles.add((tile_x, tile_y))
    grid[entry_y][entry_x] = "∪"
    grid[exit_y][exit_x] = "."

    ascii_map = ["".join(row) for row in grid]
    occupied_tiles = set(protected_tiles)
    available_room_indexes = list(range(len(rooms)))
    hazards = place_feature_batch(
        "hazard",
        settings["hazard_count"],
        normalize_feature_pool(biome.get("hazard_types", []), floor_number),
        rooms,
        available_room_indexes,
        occupied_tiles,
        randomizer,
        start_index=0,
    )
    landmarks = place_feature_batch(
        "landmark",
        settings["landmark_count"],
        normalize_feature_pool(biome.get("landmark_types", []), floor_number),
        rooms,
        available_room_indexes,
        occupied_tiles,
        randomizer,
        start_index=len(hazards),
    )
    features = [*hazards, *landmarks]
    validation = validate_floor(
        ascii_map,
        entry=(entry_x, entry_y),
        exit_point=(exit_x, exit_y),
        features=features,
        reserved_tiles=protected_tiles,
    )
    location_id = f"dungeon:{floor_seed}:{floor_number}"
    exits = [build_return_exit(biome, entry_x=entry_x, entry_y=entry_y)]
    generation = {
        "profile": settings["profile"],
        "room_count": len(rooms),
        "width": width,
        "height": height,
        "loop_count": loops_added,
        "landmark_count": len(landmarks),
        "hazard_count": len(hazards),
        "depth_tier": max(0, floor_number - 1),
    }
    return FloorLayout(
        location_id=location_id,
        name=build_floor_name(biome, floor_number=floor_number, randomizer=randomizer),
        description=build_floor_description(biome, floor_number=floor_number, randomizer=randomizer),
        biome_id=biome["id"],
        floor_number=floor_number,
        floor_seed=floor_seed,
        ascii_map=ascii_map,
        exits=exits,
        entry_x=entry_x,
        entry_y=entry_y,
        features=features,
        generation=generation,
        validation=validation,
    )
