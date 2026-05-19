from __future__ import annotations

from collections import deque

from ..content import WALKABLE_MAP_GLYPHS


def validate_floor(
    ascii_map: list[str],
    entry: tuple[int, int],
    exit_point: tuple[int, int],
    *,
    features: list[dict] | None = None,
    reserved_tiles: set[tuple[int, int]] | None = None,
) -> dict:
    height = len(ascii_map)
    width = len(ascii_map[0]) if height else 0
    walkable = WALKABLE_MAP_GLYPHS
    reserved = reserved_tiles or set()

    def neighbors(x: int, y: int) -> list[tuple[int, int]]:
        points: list[tuple[int, int]] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = x + dx
            ny = y + dy
            if 0 <= nx < width and 0 <= ny < height and ascii_map[ny][nx] in walkable:
                points.append((nx, ny))
        return points

    visited: set[tuple[int, int]] = set()
    queue = deque([entry])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(neighbors(*current))

    walkable_tiles = sum(1 for row in ascii_map for cell in row if cell in walkable)
    feature_errors: list[str] = []
    seen_feature_positions: set[tuple[int, int]] = set()
    for feature in features or []:
        x = int(feature.get("x", -1))
        y = int(feature.get("y", -1))
        kind = feature.get("kind", "unknown")
        if not (0 <= x < width and 0 <= y < height):
            feature_errors.append(f"Feature {kind} is out of bounds at ({x}, {y})")
            continue
        if ascii_map[y][x] not in walkable:
            feature_errors.append(f"Feature {kind} must be placed on a walkable tile")
            continue
        if (x, y) in reserved:
            feature_errors.append(f"Feature {kind} overlaps a reserved tile at ({x}, {y})")
            continue
        if (x, y) in seen_feature_positions:
            feature_errors.append(f"Multiple features share tile ({x}, {y})")
            continue
        if (x, y) not in visited:
            feature_errors.append(f"Feature {kind} is not reachable from the floor entry")
            continue
        seen_feature_positions.add((x, y))

    return {
        "is_valid": exit_point in visited and entry in visited and walkable_tiles >= 20 and not feature_errors,
        "reachable_tiles": len(visited),
        "walkable_tiles": walkable_tiles,
        "entry_reachable": entry in visited,
        "exit_reachable": exit_point in visited,
        "feature_count": len(features or []),
        "feature_errors": feature_errors,
    }
