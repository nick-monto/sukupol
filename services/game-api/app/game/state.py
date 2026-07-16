from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from ..content import WorldContent


FACING_ORDER = ("N", "E", "S", "W")
FACING_DELTAS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}


TransitionHandler = Callable[["RunState", dict[str, Any]], bool]


ConnectionPair = list[str]


@dataclass
class RunState:
    id: str
    player_id: str
    player_name: str
    location_id: str
    x: int
    y: int
    facing: str
    hp: int
    max_hp: int
    gold: int
    status: str
    message: str
    created_at: str
    run_seed: int
    steps_taken: int = 0
    dungeon_instance_id: str | None = None
    floor_number: int | None = None
    procgen_version: str | None = None
    inventory: list[dict[str, Any]] | None = None
    equipped_weapon: str | None = None
    in_combat: bool = False
    combat_state: dict[str, Any] | None = None
    run_result: str | None = None
    run_depth: int = 0
    enemies_defeated: int = 0
    triggered_encounters: list[str] | None = None
    outcome_summary: dict[str, Any] | None = None
    progression: dict[str, Any] | None = None
    active_dialogue_visits: dict[str, dict[str, Any]] | None = None
    party_allies: list[dict[str, Any]] | None = None
    discovered_overworld_locations: list[str] | None = None
    discovered_overworld_connections: list[ConnectionPair] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prepare_initial_state(world: WorldContent, player_name: str) -> dict[str, Any]:
    player_id = str(uuid4())
    run_id = str(uuid4())
    run_seed = int(uuid4().hex[:12], 16)
    spawn = world.player_spawn
    inventory = [dict(item) for item in world.starting_inventory]
    equipped = next((item["item_id"] for item in inventory if item.get("equipped")), None)
    return dict(player_id=player_id, run_id=run_id, run_seed=run_seed,
                spawn=spawn, inventory=inventory, equipped=equipped)


def create_run(world: WorldContent, player_name: str) -> RunState:
    from .overworld import is_overworld_mapped_location

    prep = _prepare_initial_state(world, player_name)
    spawn = prep["spawn"]
    discovered = ([spawn["location_id"]] if is_overworld_mapped_location(world, spawn["location_id"]) else [])
    return RunState(
        id=prep["run_id"], player_id=prep["player_id"],
        player_name=player_name, location_id=spawn["location_id"],
        x=spawn["x"], y=spawn["y"], facing=spawn.get("facing", "N"),
        hp=12, max_hp=12, gold=4, status="active",
        message="You arrive in Sukupol and steady yourself before the first descent.",
        created_at=utc_now(), run_seed=prep["run_seed"],
        inventory=prep["inventory"], equipped_weapon=prep["equipped"],
        triggered_encounters=[], discovered_overworld_locations=discovered,
        discovered_overworld_connections=[],
    )


def state_to_dict(state: RunState) -> dict[str, Any]:
    return asdict(state)


def normalize_connection_pair(location_a: Any, location_b: Any) -> ConnectionPair | None:
    if not isinstance(location_a, str) or not isinstance(location_b, str):
        return None
    first = location_a.strip()
    second = location_b.strip()
    if not first or not second or first == second:
        return None
    return sorted((first, second))


def normalize_overworld_locations(raw_locations: Any) -> list[str]:
    if not isinstance(raw_locations, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for location_id in raw_locations:
        if not isinstance(location_id, str):
            continue
        candidate = location_id.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def normalize_overworld_connections(raw_connections: Any) -> list[ConnectionPair]:
    if not isinstance(raw_connections, list):
        return []
    normalized: list[ConnectionPair] = []
    seen: set[tuple[str, str]] = set()
    for candidate in raw_connections:
        if not isinstance(candidate, (list, tuple)) or len(candidate) != 2:
            continue
        pair = normalize_connection_pair(candidate[0], candidate[1])
        if pair is None:
            continue
        pair_key = (pair[0], pair[1])
        if pair_key in seen:
            continue
        seen.add(pair_key)
        normalized.append(pair)
    return normalized


def _build_state_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(
        id=payload["id"], player_id=payload["player_id"],
        player_name=payload["player_name"],
        location_id=payload["location_id"], x=payload["x"], y=payload["y"],
        facing=payload["facing"], hp=payload["hp"], max_hp=payload["max_hp"],
        gold=payload["gold"], status=payload["status"], message=payload["message"],
        created_at=payload["created_at"], run_seed=payload.get("run_seed", 0),
        steps_taken=payload.get("steps_taken", 0), dungeon_instance_id=payload.get("dungeon_instance_id"),
        floor_number=payload.get("floor_number"), procgen_version=payload.get("procgen_version"),
        inventory=payload.get("inventory", []), equipped_weapon=payload.get("equipped_weapon"),
        in_combat=payload.get("in_combat", False), combat_state=payload.get("combat_state"),
        run_result=payload.get("run_result"), run_depth=payload.get("run_depth", 0),
        enemies_defeated=payload.get("enemies_defeated", 0),
        triggered_encounters=payload.get("triggered_encounters", []),
        outcome_summary=payload.get("outcome_summary"), progression=payload.get("progression"),
        active_dialogue_visits=payload.get("active_dialogue_visits", {}),
        party_allies=payload.get("party_allies", []),
    )


def state_from_dict(payload: dict[str, Any]) -> RunState:
    kwargs = _build_state_kwargs(payload)
    kwargs["discovered_overworld_locations"] = normalize_overworld_locations(
        payload.get("discovered_overworld_locations", []),
    )
    kwargs["discovered_overworld_connections"] = normalize_overworld_connections(
        payload.get("discovered_overworld_connections", []),
    )
    return RunState(**kwargs)
