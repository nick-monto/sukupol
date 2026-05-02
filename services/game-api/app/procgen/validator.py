from __future__ import annotations

from collections import deque


def validate_floor(ascii_map: list[str], entry: tuple[int, int], exit_point: tuple[int, int]) -> dict:
    height = len(ascii_map)
    width = len(ascii_map[0]) if height else 0
    walkable = {".", "<"}

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
    return {
        "is_valid": exit_point in visited and entry in visited and walkable_tiles >= 20,
        "reachable_tiles": len(visited),
        "walkable_tiles": walkable_tiles,
        "entry_reachable": entry in visited,
        "exit_reachable": exit_point in visited,
    }
