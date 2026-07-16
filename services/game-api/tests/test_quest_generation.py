from __future__ import annotations

import unittest

from app.agents import AgentExecutor, QuestGenerationService
from app.content import load_world_content
from app.db.connection import initialize_database
from app.db.runs import ensure_player_profile, save_run_snapshot
from app.game import create_run, state_to_dict
from app.quests import accept_offered_quest, maybe_complete_quest_turn_in, maybe_offer_conversation_quest


class _FakeQuestExecutor(AgentExecutor):
    def __init__(self) -> None:
        super().__init__(mode="local-llm")
        self.calls: list[str] = []

    def invoke_json(self, invocation):
        self.calls.append(invocation.agent_name)
        if invocation.agent_name.startswith("quest-offer-"):
            return {
                "title": "Recover Marta's Satchel",
                "summary": "Marta wants her satchel recovered from the flooded archive.",
                "objective_text": "Recover Marta's satchel in Sunken Archive and bring it back.",
                "offer_text": "If you go below, bring my satchel back from the flooded archive.",
            }
        return {"response_text": "Then we have terms. Bring it back to me."}


class QuestGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()
        initialize_database(cls.world)

    def setUp(self) -> None:
        self.state = create_run(self.world, "Wayfarer")
        ensure_player_profile(self.state.player_id, self.state.player_name)
        save_run_snapshot(state_to_dict(self.state))
        self.quest_service = QuestGenerationService(executor=_FakeQuestExecutor())
        self.npc = self.world.npcs["marta-innkeeper"]

    def test_offer_generation_service_overrides_offer_text_fields(self) -> None:
        offered = maybe_offer_conversation_quest(
            self.world,
            self.state,
            self.npc,
            "I need work. Is there anything missing in the archive?",
            quest_generation_service=self.quest_service,
        )

        assert offered is not None
        self.assertIsNotNone(offered)
        self.assertEqual("Recover Marta's Satchel", offered["title"])
        self.assertEqual("Marta wants her satchel recovered from the flooded archive.", offered["summary"])
        self.assertEqual("Recover Marta's satchel in Sunken Archive and bring it back.", offered["objective_text"])
        self.assertEqual("If you go below, bring my satchel back from the flooded archive.", offered["offer_text"])

    def test_accept_and_completion_use_generated_responses(self) -> None:
        offered = maybe_offer_conversation_quest(
            self.world,
            self.state,
            self.npc,
            "Do you need help finding something?",
            quest_generation_service=self.quest_service,
        )
        assert offered is not None
        self.assertIsNotNone(offered)

        accepted = accept_offered_quest(
            self.world,
            self.state,
            offered["id"],
            quest_generation_service=self.quest_service,
        )
        self.assertEqual("Then we have terms. Bring it back to me.", accepted["response_text"])

        target_item_id = accepted["target_item_id"]
        self.state.inventory = list(self.state.inventory or []) + [{"item_id": target_item_id, "quantity": 1, "equipped": False}]
        completed = maybe_complete_quest_turn_in(
            self.world,
            self.state,
            self.npc["id"],
            quest_generation_service=self.quest_service,
        )
        assert completed is not None
        self.assertIsNotNone(completed)
        self.assertEqual("Then we have terms. Bring it back to me.", completed["response_text"])


if __name__ == "__main__":
    unittest.main()