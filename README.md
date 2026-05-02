# sukupol

Sukupol is a browser-based first-person ASCII rogue-lite dungeon crawler with an overworld, seeded dungeons, and database-backed content and progression. The first implementation pass in this repository establishes a server-authoritative Python backend, a minimal browser client, shared content and schema packages, and a dialogue integration seam for local LLM-backed NPCs.

## Current shape

- `services/game-api`: authoritative FastAPI service for simulation, procgen bootstrap, persistence, and dialogue orchestration.
- `apps/web`: minimal Vite + TypeScript client for ASCII rendering, input, and NPC interaction.
- `packages/content`: version-controlled world content and seeded NPC data.
- `packages/schema`: SQLite schema used by the backend.
- `docs`: design notes for the MVP implementation path.

## What works now

- Start a new run from the browser.
- Render a first-person ASCII viewport returned by the backend.
- Turn left and right, move forward and backward, and transition between seeded locations.
- Enter a deterministic, procedurally generated first dungeon floor that is persisted in SQLite per run.
- See a development minimap while the renderer is still early.
- Talk to nearby NPCs through a dialogue service abstraction with deterministic fallback responses.
- Persist run snapshots and dialogue summaries into SQLite.

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
2. Expand seeded content into a real overworld plus procedural dungeon generation.
3. Move from seeded snapshots to richer run persistence and meta-progression.
4. Replace the development minimap-heavy client with a stronger first-person renderer.

