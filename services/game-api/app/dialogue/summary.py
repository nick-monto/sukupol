from __future__ import annotations

from typing import Any

from .fallback import fallback_summary, fallback_visit_summary
from ..agents.validate import validate_authored_text



def _normalize_lore_updates(lore_updates: Any) -> list[dict[str, str]]:
    if not isinstance(lore_updates, list):
        return []
    normalized: list[dict[str, str]] = []
    for entry in lore_updates[:4]:
        if not isinstance(entry, dict):
            continue
        category = validate_authored_text(str(entry.get("category", "conversation")), max_len=120)
        content = validate_authored_text(str(entry.get("content", "")), max_len=300)
        if category is None or content is None:
            continue
        normalized.append({"category": category, "content": content})
    return normalized


def summarize_exchange(
    mode: str,
    journal_service: Any,
    npc: dict[str, Any],
    player_message: str,
    reply_text: str,
    prior_summary: str,
) -> tuple[str, list[dict[str, str]]]:
    if mode not in {"agent-framework", "local-llm"}:
        return fallback_summary(player_message, reply_text, prior_summary), []

    payload = journal_service.summarize_exchange(npc, player_message, reply_text, prior_summary)
    if payload is None:
        return fallback_summary(player_message, reply_text, prior_summary), []

    summary = str(payload.get("summary", "")).strip() or fallback_summary(player_message, reply_text, prior_summary)
    lore_updates = _normalize_lore_updates(payload.get("lore_updates", []))
    return summary, lore_updates


async def asummarize_exchange(
    mode: str,
    journal_service: Any,
    npc: dict[str, Any],
    player_message: str,
    reply_text: str,
    prior_summary: str,
) -> tuple[str, list[dict[str, str]]]:
    if mode not in {"agent-framework", "local-llm"}:
        return fallback_summary(player_message, reply_text, prior_summary), []

    payload = await journal_service.asummarize_exchange(npc, player_message, reply_text, prior_summary)
    if payload is None:
        return fallback_summary(player_message, reply_text, prior_summary), []

    summary = str(payload.get("summary", "")).strip() or fallback_summary(player_message, reply_text, prior_summary)
    lore_updates = _normalize_lore_updates(payload.get("lore_updates", []))
    return summary, lore_updates


def summarize_visit(
    mode: str,
    journal_service: Any,
    npc: dict[str, Any],
    visit: dict[str, Any],
    visit_ended_at: str,
) -> str:
    if mode not in {"agent-framework", "local-llm"}:
        return fallback_visit_summary(npc, visit)

    payload = journal_service.summarize_visit(npc, visit, visit_ended_at)
    if payload is None:
        return fallback_visit_summary(npc, visit)

    summary = str(payload.get("summary", "")).strip()
    return summary or fallback_visit_summary(npc, visit)


async def asummarize_visit(
    mode: str,
    journal_service: Any,
    npc: dict[str, Any],
    visit: dict[str, Any],
    visit_ended_at: str,
) -> str:
    if mode not in {"agent-framework", "local-llm"}:
        return fallback_visit_summary(npc, visit)

    payload = await journal_service.asummarize_visit(npc, visit, visit_ended_at)
    if payload is None:
        return fallback_visit_summary(npc, visit)

    summary = str(payload.get("summary", "")).strip()
    return summary or fallback_visit_summary(npc, visit)
