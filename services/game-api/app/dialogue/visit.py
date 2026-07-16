from __future__ import annotations

from typing import Any

from ..db.connection import utc_now
from ..db.journal import create_npc_journal_entry
from ..game import nearby_npcs

from .summary import asummarize_visit, summarize_visit


def _get_or_init_visit(
    visits: dict[str, Any], npc_id: str, npc_name: str, now: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    visit = visits.get(npc_id)
    if not isinstance(visit, dict):
        visit = {"npc_id": npc_id, "npc_name": npc_name, "started_at": now, "updated_at": now, "turns": []}
    turns = visit.get("turns")
    if not isinstance(turns, list):
        turns = []
        visit["turns"] = turns
    return visit, turns


def record_visit_turn(
    state: Any, npc_id: str, npc_name: str,
    player_message: str, reply_text: str, source: str,
) -> None:
    visits = state.active_dialogue_visits or {}
    now = utc_now()
    visit, turns = _get_or_init_visit(visits, npc_id, npc_name, now)
    turns.append({
        "player_message": player_message.strip(),
        "npc_reply": reply_text.strip(),
        "source": source,
        "timestamp": now,
    })
    visit["npc_id"] = npc_id
    visit["npc_name"] = npc_name
    visit["updated_at"] = now
    visits[npc_id] = visit
    state.active_dialogue_visits = visits


def _pop_visit(state: Any, npc_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    visits = state.active_dialogue_visits or {}
    visit = visits.get(npc_id)
    if not isinstance(visit, dict):
        return None, None
    turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
    visits.pop(npc_id, None)
    state.active_dialogue_visits = visits
    if not turns:
        return None, None
    return visit, turns


def _resolve_npc(world: Any, npc_id: str, visit: dict[str, Any]) -> dict[str, Any]:
    return world.npcs.get(npc_id, {
        "id": npc_id, "display_name": visit.get("npc_name", npc_id), "role": "contact",
    })


def _make_journal_entry(
    state: Any, npc_id: str, npc: dict[str, Any],
    visit: dict[str, Any], visit_ended_at: str, turns: list[dict[str, Any]], summary: str,
) -> dict[str, Any]:
    from dataclasses import asdict
    return asdict(create_npc_journal_entry(
        player_id=state.player_id, npc_id=npc_id, run_id=state.id,
        summary=summary, visit_started_at=str(visit.get("started_at") or visit_ended_at),
        visit_ended_at=visit_ended_at, turn_count=len(turns),
    ))


def finalize_visit(
    world: Any, state: Any, npc_id: str, mode: str, journal_service: Any,
) -> dict[str, Any] | None:
    visit, turns = _pop_visit(state, npc_id)
    if visit is None:
        return None
    assert turns is not None
    npc = _resolve_npc(world, npc_id, visit)
    visit_ended_at = utc_now()
    summary = summarize_visit(mode, journal_service, npc, visit, visit_ended_at)
    return _make_journal_entry(state, npc_id, npc, visit, visit_ended_at, turns, summary)


async def afinalize_visit(
    world: Any, state: Any, npc_id: str, mode: str, journal_service: Any,
) -> dict[str, Any] | None:
    visit, turns = _pop_visit(state, npc_id)
    if visit is None:
        return None
    assert turns is not None
    npc = _resolve_npc(world, npc_id, visit)
    visit_ended_at = utc_now()
    summary = await asummarize_visit(mode, journal_service, npc, visit, visit_ended_at)
    return _make_journal_entry(state, npc_id, npc, visit, visit_ended_at, turns, summary)


def finalize_other_active_visits(
    world: Any, state: Any, active_npc_id: str, mode: str, journal_service: Any,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for npc_id in list((state.active_dialogue_visits or {}).keys()):
        if npc_id == active_npc_id:
            continue
        entry = finalize_visit(world, state, npc_id, mode, journal_service)
        if entry is not None:
            entries.append(entry)
    return entries


async def afinalize_other_active_visits(
    world: Any, state: Any, active_npc_id: str, mode: str, journal_service: Any,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for npc_id in list((state.active_dialogue_visits or {}).keys()):
        if npc_id == active_npc_id:
            continue
        entry = await afinalize_visit(world, state, npc_id, mode, journal_service)
        if entry is not None:
            entries.append(entry)
    return entries


def finalize_departed_visits(
    world: Any, state: Any, mode: str, journal_service: Any,
) -> list[dict[str, Any]]:
    nearby_ids = {npc["id"] for npc in nearby_npcs(world, state)}
    entries: list[dict[str, Any]] = []
    for npc_id in list((state.active_dialogue_visits or {}).keys()):
        if npc_id in nearby_ids:
            continue
        entry = finalize_visit(world, state, npc_id, mode, journal_service)
        if entry is not None:
            entries.append(entry)
    return entries


def finalize_all_active_visits(
    world: Any, state: Any, mode: str, journal_service: Any,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for npc_id in list((state.active_dialogue_visits or {}).keys()):
        entry = finalize_visit(world, state, npc_id, mode, journal_service)
        if entry is not None:
            entries.append(entry)
    return entries
