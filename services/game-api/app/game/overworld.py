from __future__ import annotations

from typing import Any

from ..content import WorldContent
from .state import RunState, normalize_connection_pair
from .state import normalize_overworld_connections, normalize_overworld_locations


def overworld_map_data(location: dict[str, Any]) -> dict[str, int] | None:
    raw = location.get("overworld_map")
    if not isinstance(raw, dict):
        return None
    x = raw.get("x")
    y = raw.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    return {"x": x, "y": y}


def is_overworld_mapped_location(world: WorldContent, location_id: str) -> bool:
    location = world.locations.get(location_id)
    if location is None:
        return False
    return overworld_map_data(location) is not None


def reveal_overworld_location(world: WorldContent, state: RunState, location_id: str) -> None:
    if not is_overworld_mapped_location(world, location_id):
        return
    locations = normalize_overworld_locations(state.discovered_overworld_locations or [])
    if location_id not in locations:
        locations.append(location_id)
    state.discovered_overworld_locations = locations


def reveal_overworld_connection(world: WorldContent, state: RunState, location_a: str, location_b: str) -> None:
    if not is_overworld_mapped_location(world, location_a) or not is_overworld_mapped_location(world, location_b):
        return
    pair = normalize_connection_pair(location_a, location_b)
    if pair is None:
        return
    reveal_overworld_location(world, state, pair[0])
    reveal_overworld_location(world, state, pair[1])
    connections = normalize_overworld_connections(state.discovered_overworld_connections or [])
    if pair not in connections:
        connections.append(pair)
    state.discovered_overworld_connections = connections


def _append_overworld_node(
    nodes: list[dict[str, Any]], location: dict[str, Any],
    map_position: dict[str, int], discovered_locations: set[str],
) -> None:
    nodes.append({
        "id": location["id"],
        "name": location["name"],
        "x": map_position["x"],
        "y": map_position["y"],
        "discovered": location["id"] in discovered_locations,
    })


def _process_overworld_exit(
    location: dict[str, Any], exit_node: dict[str, Any],
    connections_by_key: dict[tuple[str, str], dict[str, Any]],
    discovered_connections: set[tuple[str, str]], world: WorldContent,
) -> None:
    if exit_node.get("transition"):
        return
    target_id = exit_node.get("target_location_id")
    if not isinstance(target_id, str) or not is_overworld_mapped_location(world, target_id):
        return
    pair = normalize_connection_pair(location["id"], target_id)
    if pair is None:
        return
    pair_key = (pair[0], pair[1])
    if pair_key not in connections_by_key:
        connections_by_key[pair_key] = {
            "location_ids": pair,
            "discovered": pair_key in discovered_connections,
        }


def _collect_overworld_map_data(
    world: WorldContent,
    discovered_locations: set[str],
    discovered_connections: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    connections_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for location in world.locations.values():
        map_position = overworld_map_data(location)
        if map_position is None:
            continue
        _append_overworld_node(nodes, location, map_position, discovered_locations)
        for exit_node in location.get("exits", []):
            _process_overworld_exit(location, exit_node, connections_by_key, discovered_connections, world)
    return nodes, connections_by_key


def _build_overworld_map_result(
    nodes: list[dict[str, Any]],
    connections_by_key: dict[tuple[str, str], dict[str, Any]],
    world: WorldContent, state: RunState,
) -> dict[str, Any] | None:
    if not nodes:
        return None
    nodes.sort(key=lambda n: (n["y"], n["x"], n["id"]))
    connections = sorted(
        connections_by_key.values(),
        key=lambda c: (c["location_ids"][0], c["location_ids"][1]),
    )
    current_id = state.location_id if is_overworld_mapped_location(world, state.location_id) else None
    return {
        "current_location_id": current_id,
        "nodes": nodes,
        "connections": connections,
    }


def build_overworld_map(world: WorldContent, state: RunState) -> dict[str, Any] | None:
    discovered_locations = set(normalize_overworld_locations(state.discovered_overworld_locations or []))
    discovered_connections: set[tuple[str, str]] = {
        (pair[0], pair[1]) for pair in normalize_overworld_connections(state.discovered_overworld_connections or [])
    }
    nodes, connections_by_key = _collect_overworld_map_data(world, discovered_locations, discovered_connections)
    return _build_overworld_map_result(nodes, connections_by_key, world, state)
