# Procgen design

The first procedural dungeon implementation keeps the location contract stable. Generated floors are persisted as serialized maps and exits in SQLite, then hydrated back into the in-memory location registry so the existing renderer and snapshot code can consume them without special client logic.

## Current rules

- Two reachable generated biomes: Ancient Halls and Sunken Archive.
- Deterministic floor seed derived from run seed, floor number, biome id, and retry attempt.
- Room-and-corridor generation remains the base, but active biomes now use profile-driven connection rules, loop budgets, and depth scaling rather than a single rigid room chain.
- Cosmetic floor dressing is now renderer-driven: generated floors stay authored as plain walkable floor tiles, while backend metadata marks varied surface treatments for the client to paint.
- Biomes can now author floor-name pools, description templates, return-exit targets, generation settings, depth progression, and landmark or hazard feature pools.
- Generated floors persist structured procgen metadata alongside the ASCII layout, including generation summary data and placed landmarks or hazards.
- Validation checks entry reachability, exit reachability, minimum walkable area, and that generated features stay on reachable non-reserved tiles.
- Returning from a generated floor uses a normal exit generated from biome-authored return metadata.

## Generation stages

Each floor now goes through three deterministic stages:

1. Resolve biome profile and depth-scaled settings.
2. Generate the structural layout using room placement, branch-biased corridor connections, and optional loop corridors.
3. Place landmark and hazard anchors on valid walkable tiles, then persist the resulting feature metadata with the floor.

The ASCII map remains the authoritative movement surface. Procgen features are supplemental metadata used for biome identity, future gameplay hooks, and richer renderer variants.

## Why layouts are persisted

Persisting the generated floor itself avoids replay drift if the algorithm changes later. The stored layout and procgen metadata are the source of truth for an in-progress run, while the seed remains available for diagnostics and future reproducibility checks.
