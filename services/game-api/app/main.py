from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .content import WorldContent, load_world_content
from .combat import maybe_start_encounter, resolve_turn
from .db import (
    create_dungeon_instance,
    ensure_player_profile,
    initialize_database,
    load_dungeon_floor,
    load_dungeon_floor_for_instance,
    load_run_snapshot,
    save_run_outcome,
    save_run_snapshot,
    persist_dungeon_floor,
    upsert_player_progression,
)
from .dialogue import NpcDialogueService
from .game import RunState, build_snapshot, create_run, perform_action, state_from_dict, state_to_dict
from .progression import finalize_run
from .procgen.generator import generate_floor


class StartRunRequest(BaseModel):
    player_name: str = Field(default="Wayfarer", min_length=1, max_length=32)


class ActionRequest(BaseModel):
    action: str


class TalkRequest(BaseModel):
    run_id: str
    message: str = Field(min_length=1, max_length=500)


class RunScopedRequest(BaseModel):
    run_id: str


class CombatRequest(BaseModel):
    action: str


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
    load_env_file()
    world = load_world_content()
    initialize_database(world)
    app.state.world = world
    app.state.runs = {}
    app.state.dialogue = NpcDialogueService()
    yield


app = FastAPI(title="Sukupol Game API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_world() -> WorldContent:
    return app.state.world


def hydrate_dungeon_location(location_id: str) -> dict | None:
    world = get_world()
    if location_id in world.locations:
        return world.locations[location_id]

    floor = load_dungeon_floor(location_id)
    if floor is not None:
        world.locations[location_id] = floor
    return floor


def get_run_state(run_id: str) -> RunState:
    cached = app.state.runs.get(run_id)
    if cached is not None:
        return cached

    snapshot = load_run_snapshot(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Run not found")

    state = state_from_dict(snapshot)
    if state.dungeon_instance_id and state.location_id not in app.state.world.locations:
        hydrate_dungeon_location(state.location_id)
    app.state.runs[run_id] = state
    return state


def ensure_generated_floor(state: RunState, biome_id: str, floor_number: int) -> dict:
    world = get_world()
    biome = world.dungeon_biomes[biome_id]

    if state.dungeon_instance_id is None:
        instance = create_dungeon_instance(
            run_id=state.id,
            biome_id=biome_id,
            run_seed=state.run_seed,
            procgen_version=biome["procgen_version"],
        )
        state.dungeon_instance_id = instance["id"]
        state.procgen_version = instance["procgen_version"]

    floor = load_dungeon_floor_for_instance(state.dungeon_instance_id, floor_number)
    if floor is None:
        layout = generate_floor(
            run_seed=state.run_seed,
            biome=biome,
            floor_number=floor_number,
        )
        persist_dungeon_floor(
            dungeon_instance_id=state.dungeon_instance_id,
            biome_id=biome_id,
            floor_number=floor_number,
            floor_seed=layout.floor_seed,
            location_id=layout.location_id,
            name=layout.name,
            description=layout.description,
            ascii_map=layout.ascii_map,
            exits=layout.exits,
            entry_x=layout.entry_x,
            entry_y=layout.entry_y,
            validation=layout.validation,
        )
        floor = load_dungeon_floor(layout.location_id)

    if floor is None:
        raise HTTPException(status_code=500, detail="Failed to load generated floor")

    world.locations[floor["id"]] = floor
    return floor


def handle_transition(state: RunState, exit_node: dict) -> bool:
    if exit_node.get("transition") != "generated_dungeon":
        return False

    biome_id = exit_node["biome_id"]
    floor_number = int(exit_node.get("floor_number", 1))
    floor = ensure_generated_floor(state, biome_id=biome_id, floor_number=floor_number)
    state.location_id = floor["id"]
    state.x = floor["entry_x"]
    state.y = floor["entry_y"]
    state.facing = exit_node.get("target_facing", "N")
    state.floor_number = floor_number
    state.run_depth = max(state.run_depth, floor_number)
    state.message = exit_node["message"]
    return True


def finalize_and_persist(state: RunState, result: str) -> None:
    app.state.dialogue.finalize_all_active_visits(get_world(), state)
    outcome = finalize_run(state, result=result)
    save_run_outcome(
        run_id=state.id,
        player_id=state.player_id,
        result=result,
        depth_reached=outcome["depth_reached"],
        enemies_defeated=outcome["enemies_defeated"],
        gold_earned=outcome["gold_earned"],
        items_json=outcome["items_json"],
    )
    state.progression = upsert_player_progression(
        player_id=state.player_id,
        result=result,
        depth_reached=outcome["depth_reached"],
    )


def build_authoritative_snapshot(state: RunState) -> dict:
    return build_snapshot(get_world(), state)


@app.get("/api/health")
def health() -> dict[str, str | None]:
    dialogue_status = app.state.dialogue.status()
    return {
        "status": "ok",
        "dialogue_mode": dialogue_status["mode"],
        "dialogue_provider_base_url": dialogue_status["provider_base_url"],
        "dialogue_provider_model": dialogue_status["provider_model"],
    }


@app.get("/api/bootstrap")
def bootstrap() -> dict:
    world = get_world()
    return {
        "title": "Sukupol",
        "dialogue_mode": app.state.dialogue.mode,
        "dungeon_biomes": [
            {
                "id": biome["id"],
                "name": biome["name"],
                "procgen_version": biome["procgen_version"],
            }
            for biome in world.dungeon_biomes.values()
        ],
        "locations": [
            {
                "id": location["id"],
                "name": location["name"],
            }
            for location in world.locations.values()
        ],
    }


@app.post("/api/runs")
def start_run(request: StartRunRequest) -> dict:
    world = get_world()
    state = create_run(world, request.player_name.strip())
    ensure_player_profile(state.player_id, state.player_name)
    app.state.runs[state.id] = state
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state)


@app.post("/api/runs/{run_id}/actions")
def act(run_id: str, request: ActionRequest) -> dict:
    world = get_world()
    state = get_run_state(run_id)
    if state.run_result is not None:
        raise HTTPException(status_code=400, detail="Run is already complete")
    previous_location_id = state.location_id
    previous_x = state.x
    previous_y = state.y
    previous_steps = state.steps_taken
    perform_action(world, state, request.action, transition_handler=handle_transition)
    moved = (
        state.steps_taken != previous_steps
        or state.location_id != previous_location_id
        or state.x != previous_x
        or state.y != previous_y
    )
    maybe_start_encounter(world, state, moved=moved)
    if state.in_combat:
        app.state.dialogue.finalize_all_active_visits(world, state)
    else:
        app.state.dialogue.finalize_departed_visits(world, state)
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state)


@app.post("/api/runs/{run_id}/combat")
def combat(run_id: str, request: CombatRequest) -> dict:
    world = get_world()
    state = get_run_state(run_id)
    if not state.in_combat:
        raise HTTPException(status_code=400, detail="No active combat")

    resolve_turn(world, state, request.action)
    if state.run_result == "death":
        finalize_and_persist(state, "death")
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state)


@app.post("/api/runs/{run_id}/extract")
def extract(run_id: str) -> dict:
    world = get_world()
    state = get_run_state(run_id)
    if state.in_combat:
        raise HTTPException(status_code=400, detail="Cannot extract during combat")
    if state.location_id != "town_square":
        raise HTTPException(status_code=400, detail="You can only extract from town")
    if state.run_result is not None:
        raise HTTPException(status_code=400, detail="Run is already complete")

    finalize_and_persist(state, "extraction")
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state)


@app.post("/api/npcs/{npc_id}/talk")
def talk_to_npc(npc_id: str, request: TalkRequest) -> dict:
    world = get_world()
    if npc_id not in world.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    state = get_run_state(request.run_id)
    if state.in_combat:
        raise HTTPException(status_code=400, detail="You cannot talk during combat")
    nearby_ids = {npc["id"] for npc in build_snapshot(world, state)["nearby_npcs"]}
    if npc_id not in nearby_ids:
        raise HTTPException(status_code=400, detail="NPC is not nearby")

    reply = app.state.dialogue.talk(world, state, npc_id, request.message)
    save_run_snapshot(state_to_dict(state))
    snapshot = build_authoritative_snapshot(state)
    snapshot["dialogue"] = {
        "npc_id": reply.npc_id,
        "npc_name": reply.npc_name,
        "text": reply.text,
        "source": reply.source,
    }
    return snapshot


@app.post("/api/npcs/{npc_id}/talk/stream")
async def stream_talk_to_npc(npc_id: str, request: TalkRequest) -> StreamingResponse:
    world = get_world()
    if npc_id not in world.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    state = get_run_state(request.run_id)
    if state.in_combat:
        raise HTTPException(status_code=400, detail="You cannot talk during combat")
    nearby_ids = {npc["id"] for npc in build_snapshot(world, state)["nearby_npcs"]}
    if npc_id not in nearby_ids:
        raise HTTPException(status_code=400, detail="NPC is not nearby")

    async def stream_events():
        try:
            async for event in app.state.dialogue.stream_talk(world, state, npc_id, request.message):
                if event["type"] == "complete":
                    reply = event["reply"]
                    save_run_snapshot(state_to_dict(state))
                    snapshot = build_authoritative_snapshot(state)
                    snapshot["dialogue"] = {
                        "npc_id": reply["npc_id"],
                        "npc_name": reply["npc_name"],
                        "text": reply["text"],
                        "source": reply["source"],
                    }
                    yield json.dumps({"type": "snapshot", "snapshot": snapshot}) + "\n"
                    continue
                yield json.dumps(event) + "\n"
        except RuntimeError as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}) + "\n"

    return StreamingResponse(stream_events(), media_type="application/x-ndjson")


@app.post("/api/npcs/{npc_id}/leave")
def leave_npc(npc_id: str, request: RunScopedRequest) -> dict:
    world = get_world()
    if npc_id not in world.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    state = get_run_state(request.run_id)
    if state.run_result is not None:
        raise HTTPException(status_code=400, detail="Run is already complete")

    app.state.dialogue.leave(world, state, npc_id)
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state)
