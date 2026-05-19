from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.combat import create_combat_state
from app.db import ensure_player_profile
from app.game import create_run
from app.main import app


class CombatSocketTests(unittest.TestCase):
    def test_combat_action_endpoint_advances_turn(self) -> None:
        with TestClient(app) as client:
            world = app.state.world
            state = create_run(world, "Wayfarer")
            ensure_player_profile(state.player_id, state.player_name)
            state.location_id = "outer_fields"
            state.x = 1
            state.y = 5
            state.in_combat = True
            state.combat_state = create_combat_state(
                world,
                state,
                enemy_id="moss_lantern",
                encounter_message="A Moss Lantern drifts over the roadside stones and brightens with hostile intent.",
            )
            app.state.runs[state.id] = state

            response = client.post(
                f"/api/runs/{state.id}/combat",
                json={
                    "action": "defend",
                },
            )

            self.assertEqual(200, response.status_code)
            snapshot = response.json()
            self.assertTrue(snapshot["in_combat"])
            self.assertEqual("turn-based", snapshot["combat_state"]["mode"])
            self.assertEqual(2, snapshot["combat_state"]["round"])
            self.assertLess(snapshot["stats"]["hp"], state.max_hp)

    def test_attack_action_can_resolve_victory(self) -> None:
        with TestClient(app) as client:
            world = app.state.world
            state = create_run(world, "Wayfarer")
            ensure_player_profile(state.player_id, state.player_name)
            state.location_id = "outer_fields"
            state.x = 1
            state.y = 5
            state.in_combat = True
            state.combat_state = create_combat_state(
                world,
                state,
                enemy_id="moss_lantern",
                encounter_message="A Moss Lantern drifts over the roadside stones and brightens with hostile intent.",
            )
            app.state.runs[state.id] = state

            combat_state = state.combat_state
            combat_state["enemy"]["hp"] = 1

            response = client.post(
                f"/api/runs/{state.id}/combat",
                json={
                    "action": "attack",
                },
            )

            self.assertEqual(200, response.status_code)
            snapshot = response.json()
            self.assertFalse(snapshot["in_combat"])
            self.assertIsNone(snapshot["combat_state"])
            self.assertGreaterEqual(snapshot["enemies_defeated"], 1)


if __name__ == "__main__":
    unittest.main()
