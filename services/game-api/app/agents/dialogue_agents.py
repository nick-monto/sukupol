from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..game import RunState
from .registry import register_agent_builder
from .runtime import AgentInvocation


@dataclass(frozen=True)
class NpcDialogueTurnContext:
    npc: dict[str, Any]
    state: RunState
    player_message: str
    player_memory: dict[str, str]
    shared_knowledge: list[dict[str, Any]]


def build_npc_dialogue_agent(context: NpcDialogueTurnContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"npc-{context.npc['id']}",
        instructions=build_dialogue_instructions(context.npc),
        user_prompt=build_dialogue_user_prompt(
            context.state,
            context.player_message,
            context.player_memory,
            context.shared_knowledge,
        ),
        tools=tools,
    )


def build_npc_stream_dialogue_agent(
    context: NpcDialogueTurnContext,
    tools: tuple[Any, ...] = (),
) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"npc-{context.npc['id']}",
        instructions=build_stream_dialogue_instructions(context.npc),
        user_prompt=build_stream_dialogue_user_prompt(
            context.state,
            context.player_message,
            context.player_memory,
            context.shared_knowledge,
        ),
        tools=tools,
    )



def build_dialogue_instructions(npc: dict[str, Any]) -> str:
    return (
        f"{npc['system_prompt']}\n"
        "Stay in character, keep responses grounded in the provided game state, and never invent mechanics or places that are not in context. "
        "Speak like a real person in a tense face-to-face conversation, not a narrator. "
        "Answer directly and default to 1-3 short sentences. "
        "Do not monologue, over-explain, stack metaphors, or repeat the obvious. "
        "If the player asks something simple, a brief direct answer is enough. "
        "Use the available tools when you need exact live state or inventory; prefer tool results over guessing. "
        "Return strict JSON with key: reply."
    )


def build_stream_dialogue_instructions(npc: dict[str, Any]) -> str:
    return (
        f"{npc['system_prompt']}\n"
        "Stay in character, keep responses grounded in the provided game state, and never invent mechanics or places that are not in context. "
        "Speak like a real person in a tense face-to-face conversation, not a narrator. "
        "Answer directly and default to 1-3 short sentences. "
        "Do not monologue, over-explain, stack metaphors, or repeat the obvious. "
        "If the player asks something simple, a brief direct answer is enough. "
        "Use the available tools when you need exact live state or inventory; prefer tool results over guessing. "
        "Reply with plain in-character prose only. Do not wrap the response in JSON, markdown fences, or bullet lists unless the player explicitly asks for that format."
    )


def build_dialogue_user_prompt(
    state: RunState,
    player_message: str,
    player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]],
) -> str:
    knowledge_text = "\n".join(f"- {entry['category']}: {entry['content']}" for entry in shared_knowledge[:6])
    return (
        f"Player: {state.player_name}\n"
        f"Location: {state.location_id}\n"
        f"Depth reached: {state.run_depth}\n"
        f"HP: {state.hp}/{state.max_hp}\n"
        f"Gold: {state.gold}\n"
        f"Prior memory: {player_memory.get('summary', '') or 'none'}\n"
        f"Shared knowledge:\n{knowledge_text or '- none'}\n\n"
        f"Player message: {player_message.strip()}\n\n"
        "Keep the reply compact and natural.\n"
        "Respond as JSON only."
    )


def build_stream_dialogue_user_prompt(
    state: RunState,
    player_message: str,
    player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]],
) -> str:
    knowledge_text = "\n".join(f"- {entry['category']}: {entry['content']}" for entry in shared_knowledge[:6])
    return (
        f"Player: {state.player_name}\n"
        f"Location: {state.location_id}\n"
        f"Depth reached: {state.run_depth}\n"
        f"HP: {state.hp}/{state.max_hp}\n"
        f"Gold: {state.gold}\n"
        f"Prior memory: {player_memory.get('summary', '') or 'none'}\n"
        f"Shared knowledge:\n{knowledge_text or '- none'}\n\n"
        f"Player message: {player_message.strip()}\n\n"
        "Keep the reply compact and natural.\n"
        "Respond with plain in-character prose only."
    )


register_agent_builder("dialogue.reply", build_npc_dialogue_agent)
register_agent_builder("dialogue.stream", build_npc_stream_dialogue_agent)