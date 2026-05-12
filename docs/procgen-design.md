# Procgen design

The first procedural dungeon implementation keeps the location contract stable. Generated floors are persisted as serialized maps and exits in SQLite, then hydrated back into the in-memory location registry so the existing renderer and snapshot code can consume them without special client logic.

## Current rules

- One biome: Ancient Halls.
- Deterministic floor seed derived from run seed, floor number, biome id, and retry attempt.
- Room-and-corridor generation only.
- Cosmetic floor dressing now sprinkles walkable rubble and worn-stone glyphs across generated floors after carving, while preserving entry and exit readability.
- Validation checks entry reachability, exit reachability, and minimum walkable area.
- Returning to the approach uses a normal exit generated into the floor layout.

## Why layouts are persisted

Persisting the generated floor itself avoids replay drift if the algorithm changes later. The stored layout is the source of truth for an in-progress run, while the seed remains available for diagnostics and future reproducibility checks.
