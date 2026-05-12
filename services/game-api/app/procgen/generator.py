from __future__ import annotations

import random

from ..content import DECORATIVE_FLOOR_GLYPHS
from .models import FloorLayout, RectRoom
from .validator import validate_floor


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


def apply_floor_dressing(
    grid: list[list[str]],
    randomizer: random.Random,
    protected_tiles: set[tuple[int, int]],
) -> None:
    for y, row in enumerate(grid):
        for x, glyph in enumerate(row):
            if glyph != "." or (x, y) in protected_tiles:
                continue

            wall_neighbors = sum(
                1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if grid[y + dy][x + dx] == "#"
            )
            roll = randomizer.random()

            if wall_neighbors >= 2 and roll < 0.32:
                grid[y][x] = ","
            elif wall_neighbors == 1 and roll < 0.18:
                grid[y][x] = ";"
            elif wall_neighbors == 0 and roll < 0.08:
                grid[y][x] = randomizer.choice(tuple(sorted(DECORATIVE_FLOOR_GLYPHS)))


def generate_floor(run_seed: int, biome: dict, floor_number: int) -> FloorLayout:
    for attempt in range(12):
        floor_seed = derive_floor_seed(run_seed, floor_number, biome["id"], attempt)
        try:
            layout = _generate_candidate(floor_seed=floor_seed, biome=biome, floor_number=floor_number)
        except ValueError:
            continue
        if layout.validation["is_valid"]:
            return layout

    raise ValueError(f"Unable to generate a valid floor for biome {biome['id']} after repeated attempts")


def _generate_candidate(floor_seed: int, biome: dict, floor_number: int) -> FloorLayout:
    width = int(biome.get("floor_width", 19))
    height = int(biome.get("floor_height", 19))
    max_rooms = int(biome.get("max_rooms", 6))
    room_min_size = int(biome.get("room_min_size", 3))
    room_max_size = int(biome.get("room_max_size", 5))
    randomizer = random.Random(floor_seed)
    grid = [["#" for _ in range(width)] for _ in range(height)]

    rooms: list[RectRoom] = []
    for _ in range(max_rooms * 5):
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
            previous_x, previous_y = rooms[-1].center
            current_x, current_y = candidate.center
            if randomizer.random() < 0.5:
                carve_h_corridor(grid, previous_x, current_x, previous_y)
                carve_v_corridor(grid, previous_y, current_y, current_x)
            else:
                carve_v_corridor(grid, previous_y, current_y, previous_x)
                carve_h_corridor(grid, previous_x, current_x, current_y)
        rooms.append(candidate)

    if len(rooms) < 2:
        raise ValueError("Procgen candidate did not produce enough rooms")

    entry_x, entry_y = rooms[0].center
    exit_x, exit_y = rooms[-1].center
    protected_tiles = {(entry_x, entry_y), (exit_x, exit_y)}
    for origin_x, origin_y in ((entry_x, entry_y), (exit_x, exit_y)):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tile_x = origin_x + dx
            tile_y = origin_y + dy
            if 0 <= tile_x < width and 0 <= tile_y < height:
                protected_tiles.add((tile_x, tile_y))
    apply_floor_dressing(grid, randomizer, protected_tiles)
    grid[entry_y][entry_x] = "<"
    grid[exit_y][exit_x] = "."

    ascii_map = ["".join(row) for row in grid]
    validation = validate_floor(ascii_map, entry=(entry_x, entry_y), exit_point=(exit_x, exit_y))
    location_id = f"dungeon:{floor_seed}:{floor_number}"
    exits = [
        {
            "x": entry_x,
            "y": entry_y,
            "target_location_id": "dungeon_approach",
            "target_x": 4,
            "target_y": 5,
            "target_facing": "S",
            "message": biome["return_message"],
        }
    ]
    return FloorLayout(
        location_id=location_id,
        name=f"{biome['name']} F{floor_number}",
        description=biome["description"],
        biome_id=biome["id"],
        floor_number=floor_number,
        floor_seed=floor_seed,
        ascii_map=ascii_map,
        exits=exits,
        entry_x=entry_x,
        entry_y=entry_y,
        validation=validation,
    )
