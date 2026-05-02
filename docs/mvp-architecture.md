# MVP architecture

The current implementation uses a server-authoritative simulation model even though the project is single-player. The browser sends intents, the backend resolves movement and transitions, and the browser renders the snapshot returned by the service.

## Why this shape

- It keeps procedural generation, persistence, and dialogue tools in one place.
- It prevents the future LLM path from becoming the rule source for gameplay.
- It makes save versioning and deterministic debugging easier once procgen expands.

## Prototype boundaries

- The backend owns map data, first-person viewport generation, NPC proximity checks, and SQLite persistence.
- The frontend owns keyboard input, UI state, and visual presentation.
- Shared world content lives in version-controlled JSON and seeds the database on startup.

## Short-term next step

Replace the stub dialogue service with a real Agent Framework-backed local model adapter, but preserve the current rule boundary so the model can only describe or request actions, never perform state mutations without validated backend tools.
