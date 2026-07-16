from __future__ import annotations

import types
import unittest

from typing import Any

from app.agents import AgentExecutor
from app.agents.quest_agents import QuestOfferContext
from app.agents.quest_generation import QuestGenerationService
from app.agents.runtime import AgentInvocation
from app.quests.offer import _build_offer_text, _resolve_offer_content


class _FakeQuestExecutor(AgentExecutor):
    """Fake executor that returns a canned response or raises on demand."""

    def __init__(self, response: dict[str, str] | None = None, *, raise_error: bool = False) -> None:
        super().__init__(mode="agent-framework")
        self.response: dict[str, Any] = response or {
            "title": "x", "summary": "y", "objective_text": "z", "offer_text": "w",
        }
        self.raise_error = raise_error
        self.calls: list[AgentInvocation] = []

    def invoke_json(self, invocation: AgentInvocation) -> dict[str, Any]:
        self.calls.append(invocation)
        if self.raise_error:
            raise RuntimeError("boom")
        return self.response


def _make_context(**overrides: object) -> QuestOfferContext:
    """Build a minimal QuestOfferContext; override any field."""
    defaults: dict[str, object] = {
        "npc": {"id": "test", "display_name": "Test", "role": "contact", "system_prompt": ""},
        "player_name": "Wayfarer",
        "player_message": "I need work.",
        "biome_name": "Sunken Archive",
        "item_name": "Silver Ring",
        "reward_gold": 100,
        "hint": "Find it in the cave.",
    }
    defaults.update(overrides)
    return QuestOfferContext(**defaults)  # type: ignore[arg-type]


class QuestOfferFallbackIntegrationTests(unittest.TestCase):
    """Boundary tests for the generate-offer -> consumer fallback chain."""

    # ------------------------------------------------------------------
    # 1. generate_offer -> None when LLM output is malformed (AF4 reject)
    # ------------------------------------------------------------------

    def test_generate_offer_returns_none_when_llm_malformed(self) -> None:
        """Newline in title and empty summary both trigger AF4 rejection."""
        executor = _FakeQuestExecutor({
            "title": "Evil\nQuest",
            "summary": "",
            "objective_text": "Retrieve the item.",
            "offer_text": "Bring it back to me.",
        })
        service = QuestGenerationService(executor=executor)
        context = _make_context()

        result = service.generate_offer(context)

        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # 2. generate_offer -> None when LLM raises
    # ------------------------------------------------------------------

    def test_generate_offer_returns_none_when_executor_raises(self) -> None:
        """A RuntimeError from the executor is caught and surfaces as None."""
        executor = _FakeQuestExecutor(raise_error=True)
        service = QuestGenerationService(executor=executor)
        context = _make_context()

        # Must not propagate the exception
        result = service.generate_offer(context)

        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # 3. None -> consumer template-fallback
    # ------------------------------------------------------------------

    def test_consumer_fallback_uses_template_content_when_generated_is_none(self) -> None:
        """When generate_offer returns None, _resolve_offer_content and
        _build_offer_text both fall through to template-sourced content."""
        # -- _resolve_offer_content returns payload values --
        payload: dict[str, str] = {
            "title": "Template Title",
            "summary": "Template Summary",
            "objective_text": "Template Objective",
        }
        title, summary, objective_text = _resolve_offer_content(payload, None)
        self.assertEqual("Template Title", title)
        self.assertEqual("Template Summary", summary)
        self.assertEqual("Template Objective", objective_text)

        # -- _build_offer_text returns formatted template string --
        payload2: dict[str, object] = {
            "offer_templates": ("{npc_name} needs {item_name} in {biome_name}.",),
            "item_id": "silver_ring",
            "item_name": "Silver Ring",
            "reward_gold": 100,
        }
        state = types.SimpleNamespace(run_seed=42)
        npc: dict[str, str] = {"id": "test-npc", "display_name": "Marta"}
        result = _build_offer_text(payload2, None, state, npc, "Sunken Archive")
        self.assertEqual("Marta needs Silver Ring in Sunken Archive.", result)


if __name__ == "__main__":
    unittest.main()
