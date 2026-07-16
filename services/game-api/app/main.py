from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .logging_config import configure_logging

from .agents import AgentExecutor, CombatParleyService, JournalService, QuestGenerationService
from .content import WorldContent, load_world_content
from .combat.encounters import maybe_start_encounter
from .db.connection import initialize_database
from .db.runs import ensure_player_profile, save_run_snapshot
from .dialogue import NpcDialogueService
from .game import create_run, perform_action, state_to_dict
from .models.requests import (
    ActionRequest,
    CombatRequest,
    RunScopedRequest,
    StartRunRequest,
    TalkRequest,
)
from .models.responses import (
    BootstrapResponse,
    HealthResponse,
    RunSnapshot,
)
from .quests import accept_offered_quest, decline_offered_quest
from .services.dungeon import handle_transition
from .services.run_state import (
    _run_locks,
    build_authoritative_snapshot,
    finalize_and_persist,
    get_run_state,
    resolve_combat_request,
    stream_talk_events,
    validate_npc_accessible,
    validate_nearby_quest,
)

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    load_env_file()
    world = load_world_content()
    initialize_database(world)
    app.state.world = world
    app.state.runs = {}
    app.state.agent_executor = AgentExecutor()
    app.state.journal = JournalService(executor=app.state.agent_executor)
    app.state.quest_generation = QuestGenerationService(executor=app.state.agent_executor)
    app.state.dialogue = NpcDialogueService(
        executor=app.state.agent_executor,
        journal_service=app.state.journal,
        quest_generation_service=app.state.quest_generation,
    )
    app.state.parley = CombatParleyService(executor=app.state.agent_executor)
    yield


app = FastAPI(title="Sukupol Game API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Catch unhandled RuntimeErrors from the simulation and return generic 500."""
    logger.exception("Internal simulation error")
    return JSONResponse(status_code=500, content={"detail": "Internal simulation error"})


def get_world() -> WorldContent:
    return app.state.world


# ── Route Handlers ──


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, str | None]:
    dialogue_status = app.state.dialogue.status()
    return {
        "status": "ok",
        "dialogue_mode": dialogue_status["mode"],
        "dialogue_provider_base_url": dialogue_status["provider_base_url"],
        "dialogue_provider_model": dialogue_status["provider_model"],
    }


@app.get("/api/bootstrap", response_model=BootstrapResponse)
def bootstrap() -> dict:
    world = get_world()
    return {
        "title": "Sukupol",
        "dialogue_mode": app.state.dialogue.mode,
        "dungeon_biomes": [
            {"id": b["id"], "name": b["name"], "procgen_version": b["procgen_version"]}
            for b in world.dungeon_biomes.values()
        ],
        "locations": [
            {"id": loc["id"], "name": loc["name"]}
            for loc in world.locations.values()
        ],
    }


@app.post("/api/runs", response_model=RunSnapshot)
def start_run(request: StartRunRequest) -> dict:
    world = get_world()
    state = create_run(world, request.player_name.strip())
    logger.info("Run started", extra={"run_id": state.id, "player_name": state.player_name})
    ensure_player_profile(state.player_id, state.player_name)
    app.state.runs[state.id] = state
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state, world)


@app.post("/api/runs/{run_id}/actions", response_model=RunSnapshot)
def act(run_id: str, request: ActionRequest) -> dict:
    world = get_world()
    state = get_run_state(run_id, app.state.runs, world)
    if state.run_result is not None:
        raise HTTPException(status_code=400, detail="Run is already complete")
    prev = (state.steps_taken, state.location_id, state.x, state.y)
    perform_action(world, state, request.action, transition_handler=handle_transition)
    moved = (state.steps_taken, state.location_id, state.x, state.y) != prev
    maybe_start_encounter(world, state, moved=moved)
    (app.state.dialogue.finalize_all_active_visits if state.in_combat else app.state.dialogue.finalize_departed_visits)(world, state)
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state, world)


@app.post("/api/runs/{run_id}/combat", response_model=RunSnapshot)
def combat(run_id: str, request: CombatRequest) -> dict:
    world = get_world()
    state = get_run_state(run_id, app.state.runs, world)
    with _run_locks[run_id]:
        return resolve_combat_request(state, request.action, world, app.state.parley, app.state.dialogue, message=request.message)


@app.post("/api/runs/{run_id}/extract", response_model=RunSnapshot)
def extract(run_id: str) -> dict:
    world = get_world()
    state = get_run_state(run_id, app.state.runs, world)
    if state.in_combat:
        raise HTTPException(status_code=400, detail="Cannot extract during combat")
    if state.location_id != "town_square":
        raise HTTPException(status_code=400, detail="You can only extract from town")
    if state.run_result is not None:
        raise HTTPException(status_code=400, detail="Run is already complete")
    finalize_and_persist(state, "extraction", world, app.state.dialogue)
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state, world)


@app.post("/api/npcs/{npc_id}/talk", response_model=RunSnapshot)
def talk_to_npc(npc_id: str, request: TalkRequest) -> dict:
    world = get_world()
    state = get_run_state(request.run_id, app.state.runs, world)
    validate_npc_accessible(world, state, npc_id)
    reply = app.state.dialogue.talk(world, state, npc_id, request.message)
    save_run_snapshot(state_to_dict(state))
    snapshot = build_authoritative_snapshot(state, world)
    snapshot["dialogue"] = {"npc_id": reply.npc_id, "npc_name": reply.npc_name, "text": reply.text, "source": reply.source}
    return snapshot


@app.post("/api/npcs/{npc_id}/talk/stream")
async def stream_talk_to_npc(npc_id: str, request: TalkRequest) -> StreamingResponse:
    world = get_world()
    state = get_run_state(request.run_id, app.state.runs, world)
    validate_npc_accessible(world, state, npc_id)
    return StreamingResponse(
        stream_talk_events(world, state, npc_id, request.message, app.state.dialogue),
        media_type="application/x-ndjson",
    )


@app.post("/api/npcs/{npc_id}/leave", response_model=RunSnapshot)
def leave_npc(npc_id: str, request: RunScopedRequest) -> dict:
    world = get_world()
    state = get_run_state(request.run_id, app.state.runs, world)
    if state.run_result is not None:
        raise HTTPException(status_code=400, detail="Run is already complete")
    app.state.dialogue.leave(world, state, npc_id)
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state, world)


@app.post("/api/quests/{quest_id}/accept", response_model=RunSnapshot)
def accept_quest(quest_id: str, request: RunScopedRequest) -> dict:
    world = get_world()
    state = get_run_state(request.run_id, app.state.runs, world)
    validate_nearby_quest(world, state, quest_id)
    try:
        quest = accept_offered_quest(world, state, quest_id, quest_generation_service=app.state.quest_generation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_run_snapshot(state_to_dict(state))
    snapshot = build_authoritative_snapshot(state, world)
    snapshot["dialogue"] = {"npc_id": quest["offered_by_npc_id"], "npc_name": quest["offered_by_npc_name"], "text": f"{quest['offered_by_npc_name']}: {quest['response_text']}", "source": "quest"}
    return snapshot


@app.post("/api/quests/{quest_id}/decline", response_model=RunSnapshot)
def decline_quest(quest_id: str, request: RunScopedRequest) -> dict:
    world = get_world()
    state = get_run_state(request.run_id, app.state.runs, world)
    validate_nearby_quest(world, state, quest_id)
    try:
        quest = decline_offered_quest(world, state, quest_id, quest_generation_service=app.state.quest_generation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_run_snapshot(state_to_dict(state))
    snapshot = build_authoritative_snapshot(state, world)
    snapshot["dialogue"] = {"npc_id": quest["offered_by_npc_id"], "npc_name": quest["offered_by_npc_name"], "text": f"{quest['offered_by_npc_name']}: {quest['response_text']}", "source": "quest"}
    return snapshot
