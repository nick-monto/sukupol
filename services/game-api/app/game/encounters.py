from __future__ import annotations

from typing import Any

from ..content import WorldContent


def encounter_context_for_location(world: WorldContent, location: dict[str, Any]) -> dict[str, Any]:
    biome_id = location.get("encounter_biome_id") or location.get("biome_id")
    biome = world.dungeon_biomes.get(biome_id) if biome_id else None
    location_type = str(location.get("location_type", "site")).strip().lower() or "site"
    explicit_enabled = location.get("encounter_enabled")
    enabled = bool(explicit_enabled) if explicit_enabled is not None else location_type not in {"town", "city"}
    floor_number = int(location.get("encounter_floor", location.get("floor_number", 0) or 0))
    encounter_rate = int(location.get("encounter_rate", biome.get("encounter_rate", 0) if biome else 0))
    return {
        "enabled": enabled and biome_id is not None and encounter_rate > 0,
        "biome_id": biome_id,
        "floor_number": floor_number,
        "encounter_rate": encounter_rate,
        "location_type": location_type,
    }
