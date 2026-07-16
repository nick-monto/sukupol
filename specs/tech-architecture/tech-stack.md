# Tech Stack — Sukupol

## Backend

- **Runtime:** Python 3.11+
- **Framework:** FastAPI
- **Build:** Hatchling
- **Database:** SQLite (schema in packages/schema/)
- **Testing:** pytest

## Frontend

- **Runtime:** Node.js
- **Framework:** Vite + TypeScript / React
- **Testing:** Vitest

## Shared

- `packages/content` — Version-controlled world content and NPC data
- `packages/schema` — SQLite schema definition

## Architecture Pattern

Browser sends intents; backend resolves state changes,
returns snapshots for rendering.
