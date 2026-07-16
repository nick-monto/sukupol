from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import asdict
import logging
from typing import Any

from ..agents import (
    AgentExecutor,
    NpcDialogueToolContext,
    NpcDialogueTurnContext,
    build_agent,
    build_tools,
)
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
from . import summary as _summary
from . import visit as _visit

logger = logging.getLogger(__name__)


async def stream_setup(
    mode: str, journal_service: Any, quest_generation_service: Any,
    world: WorldContent, state: RunState, npc_id: str, player_message: str,
) -> tuple[dict[str, Any], dict[str, str], list[dict[str, Any]], Any, str]:
    await _visit.afinalize_other_active_visits(world, state, npc_id, mode, journal_service)
    npc = world.npcs[npc_id]
    player_memory = asdict(load_npc_player_memory(state.player_id, npc_id))
    shared_knowledge = [asdict(k) for k in list_npc_shared_knowledge(npc_id)]
    quest_completion = maybe_complete_quest_turn_in(
        world, state, npc_id, quest_generation_service=quest_generation_service,
    )
    source = mode if mode in {"agent-framework", "local-llm"} else "stub"
    return npc, player_memory, shared_knowledge, quest_completion, source


async def stream_emit_quest(
    npc: dict[str, Any], quest_completion: dict[str, Any],
) -> tuple[list[str], str]:
    chunks: list[str] = []
    text = f"{npc['display_name']}: {quest_completion['response_text']}"
    async for chunk in _norm.synthesize_stream_chunks(text):
        chunks.append(chunk)
    return chunks, "quest"


async def stream_emit_stub(
    npc: dict[str, Any], player_message: str, player_memory: dict[str, str],
) -> tuple[list[str], str]:
    chunks: list[str] = []
    text = _fb.fallback_response(npc, player_message, player_memory.get("summary", ""))
    async for chunk in _norm.synthesize_stream_chunks(text):
        chunks.append(chunk)
    return chunks, "stub"


def _build_stream_invocation(
    npc: dict[str, Any], player_message: str, player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]], world: WorldContent, state: RunState,
) -> Any:
    turn_context = NpcDialogueTurnContext(
        npc=npc, state=state, player_message=player_message,
        player_memory=player_memory, shared_knowledge=shared_knowledge,
    )
    tool_context = NpcDialogueToolContext(
        world=world, state=state, npc=npc,
        player_memory=player_memory, shared_knowledge=shared_knowledge,
    )
    return build_agent("dialogue.stream", turn_context, tools=build_tools("dialogue.stream", tool_context))


async def stream_emit_model(
    executor: AgentExecutor, mode: str, npc: dict[str, Any],
    player_message: str, player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]], world: WorldContent, state: RunState,
) -> tuple[list[str], str]:
    invocation = _build_stream_invocation(npc, player_message, player_memory, shared_knowledge, world, state)
    try:
        provider_chunks: list[str] = []
        async for chunk in executor.astream_text(invocation):
            provider_chunks.append(chunk)
    except RuntimeError as error:
        logger.exception("Dialogue stream provider failed in %s mode", mode)
        return await stream_error_fallback(npc, player_message, player_memory, mode, error)

    return await stream_chunk_provider_result(provider_chunks), mode


async def stream_error_fallback(
    npc: dict[str, Any], player_message: str, player_memory: dict[str, str],
    mode: str, error: RuntimeError,
) -> tuple[list[str], str]:
    chunks: list[str] = []
    source = _norm.format_fallback_source(mode, error) if mode in {"agent-framework", "local-llm"} else "stub"
    text = _fb.fallback_response(npc, player_message, player_memory.get("summary", ""))
    async for chunk in _norm.synthesize_stream_chunks(text):
        chunks.append(chunk)
    return chunks, source


async def stream_chunk_provider_result(provider_chunks: list[str]) -> list[str]:
    chunks: list[str] = []
    text = _norm.coerce_dialogue_reply_text("".join(provider_chunks))
    async for chunk in _norm.synthesize_stream_chunks(text):
        chunks.append(chunk)
    return chunks


def stream_finalize_text(
    emitted_chunks: list[str], npc: dict[str, Any],
    player_message: str, player_memory: dict[str, str],
) -> str:
    text = "".join(emitted_chunks).strip()
    text = _norm.coerce_dialogue_reply_text(text)
    if not text:
        text = _fb.fallback_response(npc, player_message, player_memory.get("summary", ""))
    return text


def stream_maybe_offer(
    text: str, quest_generation_service: Any,
    world: WorldContent, state: RunState, npc: dict[str, Any], player_message: str,
) -> tuple[str, str | None]:
    quest_offer = maybe_offer_conversation_quest(
        world, state, npc, player_message, quest_generation_service=quest_generation_service,
    )
    if quest_offer is not None:
        offer_chunk = f"\n\n{npc['display_name']}: {quest_offer['offer_text']}"
        text = f"{text.rstrip()}{offer_chunk}"
        return text, offer_chunk
    return text, None


async def stream_persist(
    mode: str, journal_service: Any, state: RunState, npc_id: str,
    npc: dict[str, Any], player_message: str, text: str, source: str,
    player_memory: dict[str, str],
) -> None:
    summary, lore_updates = await _summary.asummarize_exchange(
        mode, journal_service, npc, player_message, text, player_memory.get("summary", ""),
    )
    upsert_npc_player_memory(state.player_id, npc_id, summary, player_message.strip(), text)
    upsert_conversation_summary(state.player_id, npc_id, summary)
    for lu in lore_updates:
        upsert_npc_shared_knowledge(
            npc_id=npc_id, category=lu.get("category", "conversation"),
            content=lu.get("content", ""), source="summary",
        )
    _visit.record_visit_turn(state, npc_id, npc["display_name"], player_message, text, source)


def _complete_reply(npc_id: str, npc_name: str, text: str, source: str) -> dict[str, Any]:
    return {"type": "complete", "reply": {"npc_id": npc_id, "npc_name": npc_name, "text": text, "source": source}}


async def stream_talk(
    mode: str, executor: AgentExecutor, journal_service: Any,
    quest_generation_service: Any, world: WorldContent, state: RunState,
    npc_id: str, player_message: str,
) -> AsyncIterator[dict[str, Any]]:
    npc, pm, sk, quest_completion, source = await stream_setup(
        mode, journal_service, quest_generation_service, world, state, npc_id, player_message,
    )
    yield {"type": "start", "npc_id": npc_id, "npc_name": npc["display_name"], "source": source}
    chunks, source = await stream_collect_reply(
        executor, mode, npc, player_message, pm, sk, quest_completion, world, state,
    )
    for c in chunks:
        yield {"type": "chunk", "text": c}
    text = stream_finalize_text(chunks, npc, player_message, pm)
    text, offer = stream_maybe_offer(text, quest_generation_service, world, state, npc, player_message)
    if offer:
        yield {"type": "chunk", "text": offer}
    await stream_persist(mode, journal_service, state, npc_id, npc, player_message, text, source, pm)
    yield _complete_reply(npc_id, npc["display_name"], text, source)


async def stream_collect_reply(
    executor: AgentExecutor, mode: str, npc: dict[str, Any],
    player_message: str, player_memory: dict[str, str],
    shared_knowledge: list[dict[str, Any]], quest_completion: Any,
    world: WorldContent, state: RunState,
) -> tuple[list[str], str]:
    if quest_completion is not None:
        return await stream_emit_quest(npc, quest_completion)
    if mode == "stub":
        return await stream_emit_stub(npc, player_message, player_memory)
    return await stream_emit_model(
        executor, mode, npc, player_message, player_memory, shared_knowledge, world, state,
    )
