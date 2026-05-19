from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry import register_agent_builder
from .runtime import AgentInvocation


@dataclass(frozen=True)
class QuestOfferContext:
    npc: dict[str, Any]
    player_name: str
    player_message: str
    biome_name: str
    item_name: str
    reward_gold: int
    hint: str


@dataclass(frozen=True)
class QuestResponseContext:
    npc_name: str
    biome_name: str
    item_name: str
    reward_gold: int
    hint: str
    stance: str


def build_quest_offer_agent(context: QuestOfferContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"quest-offer-{context.npc['id']}",
        instructions=(
            "Write a compact NPC quest offer for a server-authoritative rogue-lite. "
            "Return strict JSON with keys: title, summary, objective_text, offer_text. "
            "Keep the quest grounded in the provided item, biome, reward, and NPC voice. "
            "Do not invent mechanics, extra rewards, or alternate objectives."
        ),
        user_prompt=(
            f"NPC: {context.npc['display_name']}\n"
            f"NPC role: {context.npc.get('role', 'contact')}\n"
            f"NPC system prompt: {context.npc.get('system_prompt', '')}\n"
            f"Player: {context.player_name}\n"
            f"Player message: {context.player_message.strip()}\n"
            f"Target item: {context.item_name}\n"
            f"Target biome: {context.biome_name}\n"
            f"Reward gold: {context.reward_gold}\n"
            f"Hint: {context.hint}\n"
            "Write one concise quest title, one summary sentence, one objective line, and one in-character offer line from the NPC."
        ),
        tools=tools,
    )


def build_quest_response_agent(context: QuestResponseContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"quest-{context.stance}",
        instructions=(
            "Write one concise in-character NPC response for a quest state transition. "
            "Return strict JSON with key: response_text. "
            "Do not invent new quest facts beyond the provided item, biome, reward, and stance."
        ),
        user_prompt=(
            f"NPC: {context.npc_name}\n"
            f"Stance: {context.stance}\n"
            f"Item: {context.item_name}\n"
            f"Biome: {context.biome_name}\n"
            f"Reward gold: {context.reward_gold}\n"
            f"Hint: {context.hint}\n"
            "Write one short reply matching the stance."
        ),
        tools=tools,
    )


register_agent_builder("quest.offer", build_quest_offer_agent)
register_agent_builder("quest.response", build_quest_response_agent)