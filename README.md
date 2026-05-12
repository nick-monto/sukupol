# sukupol

Sukupol is a browser-based ASCII rogue-lite with map-based traversal, an overworld, seeded dungeons, and database-backed content and progression. The current implementation establishes a server-authoritative Python backend, a browser client, shared content and schema packages, and a dialogue integration seam for local LLM-backed NPCs.

## Current shape

- `services/game-api`: authoritative FastAPI service for simulation, procgen bootstrap, persistence, and dialogue orchestration.
- `apps/web`: minimal Vite + TypeScript client for ASCII rendering, input, and NPC interaction.
- `packages/content`: version-controlled world content and seeded NPC data.
- `packages/schema`: SQLite schema used by the backend.
- `docs`: design notes for the MVP implementation path.

## What works now

- Start a new run from the browser.
- Render a primary traversal map returned by the backend.
- Move with cardinal directions across towns, the overworld, caves, and dungeon floors.
- Enter a deterministic, procedurally generated first dungeon floor that is persisted in SQLite per run.
- Trigger random encounters while traveling through encounter-enabled areas.
- Talk to nearby NPCs through a dialogue service abstraction with deterministic fallback responses.
- Persist run snapshots and dialogue summaries into SQLite.

## ASCII asset contract

- Seeded maps currently support six glyphs: `#` wall, `.` floor, `>` forward descent or transition, `<` return or ascent, `,` loose rubble, and `;` moss or worn floor dressing.
- The decorative floor glyphs are intentionally walkable. They enrich both map displays and static content without changing collision rules.
- Any non-wall gameplay entity in seeded content must be placed on a walkable tile. The backend now validates player spawn points, NPC positions, exits, and map width consistency during content load.
- NPC and enemy portraits remain free-form multi-line ASCII art, but the current content is authored as compact 4-line silhouettes to fit the existing sidebar and combat layouts cleanly.
- Decorative glyph expansion should be treated as a renderer and simulation change, not a content-only edit, because map tone mapping and walkability are both explicit in code.

## Map snapshot contract

- The backend remains authoritative for traversal map layout. The browser renders `map_view` as the main surface and `map_metadata` as the primary structured rendering contract.
- Encounter safety, location type, player position, and other traversal semantics remain backend-owned snapshot data. If a new environment type needs special treatment, add it to backend metadata first and let the client style it second.

## Local development

### Backend

```bash
cd services/game-api
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

The backend listens on `http://127.0.0.1:8000` by default and will create `services/game-api/data/sukupol.db` on first startup.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

The web client expects the API at `http://127.0.0.1:8000`. Override it with `VITE_API_BASE` if needed.

## Dialogue integration seam

The current NPC dialogue implementation is intentionally conservative. The backend exposes a single dialogue service with a deterministic fallback mode and an environment-controlled seam for future Microsoft Agent Framework integration.

- Default mode: deterministic stub responses grounded in NPC metadata and recent conversation summary.
- Future mode: local model hosted next to the backend, with Agent Framework sessions and validated game tools.

Set `SUKUPOL_DIALOGUE_MODE=agent-framework` when that path is implemented and wired to a local provider.

## Next implementation targets

1. Replace the fallback dialogue path with Agent Framework plus a local chat client.
2. Expand seeded content, encounter tables, and biome variety across the overworld and site network.
3. Move from seeded snapshots to richer run persistence and meta-progression.
4. Continue cleaning up map-era naming and presentation layers in the client.

