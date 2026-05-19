from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator

from .agents import (
    AgentExecutor,
    JournalService,
    NpcDialogueToolContext,
    NpcDialogueTurnContext,
    build_agent,
    build_tools,
)
from .agents.quest_generation import QuestGenerationService
from .agents.providers import extract_json_payload
from .content import WorldContent
from .db import (
    create_npc_journal_entry,
    list_npc_shared_knowledge,
    load_npc_player_memory,
    utc_now,
    upsert_conversation_summary,
    upsert_npc_player_memory,
    upsert_npc_shared_knowledge,
)
from .game import RunState, nearby_npcs
from .quests import maybe_complete_quest_turn_in, maybe_offer_conversation_quest


logger = logging.getLogger(__name__)

MAX_DIALOGUE_SENTENCES = 2
MAX_DIALOGUE_WORDS = 36
MAX_DIALOGUE_CHARS = 220


@dataclass
class DialogueReply:
    npc_id: str
    npc_name: str
    text: str
    source: str


@dataclass
class ModelDialogueResult:
    reply: str


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

    def talk(self, world: WorldContent, state: RunState, npc_id: str, player_message: str) -> DialogueReply:
        self.finalize_other_active_visits(world, state, npc_id)
        npc = world.npcs[npc_id]
        player_memory = load_npc_player_memory(state.player_id, npc_id)
        shared_knowledge = list_npc_shared_knowledge(npc_id)

        quest_completion = maybe_complete_quest_turn_in(
            world,
            state,
            npc_id,
            quest_generation_service=self.quest_generation_service,
        )
        if quest_completion is not None:
            text = f"{npc['display_name']}: {quest_completion['response_text']}"
            source = "quest"
        else:
            if self.mode in {"agent-framework", "local-llm"}:
                try:
                    if self.mode == "agent-framework":
                        model_result = self._agent_framework_response(
                            world=world,
                            npc=npc,
                            state=state,
                            player_message=player_message,
                            player_memory=player_memory,
                            shared_knowledge=shared_knowledge,
                        )
                        source = "agent-framework"
                    else:
                        model_result = self._local_llm_response(
                            npc=npc,
                            state=state,
                            player_message=player_message,
                            player_memory=player_memory,
                            shared_knowledge=shared_knowledge,
                        )
                        source = "local-llm"
                    text = model_result.reply
                except RuntimeError as error:
                    logger.exception("Dialogue provider failed in %s mode", self.mode)
                    text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
                    source = format_fallback_source(self.mode, error)
            else:
                text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
                source = "stub"

        if quest_completion is None:
            quest_offer = maybe_offer_conversation_quest(
                world,
                state,
                npc,
                player_message,
                quest_generation_service=self.quest_generation_service,
            )
            if quest_offer is not None:
                separator = "\n\n" if text.strip() else ""
                text = f"{text.rstrip()}{separator}{npc['display_name']}: {quest_offer['offer_text']}"

        summary, lore_updates = self._summarize_exchange(
            npc=npc,
            player_message=player_message,
            reply_text=text,
            prior_summary=player_memory.get("summary", ""),
        )
        upsert_npc_player_memory(state.player_id, npc_id, summary, player_message.strip(), text)
        upsert_conversation_summary(state.player_id, npc_id, summary)
        for lore_update in lore_updates:
            upsert_npc_shared_knowledge(
                npc_id=npc_id,
                category=lore_update.get("category", "conversation"),
                content=lore_update.get("content", ""),
                source="summary",
            )
        self.record_visit_turn(state, npc_id, npc["display_name"], player_message, text, source)
        return DialogueReply(
            npc_id=npc_id,
            npc_name=npc["display_name"],
            text=text,
            source=source,
        )

    async def stream_talk(
        self,
        world: WorldContent,
        state: RunState,
        npc_id: str,
        player_message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        await self.afinalize_other_active_visits(world, state, npc_id)
        npc = world.npcs[npc_id]
        player_memory = load_npc_player_memory(state.player_id, npc_id)
        shared_knowledge = list_npc_shared_knowledge(npc_id)
        turn_context = NpcDialogueTurnContext(
            npc=npc,
            state=state,
            player_message=player_message,
            player_memory=player_memory,
            shared_knowledge=shared_knowledge,
        )
        invocation = build_agent(
            "dialogue.stream",
            turn_context,
            tools=build_tools(
                "dialogue.stream",
                NpcDialogueToolContext(
                    world=world,
                    state=state,
                    npc=npc,
                    player_memory=player_memory,
                    shared_knowledge=shared_knowledge,
                ),
            ),
        )
        source = self.mode if self.mode in {"agent-framework", "local-llm"} else "stub"

        quest_completion = maybe_complete_quest_turn_in(
            world,
            state,
            npc_id,
            quest_generation_service=self.quest_generation_service,
        )

        yield {
            "type": "start",
            "npc_id": npc_id,
            "npc_name": npc["display_name"],
            "source": source,
        }

        emitted_chunks: list[str] = []
        if quest_completion is not None:
            completion_text = f"{npc['display_name']}: {quest_completion['response_text']}"
            async for chunk in synthesize_stream_chunks(completion_text):
                emitted_chunks.append(chunk)
                yield {"type": "chunk", "text": chunk}
            source = "quest"
        elif self.mode == "stub":
            fallback_text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
            async for chunk in synthesize_stream_chunks(fallback_text):
                emitted_chunks.append(chunk)
                yield {"type": "chunk", "text": chunk}

        try:
            if self.mode in {"agent-framework", "local-llm"}:
                provider_chunks: list[str] = []
                async for chunk in self.executor.astream_text(invocation):
                    provider_chunks.append(chunk)
                provider_text = coerce_dialogue_reply_text("".join(provider_chunks))
                async for chunk in synthesize_stream_chunks(provider_text):
                    emitted_chunks.append(chunk)
                    yield {"type": "chunk", "text": chunk}
                source = self.mode
            elif self.mode != "stub":
                raise RuntimeError(f"unsupported dialogue mode: {self.mode}")
        except RuntimeError as error:
            logger.exception("Dialogue stream provider failed in %s mode", self.mode)
            source = format_fallback_source(self.mode, error) if self.mode in {"agent-framework", "local-llm"} else "stub"
            if quest_completion is None and self.mode != "stub":
                emitted_chunks = []
                fallback_text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))
                async for chunk in synthesize_stream_chunks(fallback_text):
                    emitted_chunks.append(chunk)
                    yield {"type": "chunk", "text": chunk}

        text = "".join(emitted_chunks).strip()
        text = coerce_dialogue_reply_text(text)
        if not text:
            text = self._fallback_response(npc, player_message, player_memory.get("summary", ""))

        if quest_completion is None:
            quest_offer = maybe_offer_conversation_quest(
                world,
                state,
                npc,
                player_message,
                quest_generation_service=self.quest_generation_service,
            )
            if quest_offer is not None:
                offer_chunk = f"\n\n{npc['display_name']}: {quest_offer['offer_text']}"
                text = f"{text.rstrip()}{offer_chunk}"
                yield {"type": "chunk", "text": offer_chunk}

        summary, lore_updates = await self._asummarize_exchange(
            npc=npc,
            player_message=player_message,
            reply_text=text,
            prior_summary=player_memory.get("summary", ""),
        )
        upsert_npc_player_memory(state.player_id, npc_id, summary, player_message.strip(), text)
        upsert_conversation_summary(state.player_id, npc_id, summary)
        for lore_update in lore_updates:
            upsert_npc_shared_knowledge(
                npc_id=npc_id,
                category=lore_update.get("category", "conversation"),
                content=lore_update.get("content", ""),
                source="summary",
            )
        self.record_visit_turn(state, npc_id, npc["display_name"], player_message, text, source)

        yield {
            "type": "complete",
            "reply": {
                "npc_id": npc_id,
                "npc_name": npc["display_name"],
                "text": text,
                "source": source,
            },
        }

    def leave(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        return self._finalize_visit(world, state, npc_id)

    async def aleave(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        return await self._afinalize_visit(world, state, npc_id)

    def finalize_other_active_visits(self, world: WorldContent, state: RunState, active_npc_id: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            if npc_id == active_npc_id:
                continue
            entry = self._finalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    async def afinalize_other_active_visits(self, world: WorldContent, state: RunState, active_npc_id: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            if npc_id == active_npc_id:
                continue
            entry = await self._afinalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    def finalize_departed_visits(self, world: WorldContent, state: RunState) -> list[dict[str, Any]]:
        nearby_ids = {npc["id"] for npc in nearby_npcs(world, state)}
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            if npc_id in nearby_ids:
                continue
            entry = self._finalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    def finalize_all_active_visits(self, world: WorldContent, state: RunState) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        visits = state.active_dialogue_visits or {}
        for npc_id in list(visits.keys()):
            entry = self._finalize_visit(world, state, npc_id)
            if entry is not None:
                entries.append(entry)
        return entries

    def record_visit_turn(
        self,
        state: RunState,
        npc_id: str,
        npc_name: str,
        player_message: str,
        reply_text: str,
        source: str,
    ) -> None:
        visits = state.active_dialogue_visits or {}
        now = utc_now()
        visit = visits.get(npc_id)
        if not isinstance(visit, dict):
            visit = {
                "npc_id": npc_id,
                "npc_name": npc_name,
                "started_at": now,
                "updated_at": now,
                "turns": [],
            }

        turns = visit.get("turns")
        if not isinstance(turns, list):
            turns = []
            visit["turns"] = turns

        turns.append(
            {
                "player_message": player_message.strip(),
                "npc_reply": reply_text.strip(),
                "source": source,
                "timestamp": now,
            }
        )
        visit["npc_id"] = npc_id
        visit["npc_name"] = npc_name
        visit["updated_at"] = now
        visits[npc_id] = visit
        state.active_dialogue_visits = visits

    def _finalize_visit(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        visits = state.active_dialogue_visits or {}
        visit = visits.get(npc_id)
        if not isinstance(visit, dict):
            return None

        turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
        visits.pop(npc_id, None)
        state.active_dialogue_visits = visits
        if not turns:
            return None

        npc = world.npcs.get(npc_id, {"id": npc_id, "display_name": visit.get("npc_name", npc_id), "role": "contact"})
        visit_ended_at = utc_now()
        summary = self._summarize_visit(npc, visit, visit_ended_at)
        return create_npc_journal_entry(
            player_id=state.player_id,
            npc_id=npc_id,
            run_id=state.id,
            summary=summary,
            visit_started_at=str(visit.get("started_at") or visit_ended_at),
            visit_ended_at=visit_ended_at,
            turn_count=len(turns),
        )

    async def _afinalize_visit(self, world: WorldContent, state: RunState, npc_id: str) -> dict[str, Any] | None:
        visits = state.active_dialogue_visits or {}
        visit = visits.get(npc_id)
        if not isinstance(visit, dict):
            return None

        turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
        visits.pop(npc_id, None)
        state.active_dialogue_visits = visits
        if not turns:
            return None

        npc = world.npcs.get(npc_id, {"id": npc_id, "display_name": visit.get("npc_name", npc_id), "role": "contact"})
        visit_ended_at = utc_now()
        summary = await self._asummarize_visit(npc, visit, visit_ended_at)
        return create_npc_journal_entry(
            player_id=state.player_id,
            npc_id=npc_id,
            run_id=state.id,
            summary=summary,
            visit_started_at=str(visit.get("started_at") or visit_ended_at),
            visit_ended_at=visit_ended_at,
            turn_count=len(turns),
        )

    def _agent_framework_response(
        self,
        world: WorldContent,
        npc: dict[str, Any],
        state: RunState,
        player_message: str,
        player_memory: dict[str, str],
        shared_knowledge: list[dict[str, Any]],
    ) -> ModelDialogueResult:
        turn_context = NpcDialogueTurnContext(
            npc=npc,
            state=state,
            player_message=player_message,
            player_memory=player_memory,
            shared_knowledge=shared_knowledge,
        )
        invocation = build_agent(
            "dialogue.reply",
            turn_context,
            tools=build_tools(
                "dialogue.reply",
                NpcDialogueToolContext(
                    world=world,
                    state=state,
                    npc=npc,
                    player_memory=player_memory,
                    shared_knowledge=shared_knowledge,
                ),
            ),
        )
        payload = self.executor.invoke_json(invocation)
        return parse_model_dialogue_result(payload)

    def _local_llm_response(
        self,
        npc: dict[str, Any],
        state: RunState,
        player_message: str,
        player_memory: dict[str, str],
        shared_knowledge: list[dict[str, Any]],
    ) -> ModelDialogueResult:
        invocation = build_agent(
            "dialogue.reply",
            NpcDialogueTurnContext(
                npc=npc,
                state=state,
                player_message=player_message,
                player_memory=player_memory,
                shared_knowledge=shared_knowledge,
            ),
        )
        payload = self.executor.invoke_json(invocation)
        return parse_model_dialogue_result(payload)

    def _summarize_exchange(
        self,
        npc: dict[str, Any],
        player_message: str,
        reply_text: str,
        prior_summary: str,
    ) -> tuple[str, list[dict[str, str]]]:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        payload = self.journal_service.summarize_exchange(npc, player_message, reply_text, prior_summary)
        if payload is None:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        summary = str(payload.get("summary", "")).strip() or self._fallback_summary(player_message, reply_text, prior_summary)
        lore_updates = payload.get("lore_updates", [])
        if not isinstance(lore_updates, list):
            lore_updates = []

        normalized_lore: list[dict[str, str]] = []
        for entry in lore_updates[:4]:
            if not isinstance(entry, dict):
                continue
            category = str(entry.get("category", "conversation")).strip()
            content = str(entry.get("content", "")).strip()
            if not content:
                continue
            normalized_lore.append({"category": category, "content": content})
        return summary, normalized_lore

    async def _asummarize_exchange(
        self,
        npc: dict[str, Any],
        player_message: str,
        reply_text: str,
        prior_summary: str,
    ) -> tuple[str, list[dict[str, str]]]:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        payload = await self.journal_service.asummarize_exchange(npc, player_message, reply_text, prior_summary)
        if payload is None:
            return self._fallback_summary(player_message, reply_text, prior_summary), []

        summary = str(payload.get("summary", "")).strip() or self._fallback_summary(player_message, reply_text, prior_summary)
        lore_updates = payload.get("lore_updates", [])
        if not isinstance(lore_updates, list):
            lore_updates = []

        normalized_lore: list[dict[str, str]] = []
        for entry in lore_updates[:4]:
            if not isinstance(entry, dict):
                continue
            category = str(entry.get("category", "conversation")).strip()
            content = str(entry.get("content", "")).strip()
            if not content:
                continue
            normalized_lore.append({"category": category, "content": content})
        return summary, normalized_lore

    def _fallback_response(self, npc: dict[str, str], player_message: str, prior_summary: str) -> str:
        message = player_message.lower()
        prefix = f"{npc['display_name']}: "
        if "dungeon" in message or "depth" in message:
            body = npc["dungeon_hint"]
        elif "town" in message or "sukupol" in message:
            body = npc["town_hint"]
        elif "supply" in message or "food" in message or "gear" in message:
            body = npc["supply_hint"]
        else:
            body = npc["greeting"]

        if prior_summary:
            body = f"{body} We have spoken recently, and I have not forgotten it."

        return prefix + body

    def _fallback_summary(self, player_message: str, reply_text: str, prior_summary: str) -> str:
        latest = f"Player asked about '{player_message.strip()}'. NPC replied '{reply_text.strip()}'."
        if prior_summary:
            return f"{prior_summary} {latest}"[:600]
        return latest[:600]

    def _summarize_visit(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> str:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_visit_summary(npc, visit)

        payload = self.journal_service.summarize_visit(npc, visit, visit_ended_at)
        if payload is None:
            return self._fallback_visit_summary(npc, visit)

        summary = str(payload.get("summary", "")).strip()
        return summary or self._fallback_visit_summary(npc, visit)

    async def _asummarize_visit(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> str:
        if self.mode not in {"agent-framework", "local-llm"}:
            return self._fallback_visit_summary(npc, visit)

        payload = await self.journal_service.asummarize_visit(npc, visit, visit_ended_at)
        if payload is None:
            return self._fallback_visit_summary(npc, visit)

        summary = str(payload.get("summary", "")).strip()
        return summary or self._fallback_visit_summary(npc, visit)

    def _fallback_visit_summary(self, npc: dict[str, Any], visit: dict[str, Any]) -> str:
        turns = visit.get("turns") if isinstance(visit.get("turns"), list) else []
        if not turns:
            return f"Visited {npc.get('display_name', visit.get('npc_name', 'this contact'))}, but no details were recorded."

        opening = turns[0] if isinstance(turns[0], dict) else {}
        closing = turns[-1] if isinstance(turns[-1], dict) else {}
        first_topic = str(opening.get("player_message", "")).strip() or "general matters"
        closing_reply = str(closing.get("npc_reply", "")).strip() or "they gave no clear closing remark"
        npc_name = npc.get("display_name", visit.get("npc_name", "This contact"))
        summary = (
            f"I spoke with {npc_name} about {first_topic}. "
            f"The discussion covered {len(turns)} exchange{'s' if len(turns) != 1 else ''}, and they closed by saying: {closing_reply}"
        )
        return summary[:600]


def format_fallback_source(mode: str, error: Exception) -> str:
    detail = str(error).strip().replace("\n", " ")
    if len(detail) > 96:
        detail = f"{detail[:93]}..."
    return f"{mode}-fallback: {detail}" if detail else f"{mode}-fallback"


def parse_model_dialogue_result(payload: dict[str, Any]) -> ModelDialogueResult:
    reply = ""
    for key in ("reply", "text", "response_text", "content", "message"):
        value = payload.get(key)
        if isinstance(value, dict):
            value = value.get("content") or value.get("text")
        candidate = str(value or "").strip()
        if candidate:
            reply = candidate
            break
    if not reply:
        raise RuntimeError("Dialogue provider returned an empty reply")
    return ModelDialogueResult(reply=coerce_dialogue_reply_text(reply))


def coerce_dialogue_reply_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped

    try:
        payload = extract_json_payload(stripped)
    except RuntimeError:
        return normalize_npc_reply_text(stripped)

    reply = payload.get("reply")
    if reply is None:
        return normalize_npc_reply_text(stripped)

    normalized = str(reply).strip()
    return normalize_npc_reply_text(normalized or stripped)


def normalize_npc_reply_text(text: str) -> str:
    compact = " ".join(text.split())
    if not compact:
        return compact

    word_count = len(compact.split())
    sentence_candidates = [match.strip() for match in re.findall(r"[^.!?]+(?:[.!?]+|$)", compact) if match.strip()]
    if (
        len(sentence_candidates) <= MAX_DIALOGUE_SENTENCES
        and word_count <= MAX_DIALOGUE_WORDS
        and len(compact) <= MAX_DIALOGUE_CHARS
    ):
        return compact

    truncated = compact
    if sentence_candidates:
        truncated = " ".join(sentence_candidates[:MAX_DIALOGUE_SENTENCES]).strip()

    words = truncated.split()
    if len(words) > MAX_DIALOGUE_WORDS:
        truncated = " ".join(words[:MAX_DIALOGUE_WORDS]).strip()

    if truncated and truncated[-1].isalnum() and truncated != compact:
        truncated = f"{truncated}."
    return truncated or compact


async def synthesize_stream_chunks(text: str) -> AsyncIterator[str]:
    for chunk in split_text_for_stream(text):
        yield chunk
        await asyncio.sleep(0.012)


def split_text_for_stream(text: str, target_size: int = 18) -> list[str]:
    words = text.split(" ")
    if len(words) <= 1:
        return [text]

    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) > target_size and current:
            chunks.append(f"{current} ")
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


