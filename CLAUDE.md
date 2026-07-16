# Sukupol — Claude Code

Read CONVENTIONS.md before any GitHub or git operation.

## Project

Sukupol is a browser-based ASCII rogue-lite with map-based traversal,
seeded dungeons, and database-backed content and progression.

Stack:
Python / FastAPI / SQLite (backend)
TypeScript / Vite / React (frontend)

## Commands

| Action | Command |
| -------- | --------- |
| Run backend | `uvicorn app.main:app --reload` (in services/game-api/) |
| Run frontend | `npm run dev` (in apps/web/) |
| Test backend | `pytest` (in services/game-api/) |
| Test frontend | `npm run test` (in apps/web/) |
| Build frontend | `npm run build` (in apps/web/) |

## Architecture

Browser sends intents; FastAPI resolves movement/transitions/encounters
and returns snapshots for rendering. Shared content/schema packages
live in packages/. SQLite persists runs and dialogue.

## Conventions

- All planning output goes to specs/ at project root.
- Follow bigpowers lifecycle skills for all work.
- One thing per function, one responsibility per module. Files under 300 lines.
- Tests must cover edge cases; every story needs runnable verify commands.
- No magic strings or numbers — extract named constants.
- Remove dead code, don't comment it out.

## Never

- Do not bypass the bigpowers workflow.
Route through survey-context, plan-work, develop-tdd.
- Do not write code without a plan in specs/.
- Do not push directly to main/master except via land-branch.sh.
