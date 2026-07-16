from __future__ import annotations

import json
import unittest

from app.agents import AgentExecutor
from app.agents.dialogue_agents import (
    NpcDialogueTurnContext,
    sanitize_prompt_input,
    build_npc_dialogue_agent,
)
from app.agents.journal_agents import ExchangeSummaryContext, build_exchange_summary_agent
from app.agents.dialogue_tools import NpcDialogueToolContext, build_npc_dialogue_tools
from app.content import load_world_content
from app.dialogue import NpcDialogueService, coerce_dialogue_reply_text, parse_model_dialogue_result
from app.game import create_run


class _FakeAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        super().__init__(mode="agent-framework")
        self.calls: list[dict[str, object]] = []

    def invoke_json(self, invocation) -> dict[str, str]:
        self.calls.append(
            {
                "agent_name": invocation.agent_name,
                "instructions": invocation.instructions,
                "user_prompt": invocation.user_prompt,
                "tools": invocation.tools,
            }
        )
        return {"reply": "Marta: Stay alert."}


class DialogueAgentSeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()

    def setUp(self) -> None:
        self.state = create_run(self.world, "Wayfarer")
        self.npc = self.world.npcs["marta-innkeeper"]
        self.player_memory = {"summary": "Marta warned me about the lower halls."}
        self.shared_knowledge = [{"category": "rumor", "content": "The first descent rearranges itself."}]

    def test_tool_builder_returns_expected_payloads(self) -> None:
        tools = build_npc_dialogue_tools(
            NpcDialogueToolContext(
                world=self.world,
                state=self.state,
                npc=self.npc,
                player_memory=self.player_memory,
                shared_knowledge=self.shared_knowledge,
            )
        )

        self.assertEqual(3, len(tools))

        run_context = json.loads(tools[0]())
        self.assertEqual(self.state.location_id, run_context["location"]["id"])
        self.assertEqual(self.state.player_name, run_context["player"]["name"])
        self.assertTrue(any(entry["id"] == "ilya-lamplighter" for entry in run_context["nearby_npcs"]))

        inventory_context = json.loads(tools[1]())
        self.assertEqual(self.state.equipped_weapon, inventory_context["equipped_weapon"])
        self.assertTrue(inventory_context["inventory"])
        first_entry = inventory_context["inventory"][0]
        expected_name = self.world.items[first_entry["item_id"]]["name"]
        self.assertEqual(expected_name, first_entry["name"])

        conversation_context = json.loads(tools[2]())
        self.assertEqual(self.player_memory["summary"], conversation_context["prior_memory"])
        self.assertEqual("rumor", conversation_context["shared_knowledge"][0]["category"])

    def test_agent_builder_keeps_prompt_shape(self) -> None:
        invocation = build_npc_dialogue_agent(
            NpcDialogueTurnContext(
                npc=self.npc,
                state=self.state,
                player_message="What waits below?",
                player_memory=self.player_memory,
                shared_knowledge=self.shared_knowledge,
            )
        )

        self.assertEqual("npc-marta-innkeeper", invocation.agent_name)
        self.assertIn("default to 1-3 short sentences", invocation.instructions)
        self.assertIn("Do not monologue", invocation.instructions)
        self.assertIn("Return strict JSON with key: reply.", invocation.instructions)
        self.assertIn("Player message: What waits below?", invocation.user_prompt)
        self.assertIn("Keep the reply compact and natural.", invocation.user_prompt)
        self.assertIn("Shared knowledge:\n- rumor: The first descent rearranges itself.", invocation.user_prompt)

        summary_invocation = build_exchange_summary_agent(
            ExchangeSummaryContext(
                npc=self.npc,
                player_message="What waits below?",
                reply_text="Marta: Do not trust silence.",
                prior_summary=self.player_memory["summary"],
            )
        )
        self.assertEqual("npc-summary-marta-innkeeper", summary_invocation.agent_name)
        self.assertIn("lore_updates", summary_invocation.instructions)

    def test_service_uses_extracted_agent_and_tool_builders(self) -> None:
        fake_executor = _FakeAgentExecutor()
        service = NpcDialogueService(executor=fake_executor)

        result = service._agent_framework_response(
            world=self.world,
            npc=self.npc,
            state=self.state,
            player_message="What waits below?",
            player_memory=self.player_memory,
            shared_knowledge=self.shared_knowledge,
        )

        self.assertEqual("Marta: Stay alert.", result.reply)
        self.assertEqual(1, len(fake_executor.calls))
        call = fake_executor.calls[0]
        assert isinstance(call, dict)
        self.assertEqual("npc-marta-innkeeper", call["agent_name"])
        self.assertIn("Player message: What waits below?", str(call["user_prompt"]))
        self.assertEqual(3, len(call["tools"]))
        self.assertEqual(self.player_memory["summary"], json.loads(call["tools"][2]())["prior_memory"])

    def test_parse_model_dialogue_result_accepts_alternate_text_keys(self) -> None:
        self.assertEqual(
            "Marta: Keep moving.",
            parse_model_dialogue_result({"text": "Marta: Keep moving."}).reply,
        )
        self.assertEqual(
            "Marta: Mind the lower halls.",
            parse_model_dialogue_result({"message": {"content": "Marta: Mind the lower halls."}}).reply,
        )

    def test_coerce_dialogue_reply_text_trims_monologues(self) -> None:
        reply = (
            "Marta: The first halls listen harder than they look. Keep your torch high and your pace measured. "
            "Most fools die because they mistake silence for safety. If you feel proud down there, turn back before the place notices."
        )

        self.assertEqual(
            "Marta: The first halls listen harder than they look. Keep your torch high and your pace measured.",
            coerce_dialogue_reply_text(reply),
        )


class PromptSanitizationTests(unittest.TestCase):
    def test_sanitize_strips_newlines(self) -> None:
        raw = "hello\nworld\r\ninjection"
        result = sanitize_prompt_input(raw)
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)
        # Newlines converted to spaces and collapsed
        self.assertEqual(result, "hello world injection")

    def test_sanitize_strips_null_bytes(self) -> None:
        raw = "normal\x00text"
        result = sanitize_prompt_input(raw)
        self.assertNotIn("\x00", result)

    def test_sanitize_preserves_safe_content(self) -> None:
        raw = "Hello there, what waits below?"
        self.assertEqual(sanitize_prompt_input(raw), raw)

    def test_sanitize_collapse_multiple_newlines(self) -> None:
        raw = "a\n\n\nb"
        result = sanitize_prompt_input(raw)
        # Whitespace runs collapsed to single space
        self.assertEqual(result, "a b")


if __name__ == "__main__":
    unittest.main()