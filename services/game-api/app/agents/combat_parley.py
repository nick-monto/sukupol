from __future__ import annotations

import logging

from ..content import WorldContent
from ..game import RunState
from .combat_agents import CombatParleyContext
from .combat_tools import CombatParleyToolContext
from .registry import build_agent, build_tools
from .runtime import AgentExecutor


logger = logging.getLogger(__name__)


class CombatParleyService:
    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self.executor = executor or AgentExecutor()

    def generate_open_line(
        self,
        world: WorldContent,
        state: RunState,
        combat_state: dict,
        enemy_def: dict,
        negotiation: dict,
    ) -> str:
        fallback = (
            f"You open parley. {enemy_def['name']} answers by {negotiation['communication_mode']}, "
            "waiting for your terms."
        )
        return self._generate_text(
            agent_key="combat.parley_open",
            context=CombatParleyContext(
                enemy_def=enemy_def,
                state=state,
                combat_state=combat_state,
                negotiation=negotiation,
            ),
            tool_context=CombatParleyToolContext(
                world=world,
                state=state,
                combat_state=combat_state,
                enemy_def=enemy_def,
                negotiation=negotiation,
            ),
            fallback=fallback,
        )

    def generate_reply(
        self,
        world: WorldContent,
        state: RunState,
        combat_state: dict,
        enemy_def: dict,
        negotiation: dict,
        player_message: str,
        analysis: dict,
    ) -> str:
        fallback = str(analysis.get("reply", "")).strip()
        return self._generate_text(
            agent_key="combat.parley_reply",
            context=CombatParleyContext(
                enemy_def=enemy_def,
                state=state,
                combat_state=combat_state,
                negotiation=negotiation,
                player_message=player_message,
                heuristic_reply=fallback,
                inferred_intent=analysis.get("inferred_intent"),
                leverage_delta=int(analysis.get("leverage_delta", 0)),
                anger_delta=int(analysis.get("anger_delta", 0)),
                grants_pause=bool(analysis.get("grants_pause", False)),
                provoked=bool(analysis.get("provoked", False)),
            ),
            tool_context=CombatParleyToolContext(
                world=world,
                state=state,
                combat_state=combat_state,
                enemy_def=enemy_def,
                negotiation=negotiation,
            ),
            fallback=fallback,
        )

    def _generate_text(self, agent_key: str, context: CombatParleyContext, tool_context: CombatParleyToolContext, fallback: str) -> str:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return fallback

        try:
            invocation = build_agent(agent_key, context, tools=build_tools(agent_key, tool_context))
            text = self.executor.invoke_text(invocation).strip()
        except RuntimeError:
            logger.exception("Combat parley provider failed in %s mode", self.executor.mode)
            return fallback

        return text or fallback