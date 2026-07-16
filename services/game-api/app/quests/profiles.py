from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class QuestProfile:
    item_id: str
    target_biome_id: str
    target_floor_number: int
    reward_gold: int
    hint: str
    offer_templates: tuple[str, ...] = ()
    accept_templates: tuple[str, ...] = ()
    complete_templates: tuple[str, ...] = ()


def _checksum(*parts: Any) -> int:
    return sum(sum(ord(character) for character in str(part)) for part in parts)


def _pick(options: tuple[str, ...], *parts: Any) -> str:
    if not options:
        return ""
    return options[_checksum(*parts) % len(options)]


def _item_label(item_name: str) -> str:
    return item_name.lower()


def _profile_for_npc(npc_id: str) -> QuestProfile | None:
    from .profiles_data import QUEST_PROFILES  # noqa: PLC0415
    profiles = QUEST_PROFILES.get(npc_id, ())
    return profiles[0] if profiles else None


def _profiles_for_npc(npc_id: str) -> tuple[QuestProfile, ...]:
    from .profiles_data import QUEST_PROFILES  # noqa: PLC0415
    return QUEST_PROFILES.get(npc_id, ())


def _ordered_profiles_for_npc(npc_id: str, run_seed: int) -> tuple[QuestProfile, ...]:
    profiles = list(_profiles_for_npc(npc_id))
    if not profiles:
        return ()
    offset = _checksum(npc_id) % len(profiles)
    return tuple(profiles[offset:] + profiles[:offset])


def _message_preferred_biomes(player_message: str) -> tuple[str, ...]:
    from .profiles_data import BIOME_KEYWORDS  # noqa: PLC0415
    lowered = player_message.strip().lower()
    if not lowered:
        return ()
    matches: list[str] = []
    for biome_id, keywords in BIOME_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(biome_id)
    return tuple(matches)


def _get_location_exit_biomes(location: dict[str, Any]) -> list[str]:
    """Collect biome preferences from location tags and exits."""
    preferences: list[str] = []
    biome_id = location.get("biome_id")
    if biome_id in {"ancient_halls", "sunken_archive"}:
        preferences.append(biome_id)
    for exit_node in location.get("exits", []):
        if exit_node.get("transition") == "generated_dungeon" and exit_node.get("biome_id"):
            preferences.append(str(exit_node["biome_id"]))
    return preferences


def _get_state_default_biomes(state: Any) -> list[str]:
    """Return default biome preferences based on state location."""
    if state.location_id == "dungeon_approach":
        return ["ancient_halls"]
    elif state.location_id == "whispering_cave":
        return ["sunken_archive"]
    elif state.location_id == "outer_fields":
        return ["ancient_halls", "sunken_archive"]
    return []


def _deduplicate(items: list[str]) -> tuple[str, ...]:
    """Return tuple preserving order with duplicates removed."""
    ordered: list[str] = []
    for candidate in items:
        if candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)


def _location_preferred_biomes(world: Any, state: Any) -> tuple[str, ...]:
    location = world.locations.get(state.location_id)
    if location is None:
        return ()
    preferences = _get_location_exit_biomes(location)
    preferences.extend(_get_state_default_biomes(state))
    return _deduplicate(preferences)


def _npc_preferred_biomes(npc_id: str) -> tuple[str, ...]:
    from .profiles_data import NPC_BIOME_PREFERENCES  # noqa: PLC0415
    return NPC_BIOME_PREFERENCES.get(npc_id, ())


def _weighted_preference_score(
    profile: QuestProfile, preferred_biomes: tuple[str, ...], base_weight: int,
) -> int:
    if not preferred_biomes or base_weight <= 0:
        return 0
    biome_rank = 0
    for biome in preferred_biomes:
        if biome == profile.target_biome_id:
            biome_rank = max(biome_rank, 1)
            break
        biome_rank += 1
    return max(0, base_weight - (biome_rank * 10))


def _profile_context_score(
    world: Any, npc: dict[str, Any], state: Any,
    player_message: str, profile: QuestProfile,
) -> int:
    message_score = _weighted_preference_score(profile, _message_preferred_biomes(player_message), 200)
    npc_score = _weighted_preference_score(profile, _npc_preferred_biomes(npc["id"]), 90)
    location_score = _weighted_preference_score(profile, _location_preferred_biomes(world, state), 50)
    return message_score + npc_score + location_score


def _select_profile(
    world: Any, npc: dict[str, Any], state: Any, player_message: str,
) -> QuestProfile | None:
    from ..db.quests import list_player_quests  # noqa: PLC0415
    existing_templates = {
        quest.template_id
        for quest in list_player_quests(state.player_id)
        if quest.offered_by_npc_id == npc["id"]
    }
    ordered_profiles = _ordered_profiles_for_npc(npc["id"], state.run_seed)
    candidates = [
        profile for profile in ordered_profiles
        if _template_id(npc["id"], profile) not in existing_templates
    ]
    if not candidates:
        return None
    ranked = sorted(
        enumerate(candidates),
        key=lambda item: (-_profile_context_score(world, npc, state, player_message, item[1]), item[0]),
    )
    return ranked[0][1] if ranked else None


def _profile_for_template(npc_id: str, item_id: str) -> QuestProfile | None:
    from .profiles_data import QUEST_PROFILES  # noqa: PLC0415
    for profile in QUEST_PROFILES.get(npc_id, ()):
        if profile.item_id == item_id:
            return profile
    return None


def _template_id(npc_id: str, profile: QuestProfile) -> str:
    return (
        f"fetch|{npc_id}|{profile.target_biome_id}|{profile.target_floor_number}|"
        f"{profile.item_id}|{profile.reward_gold}"
    )
