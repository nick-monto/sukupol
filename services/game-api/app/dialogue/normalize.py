from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, AsyncIterator

from ..agents.providers import extract_json_payload


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


def format_fallback_source(mode: str, error: Exception) -> str:
    """Return a generic fallback source string, omitting error detail
    to avoid leaking internals to the client (audit AF1)."""
    return f"{mode}-fallback"


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


def _truncate_text(compact: str, sentence_candidates: list[str]) -> str:
    truncated = compact
    if sentence_candidates:
        truncated = " ".join(sentence_candidates[:MAX_DIALOGUE_SENTENCES]).strip()
    words = truncated.split()
    if len(words) > MAX_DIALOGUE_WORDS:
        truncated = " ".join(words[:MAX_DIALOGUE_WORDS]).strip()
    if truncated and truncated[-1].isalnum() and truncated != compact:
        truncated = f"{truncated}."
    return truncated or compact


def normalize_npc_reply_text(text: str) -> str:
    compact = " ".join(text.split())
    if not compact:
        return compact

    word_count = len(compact.split())
    sentence_candidates = [m.strip() for m in re.findall(r"[^.!?]+(?:[.!?]+|$)", compact) if m.strip()]
    if (
        len(sentence_candidates) <= MAX_DIALOGUE_SENTENCES
        and word_count <= MAX_DIALOGUE_WORDS
        and len(compact) <= MAX_DIALOGUE_CHARS
    ):
        return compact

    return _truncate_text(compact, sentence_candidates)


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
