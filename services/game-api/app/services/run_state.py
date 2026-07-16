from __future__ import annotations

from collections import defaultdict
import json
import logging
import threading
from typing import Any

from ..db.quests import load_player_quest
from ..db.rows import QuestRow
from fastapi import HTTPException
from ..combat.turn import resolve_turn
from ..content import WorldContent
from ..db.runs import (
    load_run_snapshot,
    save_run_outcome,
    save_run_snapshot,
    upsert_player_progression,
)
from ..dialogue import NpcDialogueService
from ..game import RunState, build_snapshot, state_from_dict, state_to_dict
from ..progression import finalize_run

logger = logging.getLogger(__name__)

# Per-run concurrency guard: prevents lost updates when two rapid
# combat POSTs read stale state.
_run_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)


def get_run_state(
    run_id: str, runs_cache: dict[str, Any], world: WorldContent,
) -> RunState:
    cached = runs_cache.get(run_id)
    if cached is not None:
        return cached
    snapshot = load_run_snapshot(run_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Run not found")
    state = state_from_dict(snapshot)
    if state.dungeon_instance_id and state.location_id not in world.locations:
        from .dungeon import hydrate_dungeon_location  # noqa: PLC0415

        hydrate_dungeon_location(state.location_id, world)
    runs_cache[run_id] = state
    return state


def finalize_and_persist(
    state: RunState,
    result: str,
    world: WorldContent,
    dialogue_svc: NpcDialogueService,
) -> None:
    logger.info("Run finalized", extra={"run_id": state.id, "result": result})
    dialogue_svc.finalize_all_active_visits(world, state)
    outcome = finalize_run(state, result=result)
    save_run_outcome(
        run_id=state.id, player_id=state.player_id, result=result,
        depth_reached=outcome["depth_reached"],
        enemies_defeated=outcome["enemies_defeated"],
        gold_earned=outcome["gold_earned"],
        items_json=outcome["items_json"],
    )
    _run_locks.pop(state.id, None)
    from dataclasses import asdict
    state.progression = asdict(upsert_player_progression(
        player_id=state.player_id, result=result, depth_reached=outcome["depth_reached"],
    ))

def build_authoritative_snapshot(
    state: RunState, world: WorldContent,
) -> dict[str, Any]:
    """Build a complete authoritative snapshot of the current run state."""
    return build_snapshot(world, state)


def resolve_combat_request(
    state: RunState,
    action: str,
    world: WorldContent,
    parley_service: Any,
    dialogue_svc: NpcDialogueService,
    message: str | None = None,
) -> dict[str, Any]:
    """Process a combat action and return the updated authoritative snapshot."""
    logger.info("Combat action resolved", extra={
        "run_id": state.id, "action": action,
    })
    if not state.in_combat:
        raise HTTPException(status_code=400, detail="No active combat")

    resolve_turn(world, state, action, message=message, parley_service=parley_service)
    if state.run_result == "death":
        finalize_and_persist(state, "death", world, dialogue_svc)
    save_run_snapshot(state_to_dict(state))
    return build_authoritative_snapshot(state, world)



async def stream_talk_events(
    world: WorldContent,
    state: RunState,
    npc_id: str,
    message: str,
    dialogue_svc: NpcDialogueService,
):
    try:
        async for event in dialogue_svc.stream_talk(world, state, npc_id, message):
            if event["type"] == "complete":
                reply = event["reply"]
                save_run_snapshot(state_to_dict(state))
                snapshot = build_authoritative_snapshot(state, world)
                snapshot["dialogue"] = {"npc_id": reply["npc_id"], "npc_name": reply["npc_name"], "text": reply["text"], "source": reply["source"]}
                yield json.dumps({"type": "snapshot", "snapshot": snapshot}) + "\n"
                continue
            yield json.dumps(event) + "\n"
    except RuntimeError as exc:
        logger.exception("stream_talk failed")
        yield json.dumps({"type": "error", "detail": "Dialogue unavailable"}) + "\n"


def validate_npc_accessible(world: WorldContent, state: RunState, npc_id: str) -> None:
    """Check NPC exists and is nearby for conversation."""
    if npc_id not in world.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")
    if state.in_combat:
        raise HTTPException(status_code=400, detail="You cannot talk during combat")
    nearby_ids = {npc["id"] for npc in build_snapshot(world, state)["nearby_npcs"]}
    if npc_id not in nearby_ids:
        raise HTTPException(status_code=400, detail="NPC is not nearby")


def validate_nearby_quest(world: WorldContent, state: RunState, quest_id: str) -> QuestRow:
    """Validate quest exists and its giver is nearby. Returns the quest row."""
    row = load_player_quest(state.player_id, quest_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quest not found")
    nearby_ids = {npc["id"] for npc in build_snapshot(world, state)["nearby_npcs"]}
    if row.offered_by_npc_id not in nearby_ids:
        raise HTTPException(status_code=400, detail="Quest giver is not nearby")
    return row