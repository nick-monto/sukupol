from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .db import (
    create_player_quest,
    list_player_quests,
    load_player_quest,
    set_player_quest_progress,
    set_player_quest_status,
)
from .inventory import add_item, get_inventory_entry, remove_item


QUEST_TRIGGER_TERMS = (
    "help",
    "job",
    "quest",
    "work",
    "errand",
    "task",
    "need",
    "missing",
    "find",
    "recover",
    "retrieve",
    "fetch",
    "looking for",
)

TITLE_TEMPLATES = (
    "Recover the {item_name}",
    "Bring Back the {item_name}",
    "Find {npc_name}'s {item_name}",
)

SUMMARY_TEMPLATES = (
    "{npc_name} asked you to recover the {item_name}, last seen in the {biome_name}, and return it intact.",
    "A missing keepsake lies somewhere in the {biome_name}. {npc_name} wants it brought back before the dungeon ruins it completely.",
    "{npc_name} believes the {item_name} was dragged into the {biome_name}. Recover it and bring it back in person.",
)

OFFER_TEMPLATES = (
    "If you're heading into the {biome_name}, acquire my lost {item_label} and bring it back to me.",
    "One thing more: my {item_label} vanished into the {biome_name}. Bring it back if you can.",
    "Do a piece of work for me. Recover my {item_label} from the {biome_name} and return it here.",
)

ACCEPT_TEMPLATES = (
    "Good. Recover the {item_name} from the {biome_name} and bring it straight back to me.",
    "Then we understand each other. Find the {item_name} in the {biome_name} and return with it.",
)

DECLINE_TEMPLATES = (
    "Leave it, then. I will find another way to bear the loss.",
    "Fair enough. Better a refusal than a promise made loosely.",
)

COMPLETE_TEMPLATES = (
    "You brought it back. I'll see this kept safe, and {reward_gold} gold is yours.",
    "That is the one. You have my thanks, and {reward_gold} gold for bringing it home.",
)

BIOME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ancient_halls": (
        "ancient halls",
        "halls",
        "hall",
        "first descent",
        "approach",
        "shrine",
        "stone halls",
    ),
    "sunken_archive": (
        "sunken archive",
        "archive",
        "archives",
        "flooded archive",
        "whispering cave",
        "cave",
        "flooded stair",
        "drowned vault",
    ),
}

NPC_BIOME_PREFERENCES: dict[str, tuple[str, ...]] = {
    "marta-innkeeper": ("sunken_archive", "ancient_halls"),
    "ilya-lamplighter": ("ancient_halls", "sunken_archive"),
    "petra-scout": ("ancient_halls", "sunken_archive"),
    "sava-herbalist": ("sunken_archive", "ancient_halls"),
}


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


QUEST_PROFILES: dict[str, tuple[QuestProfile, ...]] = {
    "marta-innkeeper": (
        QuestProfile(
            item_id="marta_ledger_satchel",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=18,
            hint="Drowned scribes drag satchels toward the first flooded shelves.",
            offer_templates=(
                "If you're heading into the {biome_name}, acquire my lost {item_label} and bring it back to me.",
                "My {item_label} went missing in the {biome_name}. Bring it back before the damp ruins the whole account book.",
            ),
            complete_templates=(
                "You brought the {item_name} back dry enough to save. Take {reward_gold} gold for the trouble.",
                "Good. The house can keep its books another week. {reward_gold} gold, as promised.",
            ),
        ),
        QuestProfile(
            item_id="marta_cellar_key",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=15,
            hint="Old bronze keys end up in rubble pockets where wardens used to stand watch.",
            offer_templates=(
                "There is another thing. My old cellar key vanished into the {biome_name}. Recover it if you pass that way.",
                "Bring me back my {item_label} from the {biome_name}. I'd rather not lose another storehouse to a bad latch.",
            ),
            complete_templates=(
                "That key still turns, by the look of it. Take {reward_gold} gold and my thanks.",
                "You saved me a locksmith and a great deal of cursing. {reward_gold} gold for you.",
            ),
        ),
    ),
    "ilya-lamplighter": (
        QuestProfile(
            item_id="ilya_lost_lamp",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=16,
            hint="Bright things tend to end up near collapsed shrines on the first descent.",
            offer_templates=(
                "If you descend into the {biome_name}, acquire my lost {item_label} and bring it back lit or dark, I don't care which.",
                "My {item_label} is still somewhere in the {biome_name}. Find it and return it before the dark claims it entirely.",
            ),
            complete_templates=(
                "There it is. I know the weight of it even cold. {reward_gold} gold is yours.",
                "You carried a little light back with you. Take {reward_gold} gold for the effort.",
            ),
        ),
        QuestProfile(
            item_id="ilya_watch_oil",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=17,
            hint="Oil flasks drift toward the archive shelves where the seep runs blackest.",
            offer_templates=(
                "A sealed flask of watch oil went missing in the {biome_name}. Bring the {item_label} back if you find it.",
                "Recover my {item_label} from the {biome_name}. Without it, half the square burns dirty by dusk.",
            ),
            complete_templates=(
                "Still sealed. Good. This will keep the square burning another few nights. {reward_gold} gold.",
                "That oil matters more than it looks. Take {reward_gold} gold and keep your own flame close.",
            ),
        ),
    ),
    "petra-scout": (
        QuestProfile(
            item_id="petra_scout_compass",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=20,
            hint="Watch the first side chambers. Sentinels collect dropped field gear.",
            offer_templates=(
                "One of my route runs ended badly in the {biome_name}. Bring back my {item_label} if you see it.",
                "Find my {item_label} in the {biome_name} and bring it back. I trust the mark cuts on the casing more than memory.",
            ),
            complete_templates=(
                "Good. I can chart with this again. {reward_gold} gold for bringing it back.",
                "That compass still holds true. You've earned {reward_gold} gold.",
            ),
        ),
        QuestProfile(
            item_id="petra_route_case",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=19,
            hint="Map cases snag under flooded desks and broken shelf braces.",
            offer_templates=(
                "My {item_label} slipped away in the {biome_name}. Recover it before the damp turns the route notes to pulp.",
                "If you push into the {biome_name}, keep an eye out for my {item_label} and bring it straight back.",
            ),
            complete_templates=(
                "The notes inside might still be readable. That's worth {reward_gold} gold to me.",
                "You saved the routes and a week's work with them. Take {reward_gold} gold.",
            ),
        ),
    ),
    "sava-herbalist": (
        QuestProfile(
            item_id="sava_spore_case",
            target_biome_id="sunken_archive",
            target_floor_number=1,
            reward_gold=22,
            hint="Specimen cases sink where the waterline meets broken reading desks.",
            offer_templates=(
                "Recover my {item_label} from the {biome_name}. I want those samples before the mold changes them.",
                "The {biome_name} took my {item_label}. Bring it back intact and I'll make it worth the trip.",
            ),
            complete_templates=(
                "Still sealed. Good. The samples may yet tell the truth. {reward_gold} gold for you.",
                "You kept the spores uncontaminated. That earns {reward_gold} gold and real gratitude.",
            ),
        ),
        QuestProfile(
            item_id="sava_amber_vial",
            target_biome_id="ancient_halls",
            target_floor_number=1,
            reward_gold=21,
            hint="Glass vials catch in cracked flagstones where shrine dust has settled thickest.",
            offer_templates=(
                "Bring back my {item_label} from the {biome_name}. The resin inside matters more than the glass.",
                "I lost an {item_label} in the {biome_name}. Recover it before the seal gives out.",
            ),
            complete_templates=(
                "Unbroken. Better than I expected. Take {reward_gold} gold for returning it.",
                "That vial could have shattered a dozen times over. {reward_gold} gold says I know the value of what you did.",
            ),
        ),
    ),
}


def _checksum(*parts: Any) -> int:
    return sum(sum(ord(character) for character in str(part)) for part in parts)


def _pick(options: tuple[str, ...], *parts: Any) -> str:
    if not options:
        return ""
    return options[_checksum(*parts) % len(options)]


def _item_label(item_name: str) -> str:
    return item_name.lower()


def _profile_for_npc(npc_id: str) -> QuestProfile | None:
    profiles = QUEST_PROFILES.get(npc_id, ())
    return profiles[0] if profiles else None


def _profiles_for_npc(npc_id: str) -> tuple[QuestProfile, ...]:
    return QUEST_PROFILES.get(npc_id, ())


def _ordered_profiles_for_npc(npc_id: str, run_seed: int) -> tuple[QuestProfile, ...]:
    profiles = list(_profiles_for_npc(npc_id))
    if not profiles:
        return ()
    offset = _checksum(run_seed, npc_id, "quest-rotation") % len(profiles)
    return tuple(profiles[offset:] + profiles[:offset])


def _message_preferred_biomes(player_message: str) -> tuple[str, ...]:
    lowered = player_message.strip().lower()
    if not lowered:
        return ()

    matches: list[str] = []
    for biome_id, keywords in BIOME_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(biome_id)
    return tuple(matches)


def _location_preferred_biomes(world: Any, state: Any) -> tuple[str, ...]:
    location = world.locations.get(state.location_id)
    if location is None:
        return ()

    preferences: list[str] = []
    biome_id = location.get("biome_id")
    if biome_id in {"ancient_halls", "sunken_archive"}:
        preferences.append(biome_id)

    for exit_node in location.get("exits", []):
        if exit_node.get("transition") == "generated_dungeon" and exit_node.get("biome_id"):
            preferences.append(str(exit_node["biome_id"]))

    if state.location_id == "dungeon_approach":
        preferences.append("ancient_halls")
    elif state.location_id == "whispering_cave":
        preferences.append("sunken_archive")
    elif state.location_id == "outer_fields":
        preferences.extend(("ancient_halls", "sunken_archive"))

    ordered: list[str] = []
    for candidate in preferences:
        if candidate not in ordered:
            ordered.append(candidate)
    return tuple(ordered)


def _npc_preferred_biomes(npc_id: str) -> tuple[str, ...]:
    return NPC_BIOME_PREFERENCES.get(npc_id, ())


def _weighted_preference_score(profile: QuestProfile, preferred_biomes: tuple[str, ...], base_weight: int) -> int:
    if not preferred_biomes or base_weight <= 0:
        return 0
    try:
        preference_index = preferred_biomes.index(profile.target_biome_id)
    except ValueError:
        return 0
    return max(0, base_weight - (preference_index * 10))


def _profile_context_score(world: Any, npc: dict[str, Any], state: Any, player_message: str, profile: QuestProfile) -> int:
    message_score = _weighted_preference_score(profile, _message_preferred_biomes(player_message), 200)
    npc_score = _weighted_preference_score(profile, _npc_preferred_biomes(npc["id"]), 90)
    location_score = _weighted_preference_score(profile, _location_preferred_biomes(world, state), 50)
    return message_score + npc_score + location_score


def _select_profile(world: Any, npc: dict[str, Any], state: Any, player_message: str) -> QuestProfile | None:
    existing_templates = {
        quest["template_id"]
        for quest in list_player_quests(state.player_id)
        if quest["offered_by_npc_id"] == npc["id"]
    }
    ordered_profiles = _ordered_profiles_for_npc(npc["id"], state.run_seed)
    candidates = [
        profile for profile in ordered_profiles if _template_id(npc["id"], profile) not in existing_templates
    ]
    if not candidates:
        return None

    ranked = sorted(
        enumerate(candidates),
        key=lambda item: (-_profile_context_score(world, npc, state, player_message, item[1]), item[0]),
    )
    return ranked[0][1] if ranked else None


def _profile_for_template(npc_id: str, item_id: str) -> QuestProfile | None:
    for profile in _profiles_for_npc(npc_id):
        if profile.item_id == item_id:
            return profile
    return None


def _template_id(npc_id: str, profile: QuestProfile) -> str:
    return (
        f"fetch|{npc_id}|{profile.target_biome_id}|{profile.target_floor_number}|"
        f"{profile.item_id}|{profile.reward_gold}"
    )


def _parse_template_id(template_id: str) -> dict[str, Any]:
    parts = template_id.split("|")
    if len(parts) != 6 or parts[0] != "fetch":
        raise ValueError(f"Unsupported quest template id: {template_id}")
    return {
        "kind": parts[0],
        "npc_id": parts[1],
        "target_biome_id": parts[2],
        "target_floor_number": int(parts[3]),
        "item_id": parts[4],
        "reward_gold": int(parts[5]),
    }


def _triggered_by_message(player_message: str) -> bool:
    message = player_message.strip().lower()
    if not message:
        return False
    return any(term in message for term in QUEST_TRIGGER_TERMS)


def _quest_payload(world: Any, npc: dict[str, Any], state: Any, player_message: str) -> dict[str, Any] | None:
    profile = _select_profile(world, npc, state, player_message)
    if profile is None:
        return None

    biome = world.dungeon_biomes[profile.target_biome_id]
    item = world.items[profile.item_id]
    title = _pick(TITLE_TEMPLATES, state.run_seed, npc["id"], item["id"]).format(
        item_name=item["name"],
        npc_name=npc["display_name"],
    )
    summary = _pick(SUMMARY_TEMPLATES, npc["id"], state.run_seed, biome["id"]).format(
        npc_name=npc["display_name"],
        item_name=item["name"],
        biome_name=biome["name"],
    )
    objective_text = f"Recover the {item['name']} in {biome['name']} and bring it back to {npc['display_name']}."
    return {
        "template_id": _template_id(npc["id"], profile),
        "title": title,
        "summary": summary,
        "objective_text": objective_text,
        "objective_kind": "fetch",
        "target_location_id": None,
        "target_biome_id": profile.target_biome_id,
        "target_floor_number": profile.target_floor_number,
        "target_count": 1,
        "progress_value": 0,
        "progress_target": 1,
        "status": "offered",
        "item_id": item["id"],
        "item_name": item["name"],
        "reward_gold": profile.reward_gold,
        "hint": profile.hint,
        "offer_templates": profile.offer_templates,
        "accept_templates": profile.accept_templates,
        "complete_templates": profile.complete_templates,
    }


def list_serialized_player_quests(world: Any, state: Any) -> list[dict[str, Any]]:
    rows = list_player_quests(state.player_id)
    payload = [_serialize_quest_row(world, state, row) for row in rows]
    status_rank = {"offered": 0, "active": 1, "completed": 2, "declined": 3}
    payload.sort(key=lambda quest: (status_rank.get(quest["status"], 9), -(quest["updated_sort"])))
    for quest in payload:
        quest.pop("updated_sort", None)
    return payload


def _serialize_quest_row(world: Any, state: Any, row: dict[str, Any]) -> dict[str, Any]:
    template = _parse_template_id(row["template_id"])
    item = world.items.get(template["item_id"], {"name": template["item_id"]})
    npc = world.npcs.get(row["offered_by_npc_id"], {"display_name": row["offered_by_npc_id"]})
    profile = _profile_for_template(row["offered_by_npc_id"], template["item_id"])
    biome = world.dungeon_biomes.get(row["target_biome_id"], {"name": row["target_biome_id"]}) if row.get("target_biome_id") else None
    has_item = get_inventory_entry(state, template["item_id"]) is not None

    progress_value = 1 if has_item and row["status"] == "active" else int(row.get("progress_value", 0))
    objective_text = row.get("objective_text", "")
    if row["status"] == "offered":
        objective_text = row.get("objective_text") or f"Accept {npc['display_name']}'s request to recover the {item['name']}."
    elif row["status"] == "active" and has_item:
        objective_text = f"Return the {item['name']} to {npc['display_name']}."
    elif row["status"] == "active":
        objective_text = f"Recover the {item['name']} in {biome['name']} and bring it back to {npc['display_name']}."
    elif row["status"] == "completed" and row.get("completion_summary"):
        objective_text = row["completion_summary"]

    updated_sort = _iso_sort_key(row.get("updated_at") or row.get("offered_at") or "")
    return {
        "id": row["id"],
        "title": row["title"],
        "summary": row["summary"],
        "objective_text": objective_text,
        "objective_kind": row["objective_kind"],
        "status": row["status"],
        "offered_by_npc_id": row["offered_by_npc_id"],
        "offered_by_npc_name": npc["display_name"],
        "target_biome_id": row.get("target_biome_id"),
        "target_biome_name": biome["name"] if biome else None,
        "target_floor_number": row.get("target_floor_number"),
        "target_count": int(row.get("target_count", 1)),
        "progress_value": progress_value,
        "progress_target": int(row.get("progress_target", 1)),
        "target_item_id": template["item_id"],
        "target_item_name": item["name"],
        "reward_gold": template["reward_gold"],
        "completion_summary": row.get("completion_summary"),
        "can_turn_in": row["status"] == "active" and has_item,
        "hint": profile.hint if profile else "",
        "offered_at": row.get("offered_at"),
        "accepted_at": row.get("accepted_at"),
        "completed_at": row.get("completed_at"),
        "declined_at": row.get("declined_at"),
        "updated_at": row.get("updated_at"),
        "updated_sort": updated_sort,
    }


def _iso_sort_key(value: str) -> int:
    digits = "".join(character for character in value if character.isdigit())
    return int(digits) if digits else 0


def maybe_offer_conversation_quest(
    world: Any,
    state: Any,
    npc: dict[str, Any],
    player_message: str,
) -> dict[str, Any] | None:
    if not _triggered_by_message(player_message):
        return None

    payload = _quest_payload(world, npc, state, player_message)
    if payload is None:
        return None

    existing = next(
        (quest for quest in list_player_quests(state.player_id) if quest["template_id"] == payload["template_id"]),
        None,
    )
    if existing is not None:
        return None

    row = create_player_quest(
        player_id=state.player_id,
        template_id=payload["template_id"],
        run_id=state.id,
        offered_by_npc_id=npc["id"],
        title=payload["title"],
        summary=payload["summary"],
        objective_text=payload["objective_text"],
        objective_kind=payload["objective_kind"],
        target_location_id=payload["target_location_id"],
        target_biome_id=payload["target_biome_id"],
        target_floor_number=payload["target_floor_number"],
        target_count=payload["target_count"],
        progress_value=payload["progress_value"],
        progress_target=payload["progress_target"],
        status="offered",
    )
    serialized = _serialize_quest_row(world, state, row)
    biome_name = serialized.get("target_biome_name") or payload["target_biome_id"]
    offer_templates = tuple(payload.get("offer_templates") or OFFER_TEMPLATES)
    offer_text = _pick(offer_templates, state.run_seed, npc["id"], payload["item_id"]).format(
        biome_name=biome_name,
        item_label=_item_label(payload["item_name"]),
        item_name=payload["item_name"],
        npc_name=npc["display_name"],
        reward_gold=payload["reward_gold"],
    )
    serialized["offer_text"] = offer_text
    return serialized


def accept_offered_quest(world: Any, state: Any, quest_id: str) -> dict[str, Any]:
    row = load_player_quest(state.player_id, quest_id)
    if row is None:
        raise ValueError("Quest not found")
    if row["status"] != "offered":
        raise ValueError("Quest is not waiting for acceptance")

    set_player_quest_status(quest_id, status="active")
    refreshed = load_player_quest(state.player_id, quest_id)
    if refreshed is None:
        raise ValueError("Quest disappeared after acceptance")

    serialized = _serialize_quest_row(world, state, refreshed)
    profile = _profile_for_template(refreshed["offered_by_npc_id"], serialized["target_item_id"])
    accept_templates = profile.accept_templates if profile and profile.accept_templates else ACCEPT_TEMPLATES
    serialized["response_text"] = _pick(accept_templates, state.run_seed, quest_id).format(
        item_name=serialized["target_item_name"],
        item_label=_item_label(serialized["target_item_name"]),
        npc_name=serialized["offered_by_npc_name"],
        biome_name=serialized.get("target_biome_name") or refreshed.get("target_biome_id") or "the dungeon",
        reward_gold=serialized["reward_gold"],
    )
    return serialized


def decline_offered_quest(world: Any, state: Any, quest_id: str) -> dict[str, Any]:
    row = load_player_quest(state.player_id, quest_id)
    if row is None:
        raise ValueError("Quest not found")
    if row["status"] != "offered":
        raise ValueError("Quest is not waiting for a decision")

    set_player_quest_status(quest_id, status="declined")
    refreshed = load_player_quest(state.player_id, quest_id)
    if refreshed is None:
        raise ValueError("Quest disappeared after decline")

    serialized = _serialize_quest_row(world, state, refreshed)
    serialized["response_text"] = _pick(DECLINE_TEMPLATES, state.run_seed, quest_id)
    return serialized


def maybe_complete_quest_turn_in(world: Any, state: Any, npc_id: str) -> dict[str, Any] | None:
    for row in list_player_quests(state.player_id):
        if row["offered_by_npc_id"] != npc_id or row["status"] != "active":
            continue

        template = _parse_template_id(row["template_id"])
        if get_inventory_entry(state, template["item_id"]) is None:
            continue

        reward_gold = template["reward_gold"]
        remove_item(state, template["item_id"], quantity=1)
        state.gold += reward_gold
        item_name = world.items.get(template["item_id"], {"name": template["item_id"]})["name"]
        completion_summary = f"Returned the {item_name} to {world.npcs[npc_id]['display_name']} for {reward_gold} gold."
        set_player_quest_progress(quest_id=row["id"], progress_value=1, objective_text=completion_summary)
        set_player_quest_status(quest_id=row["id"], status="completed", completion_summary=completion_summary)
        refreshed = load_player_quest(state.player_id, row["id"])
        if refreshed is None:
            raise ValueError("Quest disappeared during completion")

        serialized = _serialize_quest_row(world, state, refreshed)
        profile = _profile_for_template(row["offered_by_npc_id"], template["item_id"])
        complete_templates = profile.complete_templates if profile and profile.complete_templates else COMPLETE_TEMPLATES
        serialized["response_text"] = _pick(complete_templates, state.run_seed, row["id"]).format(
            item_name=item_name,
            item_label=_item_label(item_name),
            npc_name=world.npcs[npc_id]["display_name"],
            biome_name=serialized.get("target_biome_name") or template["target_biome_id"],
            reward_gold=reward_gold,
        )
        return serialized
    return None


def recover_active_fetch_quest_items(world: Any, state: Any) -> list[dict[str, Any]]:
    location = world.locations.get(state.location_id)
    if location is None:
        return []

    biome_id = location.get("biome_id")
    floor_number = int(location.get("floor_number") or state.floor_number or 0)
    if biome_id is None:
        return []

    eligible_rows: list[dict[str, Any]] = []
    for row in list_player_quests(state.player_id):
        if row["status"] != "active" or row["objective_kind"] != "fetch":
            continue
        template = _parse_template_id(row["template_id"])
        if template["target_biome_id"] != biome_id or floor_number < template["target_floor_number"]:
            continue
        if get_inventory_entry(state, template["item_id"]) is not None:
            continue
        eligible_rows.append(row)

    if not eligible_rows:
        return []

    eligible_rows.sort(key=lambda row: (_iso_sort_key(row.get("accepted_at") or row.get("offered_at") or ""), row["id"]))
    row = eligible_rows[0]
    template = _parse_template_id(row["template_id"])
    add_item(state, world, template["item_id"], quantity=1)
    item_name = world.items.get(template["item_id"], {"name": template["item_id"]})["name"]
    quest_npc_name = world.npcs.get(row["offered_by_npc_id"], {"display_name": row["offered_by_npc_id"]})["display_name"]
    objective_text = f"Return the {item_name} to {quest_npc_name}."
    set_player_quest_progress(quest_id=row["id"], progress_value=1, objective_text=objective_text)
    return [
        {
            "quest_id": row["id"],
            "item_id": template["item_id"],
            "item_name": item_name,
            "npc_name": quest_npc_name,
        }
    ]
