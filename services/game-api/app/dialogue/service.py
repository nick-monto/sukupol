from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, AsyncIterator

from ..agents import (
    AgentExecutor,
    JournalService,
    NpcDialogueToolContext,
    NpcDialogueTurnContext,
    build_agent,
    build_tools,
)
from ..agents.quest_generation import QuestGenerationService
from ..content import WorldContent
from ..db.npcs import (
    list_npc_shared_knowledge,
    load_npc_player_memory,
    upsert_conversation_summary,
    upsert_npc_player_memory,
    upsert_npc_shared_knowledge,
)
from ..game import RunState
from ..quests import maybe_complete_quest_turn_in, maybe_offer_conversation_quest

from . import fallback as _fb
from . import normalize as _norm
from . import stream as _stream
from . import summary as _summary
from . import visit as _visit

logger = logging.getLogger(__name__)


class NpcDialogueService:
    def __init__(
        self,
        executor: AgentExecutor | None = None,
        journal_service: JournalService | None = None,
        quest_generation_service: QuestGenerationService | None = None,
    ) -> None:
        self.executor = executor or AgentExecutor()
        self.mode = self.executor.mode
        self.journal_service = journal_service or JournalService(executor=self.executor)
        self.quest_generation_service = quest_generation_service

    def status(self) -> dict[str, str | None]:
        return self.executor.status()

    # ── talk ──────────────────────────────────────────────────────────

    def talk(
        self, world: WorldContent, state: RunState, npc_id: str, player_message: str,
    ) -> _norm.DialogueReply:
        _visit.finalize_other_active_visits(
            world, state, npc_id, self.mode, self.journal_service,
        )
        npc = world.npcs[npc_id]
        player_memory = asdict(load_npc_player_memory(state.player_id, npc_id))
        shared_knowledge = [asdict(k) for k in list_npc_shared_knowledge(npc_id)]
        text, source = self._talk_response(
            world, state, npc_id, npc, player_message, player_memory, shared_knowledge,
        )
        self._persist_exchange(state, npc_id, npc, player_message, text, source, player_memory)
        return _norm.DialogueReply(
            npc_id=npc_id, npc_name=npc["display_name"], text=text, source=source,
        )

    def _talk_response(
        self, world: WorldContent, state: RunState, npc_id: str, npc: dict[str, Any],
        player_message: str, player_memory: dict[str, str], shared_knowledge: list[dict[str, Any]],
    ) -> tuple[str, str]:
        quest_completion = maybe_complete_quest_turn_in(
            world, state, npc_id, quest_generation_service=self.quest_generation_service,
        )
        if quest_completion is not None:
            return f"{npc['display_name']}: {quest_completion['response_text']}", "quest"

        text, source = self._talk_model_reply(
            world, npc, state, player_message, player_memory, shared_knowledge,
        )
        text = self._maybe_append_quest_offer(text, world, state, npc, player_message)
        return text, source

    def _try_executor_reply(
        self, world: WorldContent, npc: dict[str, Any], state: RunState,
        player_message: str, player_memory: dict[str, str], shared_knowledge: list[dict[str, Any]],
    ) -> tuple[str, str]:
        if self.mode == "agent-framework":
            result = self._agent_framework_response(
                world=world, npc=npc, state=state,
                player_message=player_message, player_memory=player_memory,
                shared_knowledge=shared_knowledge,
            )
            return result.reply, "agent-framework"
        result = self._local_llm_response(
            npc=npc, state=state, player_message=player_message,
            player_memory=player_memory, shared_knowledge=shared_knowledge,
        )
        return result.reply, "local-llm"

    def _talk_model_reply(
        self, world: WorldContent, npc: dict[str, Any], state: RunState,
        player_message: str, player_memory: dict[str, str], shared_knowledge: list[dict[str, Any]],
    ) -> tuple[str, str]:
        if self.mode in {"agent-framework", "local-llm"}:
            try:
                return self._try_executor_reply(
                    world, npc, state, player_message, player_memory, shared_knowledge,
                )
            except RuntimeError as error:
                logger.exception("Dialogue provider failed in %s mode", self.mode)
                return (
                    _fb.fallback_response(npc, player_message, player_memory.get("summary", "")),
                    _norm.format_fallback_source(self.mode, error),
                )
        return _fb.fallback_response(npc, player_message, player_memory.get("summary", "")), "stub"

    def _maybe_append_quest_offer(
        self, text: str, world: WorldContent, state: RunState, npc: dict[str, Any],
        player_message: str,
    ) -> str:
        quest_offer = maybe_offer_conversation_quest(
            world, state, npc, player_message,
            quest_generation_service=self.quest_generation_service,
        )
        if quest_offer is not None:
            sep = "\n\n" if text.strip() else ""
            text = f"{text.rstrip()}{sep}{npc['display_name']}: {quest_offer['offer_text']}"
        return text

    def _persist_exchange(
        self, state: RunState, npc_id: str, npc: dict[str, Any],
        player_message: str, text: str, source: str, player_memory: dict[str, str],
    ) -> None:
        summary, lore_updates = _summary.summarize_exchange(
            self.mode, self.journal_service, npc, player_message, text,
            player_memory.get("summary", ""),
        )
        upsert_npc_player_memory(state.player_id, npc_id, summary, player_message.strip(), text)
        upsert_conversation_summary(state.player_id, npc_id, summary)
        for lu in lore_updates:
            upsert_npc_shared_knowledge(
                npc_id=npc_id, category=lu.get("category", "conversation"),
                content=lu.get("content", ""), source="summary",
            )
        _visit.record_visit_turn(state, npc_id, npc["display_name"], player_message, text, source)

    # ── stream_talk ───────────────────────────────────────────────────

    async def stream_talk(
        self, world: WorldContent, state: RunState, npc_id: str, player_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        async for event in _stream.stream_talk(
            self.mode, self.executor, self.journal_service, self.quest_generation_service,
            world, state, npc_id, player_message,
        ):
            yield event

    # ── visit lifecycle wrappers ──────────────────────────────────────

    def leave(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        return _visit.finalize_visit(world, state, npc_id, self.mode, self.journal_service)

    async def aleave(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        return await _visit.afinalize_visit(world, state, npc_id, self.mode, self.journal_service)

    def finalize_other_active_visits(
        self, world: WorldContent, state: RunState, active_npc_id: str,
    ) -> list[dict[str, Any]]:
        return _visit.finalize_other_active_visits(
            world, state, active_npc_id, self.mode, self.journal_service,
        )

    async def afinalize_other_active_visits(
        self, world: WorldContent, state: RunState, active_npc_id: str,
    ) -> list[dict[str, Any]]:
        return await _visit.afinalize_other_active_visits(
            world, state, active_npc_id, self.mode, self.journal_service,
        )

    def finalize_departed_visits(
        self, world: WorldContent, state: RunState,
    ) -> list[dict[str, Any]]:
        return _visit.finalize_departed_visits(world, state, self.mode, self.journal_service)

    def finalize_all_active_visits(
        self, world: WorldContent, state: RunState,
    ) -> list[dict[str, Any]]:
        return _visit.finalize_all_active_visits(world, state, self.mode, self.journal_service)

    def record_visit_turn(
        self, state: RunState, npc_id: str, npc_name: str,
        player_message: str, reply_text: str, source: str,
    ) -> None:
        _visit.record_visit_turn(state, npc_id, npc_name, player_message, reply_text, source)

    # ── agent model helpers (tested directly) ─────────────────────────

    def _agent_framework_response(
        self, world: WorldContent, npc: dict[str, Any], state: RunState,
        player_message: str, player_memory: dict[str, str], shared_knowledge: list[dict[str, Any]],
    ) -> _norm.ModelDialogueResult:
        turn_context = NpcDialogueTurnContext(
            npc=npc, state=state, player_message=player_message,
            player_memory=player_memory, shared_knowledge=shared_knowledge,
        )
        tool_context = NpcDialogueToolContext(
            world=world, state=state, npc=npc,
            player_memory=player_memory, shared_knowledge=shared_knowledge,
        )
        invocation = build_agent(
            "dialogue.reply", turn_context,
            tools=build_tools("dialogue.reply", tool_context),
        )
        payload = self.executor.invoke_json(invocation)
        return _norm.parse_model_dialogue_result(payload)

    def _local_llm_response(
        self, npc: dict[str, Any], state: RunState, player_message: str,
        player_memory: dict[str, str], shared_knowledge: list[dict[str, Any]],
    ) -> _norm.ModelDialogueResult:
        turn_context = NpcDialogueTurnContext(
            npc=npc, state=state, player_message=player_message,
            player_memory=player_memory, shared_knowledge=shared_knowledge,
        )
        invocation = build_agent("dialogue.reply", turn_context)
        payload = self.executor.invoke_json(invocation)
        return _norm.parse_model_dialogue_result(payload)
