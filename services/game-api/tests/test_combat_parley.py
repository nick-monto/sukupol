from __future__ import annotations

import unittest

from app.combat import create_combat_state, resolve_turn
from app.content import load_world_content
from app.game import create_run


class _FakeParleyService:
    def __init__(self) -> None:
        self.open_calls = 0
        self.reply_calls = 0

    def generate_open_line(self, world, state, combat_state, enemy_def, negotiation) -> str:
        self.open_calls += 1
        return f"{enemy_def['name']} suspends the strike and waits for your terms."

    def generate_reply(self, world, state, combat_state, enemy_def, negotiation, player_message, analysis) -> str:
        self.reply_calls += 1
        return f"{enemy_def['name']} tilts toward your offer and keeps listening."


class CombatParleyTests(unittest.TestCase):
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
        self.parley = _FakeParleyService()

    def test_parley_open_uses_service_generated_line(self) -> None:
        resolve_turn(self.world, self.state, "parley_open", parley_service=self.parley)  # type: ignore[arg-type]

        negotiation = self.state.combat_state["negotiation"]  # type: ignore[union-attr]
        self.assertEqual(1, self.parley.open_calls)
        self.assertTrue(negotiation["active"])
        self.assertIn("waits for your terms", self.state.message)
        self.assertEqual("enemy", negotiation["transcript"][-1]["speaker"])

    def test_parley_message_uses_service_generated_reply(self) -> None:
        resolve_turn(self.world, self.state, "parley_open", parley_service=self.parley)  # type: ignore[arg-type]
        resolve_turn(
            self.world,
            self.state,
            "parley_message",
            message="Please listen and accept this offer of tribute.",
            parley_service=self.parley,  # type: ignore[arg-type]
        )

        negotiation = self.state.combat_state["negotiation"]  # type: ignore[union-attr]
        self.assertEqual(1, self.parley.reply_calls)
        self.assertEqual("Moss Lantern tilts toward your offer and keeps listening.", self.state.message)
        self.assertEqual("enemy", negotiation["transcript"][-1]["speaker"])
        self.assertIn("keeps listening", negotiation["transcript"][-1]["text"])

    def test_combat_state_is_turn_based_without_legacy_board_state(self) -> None:
        cs = self.state.combat_state
        assert cs is not None
        available_actions = {entry["id"] for entry in cs["available_actions"]}

        self.assertEqual("turn-based", cs["mode"])
        self.assertIn("enemy", cs)
        self.assertIn("available_actions", cs)
        self.assertIn("attack", available_actions)
        self.assertIn("defend", available_actions)
        self.assertIn("flee", available_actions)


if __name__ == "__main__":
    unittest.main()