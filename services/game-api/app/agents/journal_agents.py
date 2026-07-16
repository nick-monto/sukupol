from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry import register_agent_builder
from .runtime import AgentInvocation

from .sanitize import sanitize_prompt_input


JOURNAL_SUMMARY_AGENT_NAME = "Journal Summary"


@dataclass(frozen=True)
class ExchangeSummaryContext:
    npc: dict[str, Any]
    player_message: str
    reply_text: str
    prior_summary: str


@dataclass(frozen=True)
class VisitSummaryContext:
    npc: dict[str, Any]
    visit: dict[str, Any]
    visit_ended_at: str


def build_exchange_summary_agent(context: ExchangeSummaryContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=f"npc-summary-{context.npc['id']}",
        instructions=(
            "Summarize one NPC conversation turn for future retrieval. "
            "Return strict JSON with keys: summary, lore_updates. "
            "summary must be a compact memory for this player and NPC. lore_updates must be an array of objects with category and content for durable non-player-specific facts only."
        ),
        user_prompt=(
            f"NPC: {sanitize_prompt_input(context.npc['display_name'])}\n"
            f"Prior memory: {sanitize_prompt_input(context.prior_summary) or 'none'}\n"
            f"Player said: {sanitize_prompt_input(context.player_message)}\n"
            f"NPC replied: {sanitize_prompt_input(context.reply_text)}\n"
            "Do not include ephemeral phrasing or duplicate persona facts already obvious from the character description."
        ),
        tools=tools,
    )


def build_visit_summary_agent(context: VisitSummaryContext, tools: tuple[Any, ...] = ()) -> AgentInvocation:
    return AgentInvocation(
        agent_name=JOURNAL_SUMMARY_AGENT_NAME,
        instructions=(
            "You are Journal Summary. Write one player-facing journal entry for a completed visit with an NPC. "
            "Return strict JSON with key: summary. "
            "summary must be 2 to 4 sentences in past tense, focused on what was discussed, any offers or warnings, and unresolved leads from this visit only. "
            "Do not invent facts, do not repeat generic character description, and do not mention the existence of an AI or model."
        ),
        user_prompt=build_visit_summary_prompt(context.npc, context.visit, context.visit_ended_at),
        tools=tools,
    )


def build_visit_summary_prompt(npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> str:
    raw_turns = visit.get("turns")
    turns: list[dict[str, Any]] = raw_turns if isinstance(raw_turns, list) else []
    formatted_turns: list[str] = []
    for index, turn in enumerate(turns[-8:], start=max(len(turns) - 7, 1)):
        if not isinstance(turn, dict):
            continue
        player_message = sanitize_prompt_input(str(turn.get("player_message", "")))
        npc_reply = sanitize_prompt_input(str(turn.get("npc_reply", "")))
        if not player_message and not npc_reply:
            continue
        formatted_turns.append(
            f"Turn {index}:\nPlayer: {player_message or '...'}\nNPC: {npc_reply or '...'}"
        )

    transcript = "\n\n".join(formatted_turns) or "No transcript available."
    return (
        f"NPC: {sanitize_prompt_input(str(npc.get('display_name', visit.get('npc_name', 'Unknown contact'))))}\n"
        f"Role: {sanitize_prompt_input(str(npc.get('role', 'contact')))}\n"
        f"Visit started: {sanitize_prompt_input(str(visit.get('started_at') or 'unknown'))}\n"
        f"Visit ended: {sanitize_prompt_input(visit_ended_at)}\n"
        f"Turn count: {len(turns)}\n\n"
        f"Transcript:\n{transcript}"
    )


register_agent_builder("journal.summary.exchange", build_exchange_summary_agent)
register_agent_builder("journal.summary.visit", build_visit_summary_agent)
register_agent_builder("dialogue.summary.exchange", build_exchange_summary_agent)
register_agent_builder("dialogue.summary.visit", build_visit_summary_agent)