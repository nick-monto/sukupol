from __future__ import annotations

from typing import Any

from ..agents.quest_agents import QuestOfferContext, QuestResponseContext
from ..agents.quest_generation import QuestGenerationService
from ..content import WorldContent
from ..db.quests import (
    create_player_quest,
    list_player_quests,
    load_player_quest,
    set_player_quest_status,
)
from ..db.rows import QuestRow
from ..game.state import RunState
from .profiles import _item_label, _pick, _profile_for_template
from .profiles_data import ACCEPT_TEMPLATES, DECLINE_TEMPLATES, OFFER_TEMPLATES, QUEST_TRIGGER_TERMS
from .template import _quest_payload, _serialize_quest_row


def _triggered_by_message(player_message: str) -> bool:
    message = player_message.strip().lower()
    if not message:
        return False
    return any(term in message for term in QUEST_TRIGGER_TERMS)


def _has_existing_quest(player_id: str, template_id: str) -> bool:
    for quest in list_player_quests(player_id):
        if quest.template_id == template_id:
            return True
    return False


def _generate_offer_from_service(
    quest_generation_service: QuestGenerationService | None,
    npc: dict[str, Any], state: Any, payload: dict[str, Any], biome_name: str,
) -> dict[str, Any] | None:
    if quest_generation_service is None:
        return None
    return quest_generation_service.generate_offer(
        QuestOfferContext(
            npc=npc,
            player_name=state.player_name,
            player_message=state.player_message if hasattr(state, "player_message") else "",
            biome_name=biome_name,
            item_name=payload["item_name"],
            reward_gold=payload["reward_gold"],
            hint=payload["hint"],
        )
    )


def _resolve_offer_content(
    payload: dict[str, Any], generated_offer: dict[str, Any] | None,
) -> tuple[str, str, str]:
    title = generated_offer["title"] if generated_offer is not None else payload["title"]
    summary = generated_offer["summary"] if generated_offer is not None else payload["summary"]
    objective_text = generated_offer["objective_text"] if generated_offer is not None else payload["objective_text"]
    return title, summary, objective_text


def _create_quest_row(
    payload: dict[str, Any], state: Any, npc: dict[str, Any],
    title: str, summary: str, objective_text: str,
) -> QuestRow:
    return create_player_quest(
        player_id=state.player_id, template_id=payload["template_id"],
        run_id=state.id, offered_by_npc_id=npc["id"],
        title=title, summary=summary, objective_text=objective_text,
        objective_kind=payload["objective_kind"],
        target_location_id=payload["target_location_id"],
        target_biome_id=payload["target_biome_id"],
        target_floor_number=payload["target_floor_number"],
        target_count=payload["target_count"],
        progress_value=payload["progress_value"],
        progress_target=payload["progress_target"],
        status=payload["status"],
    )


def _build_offer_text(
    payload: dict[str, Any], generated_offer: dict[str, Any] | None,
    state: Any, npc: dict[str, Any], biome_name: str,
) -> str:
    """Format the offer text from generated or template content."""
    offer_templates = tuple(payload.get("offer_templates") or OFFER_TEMPLATES)
    fallback_text = _pick(offer_templates, state.run_seed, npc["id"], payload["item_id"]).format(
        item_name=payload["item_name"],
        item_label=_item_label(payload["item_name"]),
        npc_name=npc["display_name"],
        biome_name=biome_name,
        reward_gold=payload["reward_gold"],
    )
    if generated_offer is None:
        return fallback_text
    return generated_offer.get("offer_text") or fallback_text


def maybe_offer_conversation_quest(
    world: WorldContent,
    state: RunState,
    npc: dict[str, Any],
    player_message: str,
    quest_generation_service: QuestGenerationService | None = None,
) -> dict[str, Any] | None:
    if not _triggered_by_message(player_message):
        return None
    payload = _quest_payload(world, npc, state, player_message)
    if payload is None:
        return None
    if _has_existing_quest(state.player_id, payload["template_id"]):
        return None
    biome_name = world.dungeon_biomes[payload["target_biome_id"]]["name"]
    generated_offer = _generate_offer_from_service(quest_generation_service, npc, state, payload, biome_name)
    title, summary, objective_text = _resolve_offer_content(payload, generated_offer)
    row = _create_quest_row(payload, state, npc, title, summary, objective_text)
    serialized = _serialize_quest_row(world, state, row)
    serialized["offer_text"] = _build_offer_text(payload, generated_offer, state, npc, biome_name)
    return serialized


def _generate_accept_response(
    serialized: dict[str, Any], refreshed: QuestRow,
    state: Any, quest_id: str,
    quest_generation_service: QuestGenerationService | None,
) -> str:
    profile = _profile_for_template(refreshed.offered_by_npc_id, serialized["target_item_id"])
    templates = profile.accept_templates if profile and profile.accept_templates else ACCEPT_TEMPLATES
    fallback_text = _pick(templates, state.run_seed, quest_id).format(
        item_name=serialized["target_item_name"],
        item_label=_item_label(serialized["target_item_name"]),
        npc_name=serialized["offered_by_npc_name"],
        biome_name=serialized.get("target_biome_name") or refreshed.target_biome_id or "the dungeon",
        reward_gold=serialized["reward_gold"],
    )
    if quest_generation_service is None:
        return fallback_text
    generated_text = quest_generation_service.generate_response(
        QuestResponseContext(
            npc_name=serialized["offered_by_npc_name"],
            biome_name=serialized.get("target_biome_name") or refreshed.target_biome_id or "the dungeon",
            item_name=serialized["target_item_name"],
            reward_gold=serialized["reward_gold"],
            hint=serialized.get("hint", ""),
            stance="accept",
        )
    )
    return generated_text or fallback_text


def accept_offered_quest(
    world: WorldContent,
    state: RunState,
    quest_id: str,
    quest_generation_service: QuestGenerationService | None = None,
) -> dict[str, Any]:
    row = load_player_quest(state.player_id, quest_id)
    if row is None:
        raise ValueError("Quest not found")
    if row.status != "offered":
        raise ValueError("Quest is not waiting for acceptance")
    set_player_quest_status(quest_id, status="active")
    refreshed = load_player_quest(state.player_id, quest_id)
    if refreshed is None:
        raise ValueError("Quest disappeared after acceptance")
    serialized = _serialize_quest_row(world, state, refreshed)
    serialized["response_text"] = _generate_accept_response(
        serialized, refreshed, state, quest_id, quest_generation_service,
    )
    return serialized


def _generate_decline_response(
    serialized: dict[str, Any], refreshed: QuestRow,
    state: Any, quest_id: str,
    quest_generation_service: QuestGenerationService | None,
) -> str:
    fallback_text = _pick(DECLINE_TEMPLATES, state.run_seed, quest_id)
    if quest_generation_service is None:
        return fallback_text
    generated_text = quest_generation_service.generate_response(
        QuestResponseContext(
            npc_name=serialized["offered_by_npc_name"],
            biome_name=serialized.get("target_biome_name") or refreshed.target_biome_id or "the dungeon",
            item_name=serialized["target_item_name"],
            reward_gold=serialized["reward_gold"],
            hint=serialized.get("hint", ""),
            stance="decline",
        )
    )
    return generated_text or fallback_text


def decline_offered_quest(
    world: WorldContent,
    state: RunState,
    quest_id: str,
    quest_generation_service: QuestGenerationService | None = None,
) -> dict[str, Any]:
    row = load_player_quest(state.player_id, quest_id)
    if row is None:
        raise ValueError("Quest not found")
    if row.status != "offered":
        raise ValueError("Quest is not waiting for a decision")
    set_player_quest_status(quest_id, status="declined")
    refreshed = load_player_quest(state.player_id, quest_id)
    if refreshed is None:
        raise ValueError("Quest disappeared after decline")
    serialized = _serialize_quest_row(world, state, refreshed)
    serialized["response_text"] = _generate_decline_response(
        serialized, refreshed, state, quest_id, quest_generation_service,
    )
    return serialized
