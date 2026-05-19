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
- Enter deterministic, procedurally generated first dungeon floors from multiple biome entrances, each persisted in SQLite per run.
- Trigger random encounters while traveling through encounter-enabled areas.
- Talk to nearby NPCs through a dialogue service abstraction with deterministic fallback responses.
- Receive dungeon-linked fetch quests from NPC conversations, accept or decline them from the dialogue panel, and track recovery progress in the client. Each NPC now draws from a seeded pool of fetch variants rather than a single fixed errand, and offers bias toward the biome implied by the current conversation, nearby route context, and that NPC's own default concerns.
- Persist run snapshots and dialogue summaries into SQLite.

## ASCII asset contract

- Seeded maps support four gameplay glyphs: `#` wall, `.` floor, `∩` dungeon entrance or descent, and `∪` return or ascent.
- Adjacent surface-zone transitions should read as gaps on the map edge, authored as walkable floor openings with matching exit nodes rather than standalone transition punctuation.
- Player facing remains arrow-based (`^`, `>`, `v`, `<`), so seeded traversal glyphs should avoid those shapes to keep navigation legible.
- Floor variety now comes from backend-owned map metadata and renderer underlays rather than extra walkable punctuation authored into the map itself.
- Any non-wall gameplay entity in seeded content must be placed on a walkable tile. The backend validates player spawn points, NPC positions, exits, and map width consistency during content load.
- NPC and enemy portraits remain free-form multi-line ASCII art, but the current content is authored as compact 4-line silhouettes to fit the existing sidebar and combat layouts cleanly.
- If a biome needs richer floor treatment, add structured metadata or renderer logic rather than inventing more walkable map glyphs.

## Map snapshot contract

- The backend remains authoritative for traversal map layout. The browser renders `map_view` as the main surface and `map_metadata` as the primary structured rendering contract.
- Encounter safety, location type, player position, and other traversal semantics remain backend-owned snapshot data. If a new environment type needs special treatment, add it to backend metadata first and let the client style it second.

## Local development

### Full stack

```bash
./launch-dev.sh
```

The root launcher bootstraps both app halves for local development: it installs `apps/web` dependencies on first run, creates `services/game-api/.venv` if needed, installs backend dependencies, starts the API on port `8000`, and starts the Vite client on port `5173`. Stop both with `Ctrl+C`.

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
./launch-web.sh
```

The web client expects the API at `http://127.0.0.1:8000`. Override it with `VITE_API_BASE` if needed.

`./launch-web.sh` is kept as a compatibility wrapper and now delegates to the full-stack launcher above.

## Dialogue integration seam

The current NPC dialogue implementation is intentionally conservative. The backend exposes a single dialogue service with a deterministic fallback mode and an environment-controlled seam for future Microsoft Agent Framework integration.

- Default mode: deterministic stub responses grounded in NPC metadata and recent conversation summary.
- NPC conversations can now surface backend-authored fetch quest offers tied to dungeon biomes, with explicit accept and decline actions in the client.
- Future mode: local model hosted next to the backend, with Agent Framework sessions and validated game tools.

Set `SUKUPOL_DIALOGUE_MODE=agent-framework` when that path is implemented and wired to a local provider.

### Local llama.cpp server

If you want to run NPC dialogue against a local `llama.cpp` build, start an OpenAI-compatible `llama-server` instance and point the backend at it.

Build `llama.cpp` locally if needed:

```bash
git clone https://github.com/TheTom/llama-cpp-turboquant
cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DGGML_NATIVE=ON -DCMAKE_CUDA_COMPILER:PATH=/usr/local/cuda/bin/nvcc
cmake --build build --config Release -j$(nproc)
```

Launch the server from the root of your local `llama.cpp` checkout, or replace `./build/bin/llama-server` with an absolute path:
```bash
chmod u+x LLM_BACKEND_LAUNCH_CONFIG.sh
./LLM_BACKEND_LAUNCH_CONFIG.sh
```

Then start the game API with the local-LLM settings:

```bash
cd services/game-api
source .venv/bin/activate
export SUKUPOL_DIALOGUE_MODE=agent-framework
export SUKUPOL_OPENAI_BASE_URL=http://127.0.0.1:8033
uvicorn app.main:app --reload
```

Quick smoke test for the LLM server:

```bash
curl http://127.0.0.1:8033/v1/models
```