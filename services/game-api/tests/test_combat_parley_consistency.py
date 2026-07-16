from __future__ import annotations

import copy
import unittest

from app.agents.combat_parley import CombatParleyService
from app.agents.runtime import AgentExecutor, AgentInvocation
from app.combat import create_combat_state
from app.combat.negotiation import append_negotiation_transcript
from app.content import load_world_content
from app.game import create_run


class _RaisingExecutor(AgentExecutor):
    """Fake executor whose invoke_text raises RuntimeError."""

    def __init__(self) -> None:
        super().__init__(mode="agent-framework")

    def invoke_text(self, invocation: AgentInvocation) -> str:
        raise RuntimeError("connect failed")


class _EmptyReturningExecutor(AgentExecutor):
    """Fake executor whose invoke_text returns an empty string."""

    def __init__(self) -> None:
        super().__init__(mode="agent-framework")

    def invoke_text(self, invocation: AgentInvocation) -> str:
        return ""


class CombatParleyConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()

    def setUp(self) -> None:
        self.state = create_run(self.world, "Wayfarer")
        self.state.location_id = "outer_fields"
        self.state.x = 1
        self.state.y = 5
        self.state.in_combat = True
        self.state.combat_state = create_combat_state(
            self.world,
            self.state,
            enemy_id="moss_lantern",
            encounter_message="A Moss Lantern drifts over the roadside stones and brightens with hostile intent.",
        )

    # ----------------------------------------------------------------
    # Test 1: open-line raise -> fallback, combat state unchanged
    # ----------------------------------------------------------------
    def test_open_line_raise_returns_fallback_and_combat_unchanged(self) -> None:
        service = CombatParleyService(executor=_RaisingExecutor())
        cs = self.state.combat_state
        assert cs is not None
        negotiation = cs["negotiation"]
        enemy_def = cs["enemy"]

        combat_state_before = copy.deepcopy(cs)
        negotiation_before = copy.deepcopy(negotiation)

        result = service.generate_open_line(
            world=self.world,
            state=self.state,
            combat_state=cs,
            enemy_def=enemy_def,
            negotiation=negotiation,
        )

        # Must return the deterministic fallback and NOT raise
        expected_fallback = (
            f"You open parley. {enemy_def['name']} answers by "
            f"{negotiation['communication_mode']}, waiting for your terms."
        )
        self.assertEqual(expected_fallback, result)
        # Combat state and negotiation must not be mutated by a failed LLM call
        self.assertEqual(combat_state_before, cs)
        self.assertEqual(negotiation_before, negotiation)

    # ----------------------------------------------------------------
    # Test 2: reply raise -> fallback, transcript increments by exactly 1
    # ----------------------------------------------------------------
    def test_reply_raise_returns_fallback_and_transcript_increments_by_one(self) -> None:
        service = CombatParleyService(executor=_RaisingExecutor())
        cs = self.state.combat_state
        assert cs is not None
        negotiation = cs["negotiation"]
        enemy_def = cs["enemy"]

        # Build a realistic analysis dict and set up a starting transcript entry
        analysis: dict[str, object] = {
            "reply": "Moss Lantern flickers but doesn't strike.",
            "inferred_intent": "cautious",
            "leverage_delta": 0,
            "anger_delta": 0,
            "grants_pause": False,
            "provoked": False,
        }

        transcript_before = copy.deepcopy(negotiation.get("transcript", []))

        result = service.generate_reply(
            world=self.world,
            state=self.state,
            combat_state=cs,
            enemy_def=enemy_def,
            negotiation=negotiation,
            player_message="I offer a tribute of gold.",
            analysis=analysis,
        )

        # Must return the deterministic fallback and NOT raise
        expected_fallback = str(analysis.get("reply", "")).strip()
        self.assertEqual(expected_fallback, result)
        # Service must not have mutated the transcript itself
        self.assertEqual(transcript_before, negotiation.get("transcript", []))

        # Simulate what the caller (combat/parley.py:_execute_parley_message) does:
        # append the returned fallback line to the transcript as the enemy's reply.
        append_negotiation_transcript(negotiation, "enemy", result)
        self.assertEqual(
            len(transcript_before) + 1,
            len(negotiation["transcript"]),
            "Transcript must grow by exactly 1 entry (the fallback line).",
        )
        # The new entry must be the fallback, not empty or partial
        last_entry = negotiation["transcript"][-1]
        self.assertEqual("enemy", last_entry["speaker"])
        self.assertEqual(expected_fallback, last_entry["text"])

    # ----------------------------------------------------------------
    # Test 3: malformed (empty) LLM text -> stored as fallback, not raw empty
    # ----------------------------------------------------------------
    def test_empty_llm_text_replaced_with_fallback(self) -> None:
        service = CombatParleyService(executor=_EmptyReturningExecutor())
        cs = self.state.combat_state
        assert cs is not None
        negotiation = cs["negotiation"]
        enemy_def = cs["enemy"]

        analysis: dict[str, object] = {
            "reply": "Moss Lantern holds its ground and says nothing.",
            "inferred_intent": "wary",
            "leverage_delta": 0,
            "anger_delta": 0,
            "grants_pause": False,
            "provoked": False,
        }

        transcript_before = copy.deepcopy(negotiation.get("transcript", []))

        result = service.generate_reply(
            world=self.world,
            state=self.state,
            combat_state=cs,
            enemy_def=enemy_def,
            negotiation=negotiation,
            player_message="I mean you no harm.",
            analysis=analysis,
        )

        # Must return the fallback (not the empty string from the fake executor)
        expected_fallback = str(analysis.get("reply", "")).strip()
        self.assertEqual(expected_fallback, result)

        # Simulate the caller appending the result to the transcript
        append_negotiation_transcript(negotiation, "enemy", result)
        self.assertEqual(len(transcript_before) + 1, len(negotiation["transcript"]))

        # The transcript entry must hold the fallback, NOT an empty string
        last_entry = negotiation["transcript"][-1]
        self.assertEqual("enemy", last_entry["speaker"])
        self.assertEqual(expected_fallback, last_entry["text"])
        self.assertNotEqual("", last_entry["text"])


if __name__ == "__main__":
    unittest.main()
