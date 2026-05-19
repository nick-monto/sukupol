# MVP architecture

The current implementation uses a server-authoritative simulation model even though the project is single-player. The browser sends intents, the backend resolves movement, transitions, and encounter checks, and the browser renders the snapshot returned by the service.

## Why this shape

- It keeps procedural generation, persistence, and dialogue tools in one place.
- It prevents the future LLM path from becoming the rule source for gameplay.
- It makes save versioning and deterministic debugging easier once procgen expands.

## Prototype boundaries

- The backend owns map data, traversal snapshot generation, encounter checks, NPC proximity checks, and SQLite persistence.
- The frontend owns keyboard input, UI state, and visual presentation.
- Shared world content lives in version-controlled JSON and seeds the database on startup.

## Short-term next step

Replace the stub dialogue service with a real Agent Framework-backed local model adapter, but preserve the current rule boundary so the model can only describe or request actions, never perform state mutations without validated backend tools.

## Agent seam

- Agentized backend features should split into three layers: gameplay orchestration in the owning service, agent definitions that build prompts and agent names, and tool builders that expose validated read or write capabilities.
- Shared execution now lives in a reusable agent executor under `services/game-api/app/agents`, with a simple registry for agent builders and tool builders keyed by feature.
- NPC dialogue, journal summarization, combat parley, and quest text generation now consume that shared executor, but gameplay authority remains in their owning services and rule modules: models only generate phrasing or summaries, while validated backend code still decides state changes and outcomes.
- Future systems should add new registered agent and tool modules in that package instead of expanding `NpcDialogueService`, `combat.py`, `quests.py`, or embedding new tool closures directly inside service classes.
