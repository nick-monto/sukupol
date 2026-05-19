from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..game import RunState
from .registry import register_agent_builder
from .runtime import AgentInvocation


@dataclass(frozen=True)
class CombatParleyContext:
    enemy_def: dict[str, Any]
    state: RunState
    combat_state: dict[str, Any]
    negotiation: dict[str, Any]
    player_message: str = ""
    heuristic_reply: str = ""
    inferred_intent: str | None = None
    leverage_delta: int = 0
    anger_delta: int = 0
    grants_pause: bool = False
    provoked: bool = False


def build_combat_parley_open_agent(context: CombatParleyContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"combat-parley-open-{context.enemy_def['id']}",
        instructions=(
            f"You are {context.enemy_def['name']} during a live combat parley. "
            "Reply in one or two concise in-character sentences only. "
            "Acknowledge that the player has opened negotiations, stay grounded in the exact combat state, and do not resolve combat or promise outcomes."
        ),
        user_prompt=(
            f"Enemy: {context.enemy_def['name']}\n"
            f"Enemy description: {context.enemy_def.get('description', 'unknown')}\n"
            f"Communication mode: {context.negotiation.get('communication_mode', 'speech')}\n"
            f"Temperament: {context.negotiation.get('temperament', 'wary')}\n"
            f"Player: {context.state.player_name}\n"
            f"Player HP: {context.state.hp}/{context.state.max_hp}\n"
            "The player has called for terms. Reply as the enemy opening the parley."
        ),
        tools=tools,
    )


def build_combat_parley_reply_agent(context: CombatParleyContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"combat-parley-reply-{context.enemy_def['id']}",
        instructions=(
            f"You are {context.enemy_def['name']} replying during a live combat parley. "
            "Reply in one or two concise in-character sentences only. "
            "Do not resolve combat, do not announce mechanics, and do not promise outcomes beyond the current posture. "
            "Your reply must match the provided negotiation reaction signal exactly in tone and pressure."
        ),
        user_prompt=(
            f"Enemy: {context.enemy_def['name']}\n"
            f"Enemy description: {context.enemy_def.get('description', 'unknown')}\n"
            f"Temperament: {context.negotiation.get('temperament', 'wary')}\n"
            f"Player line: {context.player_message.strip()}\n"
            f"Current active intent: {context.inferred_intent or context.negotiation.get('active_intent') or 'none'}\n"
            f"Leverage delta: {context.leverage_delta}\n"
            f"Anger delta: {context.anger_delta}\n"
            f"Grants pause: {context.grants_pause}\n"
            f"Provoked: {context.provoked}\n"
            f"Required reaction: {context.heuristic_reply.strip()}\n"
            "Rephrase that reaction as the enemy's immediate response."
        ),
        tools=tools,
    )


register_agent_builder("combat.parley_open", build_combat_parley_open_agent)
register_agent_builder("combat.parley_reply", build_combat_parley_reply_agent)