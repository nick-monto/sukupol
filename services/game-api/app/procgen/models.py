from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RectRoom:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(frozen=True)
class FloorLayout:
    location_id: str
    name: str
    description: str
    biome_id: str
    floor_number: int
    floor_seed: int
    ascii_map: list[str]
    exits: list[dict]
    entry_x: int
    entry_y: int
    features: list[dict]
    generation: dict
    validation: dict
