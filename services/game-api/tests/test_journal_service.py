from __future__ import annotations

import asyncio
import unittest
from typing import Any

from app.agents import AgentExecutor, AgentInvocation, JournalService


class _FakeJournalExecutor(AgentExecutor):
    """Fake AgentExecutor that captures calls and returns a configurable payload."""

    def __init__(self, return_value: dict[str, Any] | None = None) -> None:
        super().__init__(mode="agent-framework")
        self.return_value = return_value or {
            "summary": "Marta recalled the cave.",
            "lore_updates": [{"category": "rumor", "content": "x"}],
        }
        self.calls: list[dict[str, object]] = []

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        self.calls.append({"agent_name": invocation.agent_name})
        return self.return_value

    async def ainvoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        self.calls.append({"agent_name": invocation.agent_name})
        return self.return_value


class JournalServiceTests(unittest.TestCase):
    """JournalService seam tests — stub guard, sync, async parity, malformed payload."""

    def setUp(self) -> None:
        self.npc: dict[str, Any] = {"id": "marta", "display_name": "Marta", "role": "guide"}
        self.player_message: str = "What lies ahead?"
        self.reply_text: str = "Marta: The road is treacherous."
        self.prior_summary: str = ""
        self.visit: dict[str, Any] = {"started_at": "2026-07-15T10:00:00Z", "turns": []}
        self.visit_ended_at: str = "2026-07-15T10:30:00Z"

    # ---- Test 1: stub mode returns None ----

    def test_stub_mode_returns_none(self) -> None:
        """All four JournalService methods return None in stub mode."""
        service = JournalService(AgentExecutor(mode="stub"))

        result = service.summarize_exchange(
            self.npc, self.player_message, self.reply_text, self.prior_summary,
        )
        self.assertIsNone(result)

        result = asyncio.run(
            service.asummarize_exchange(
                self.npc, self.player_message, self.reply_text, self.prior_summary,
            )
        )
        self.assertIsNone(result)

        result = service.summarize_visit(self.npc, self.visit, self.visit_ended_at)
        self.assertIsNone(result)

        result = asyncio.run(
            service.asummarize_visit(self.npc, self.visit, self.visit_ended_at)
        )
        self.assertIsNone(result)

    # ---- Test 2: agent-framework sync returns parsed payload ----

    def test_sync_returns_payload(self) -> None:
        """Sync methods return the payload from invoke_json unchanged."""
        fake = _FakeJournalExecutor()
        service = JournalService(fake)
        exchange_result = service.summarize_exchange(
            self.npc, self.player_message, self.reply_text, self.prior_summary,
        )
        self.assertIsNotNone(exchange_result)
        if exchange_result is not None:
            self.assertEqual(exchange_result, fake.return_value)
            self.assertIn("summary", exchange_result)
            self.assertIn("lore_updates", exchange_result)

        visit_result = service.summarize_visit(self.npc, self.visit, self.visit_ended_at)
        self.assertIsNotNone(visit_result)
        if visit_result is not None:
            self.assertEqual(visit_result, fake.return_value)
            self.assertIn("summary", visit_result)

    def test_async_parity(self) -> None:
        """Async methods return the same payload as sync methods for the same input."""
        fake = _FakeJournalExecutor()
        service = JournalService(fake)

        sync_exchange = service.summarize_exchange(
            self.npc, self.player_message, self.reply_text, self.prior_summary,
        )
        async_exchange = asyncio.run(
            service.asummarize_exchange(
                self.npc, self.player_message, self.reply_text, self.prior_summary,
            )
        )
        self.assertEqual(sync_exchange, async_exchange)

        sync_visit = service.summarize_visit(self.npc, self.visit, self.visit_ended_at)
        async_visit = asyncio.run(
            service.asummarize_visit(self.npc, self.visit, self.visit_ended_at)
        )
        self.assertEqual(sync_visit, async_visit)

    # ---- Test 4: malformed LLM payload does not crash ----

    def test_malformed_payload_does_not_crash(self) -> None:
        """A payload without expected keys is passed through by JournalService without crashing."""
        fake = _FakeJournalExecutor(return_value={"nope": 1})
        service = JournalService(fake)
        result = service.summarize_exchange(
            self.npc, self.player_message, self.reply_text, self.prior_summary,
        )
        # JournalService passes through whatever invoke_json returns; no crash.
        self.assertEqual(result, {"nope": 1})


if __name__ == "__main__":
    unittest.main()
