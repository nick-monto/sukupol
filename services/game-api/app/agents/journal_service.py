from __future__ import annotations

import logging
from typing import Any

from .journal_agents import ExchangeSummaryContext, VisitSummaryContext
from .registry import build_agent
from .runtime import AgentExecutor


logger = logging.getLogger(__name__)


class JournalService:
    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self.executor = executor or AgentExecutor()

    def summarize_exchange(
        self,
        npc: dict[str, Any],
        player_message: str,
        reply_text: str,
        prior_summary: str,
    ) -> dict[str, Any] | None:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return None

        try:
            return self.executor.invoke_json(
                build_agent(
                    "journal.summary.exchange",
                    ExchangeSummaryContext(
                        npc=npc,
                        player_message=player_message,
                        reply_text=reply_text,
                        prior_summary=prior_summary,
                    ),
                )
            )
        except RuntimeError:
            logger.exception("Journal exchange summary failed in %s mode", self.executor.mode)
            return None

    async def asummarize_exchange(
        self,
        npc: dict[str, Any],
        player_message: str,
        reply_text: str,
        prior_summary: str,
    ) -> dict[str, Any] | None:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return None

        try:
            return await self.executor.ainvoke_json(
                build_agent(
                    "journal.summary.exchange",
                    ExchangeSummaryContext(
                        npc=npc,
                        player_message=player_message,
                        reply_text=reply_text,
                        prior_summary=prior_summary,
                    ),
                )
            )
        except RuntimeError:
            logger.exception("Async journal exchange summary failed in %s mode", self.executor.mode)
            return None

    def summarize_visit(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> dict[str, Any] | None:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return None

        try:
            return self.executor.invoke_json(
                build_agent(
                    "journal.summary.visit",
                    VisitSummaryContext(npc=npc, visit=visit, visit_ended_at=visit_ended_at),
                )
            )
        except RuntimeError:
            logger.exception("Journal visit summary failed in %s mode", self.executor.mode)
            return None

    async def asummarize_visit(self, npc: dict[str, Any], visit: dict[str, Any], visit_ended_at: str) -> dict[str, Any] | None:
        if self.executor.mode not in {"agent-framework", "local-llm"}:
            return None

        try:
            return await self.executor.ainvoke_json(
                build_agent(
                    "journal.summary.visit",
                    VisitSummaryContext(npc=npc, visit=visit, visit_ended_at=visit_ended_at),
                )
            )
        except RuntimeError:
            logger.exception("Async journal visit summary failed in %s mode", self.executor.mode)
            return None