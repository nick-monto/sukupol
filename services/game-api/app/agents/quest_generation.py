from __future__ import annotations

import logging
from typing import Any

from .quest_agents import QuestOfferContext, QuestResponseContext
from .registry import build_agent
from .runtime import AgentExecutor


logger = logging.getLogger(__name__)


class QuestGenerationService:
    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self.executor = executor or AgentExecutor()

    def generate_offer(self, context: QuestOfferContext) -> dict[str, str] | None:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return None

        try:
            payload = self.executor.invoke_json(build_agent("quest.offer", context))
        except RuntimeError:
            logger.exception("Quest offer generation failed in %s mode", self.executor.mode)
            return None

        return self._normalize_offer_payload(payload)

    def generate_response(self, context: QuestResponseContext) -> str | None:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return None

        try:
            payload = self.executor.invoke_json(build_agent("quest.response", context))
        except RuntimeError:
            logger.exception("Quest response generation failed in %s mode", self.executor.mode)
            return None

        response_text = str(payload.get("response_text", "")).strip()
        return response_text or None

    def _normalize_offer_payload(self, payload: dict[str, Any]) -> dict[str, str] | None:
        title = str(payload.get("title", "")).strip()
        summary = str(payload.get("summary", "")).strip()
        objective_text = str(payload.get("objective_text", "")).strip()
        offer_text = str(payload.get("offer_text", "")).strip()
        if not title or not summary or not objective_text or not offer_text:
            return None
        return {
            "title": title,
            "summary": summary,
            "objective_text": objective_text,
            "offer_text": offer_text,
        }