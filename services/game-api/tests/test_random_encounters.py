from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.combat import maybe_start_encounter
from app.content import load_world_content
from app.db import connect, load_dungeon_floor
from app.game import create_run, encounter_context_for_location


class RandomEncounterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()

    def test_loaded_dungeon_floor_restores_encounter_metadata(self) -> None:
        loaded_floor = self._persist_and_load_floor()

        self.assertTrue(loaded_floor["encounter_enabled"])
        self.assertEqual("ancient_halls", loaded_floor["encounter_biome_id"])
        self.assertEqual(1, loaded_floor["encounter_floor"])
        self.assertEqual("dungeon", loaded_floor["location_type"])

    def test_loaded_dungeon_floor_can_start_encounter(self) -> None:
        loaded_floor = self._persist_and_load_floor()
        loaded_floor["encounter_rate"] = 100
        self.world.locations[loaded_floor["id"]] = loaded_floor

        state = create_run(self.world, "Wayfarer")
        state.location_id = loaded_floor["id"]
        state.x = loaded_floor["entry_x"]
        state.y = loaded_floor["entry_y"]
        state.steps_taken = 1

        maybe_start_encounter(self.world, state, moved=True)

        self.assertTrue(state.in_combat)
        self.assertIsNotNone(state.combat_state)
        self.assertEqual("engaged", state.combat_state["status"])
        self.assertEqual("turn-based", state.combat_state["mode"])
        self.assertIn("available_actions", state.combat_state)

    def test_non_town_location_types_default_to_encounters(self) -> None:
        context = encounter_context_for_location(
            self.world,
            {
                "id": "test-cave",
                "location_type": "cave",
                "biome_id": "whispering_caverns",
                "floor_number": 0,
            },
        )

        self.assertTrue(context["enabled"])

    def test_town_and_city_location_types_default_safe(self) -> None:
        town_context = encounter_context_for_location(
            self.world,
            {
                "id": "test-town",
                "location_type": "town",
                "biome_id": "ashen_fields",
                "floor_number": 0,
            },
        )
        city_context = encounter_context_for_location(
            self.world,
            {
                "id": "test-city",
                "location_type": "city",
                "biome_id": "ashen_fields",
                "floor_number": 0,
            },
        )

        self.assertFalse(town_context["enabled"])
        self.assertFalse(city_context["enabled"])

    def _persist_and_load_floor(self) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "encounters.db"
            with connect(db_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE dungeon_floors (
                      id TEXT PRIMARY KEY,
                      dungeon_instance_id TEXT NOT NULL,
                      biome_id TEXT NOT NULL,
                      floor_number INTEGER NOT NULL,
                      floor_seed INTEGER NOT NULL,
                      location_id TEXT NOT NULL UNIQUE,
                      name TEXT NOT NULL,
                      description TEXT NOT NULL,
                      ascii_map_json TEXT NOT NULL,
                      exits_json TEXT NOT NULL,
                      entry_x INTEGER NOT NULL,
                      entry_y INTEGER NOT NULL,
                                            procgen_features_json TEXT NOT NULL,
                                            generation_json TEXT NOT NULL,
                      validation_json TEXT NOT NULL,
                      created_at TEXT NOT NULL,
                      updated_at TEXT NOT NULL
                    );
                    """
                )
                connection.execute(
                    """
                    INSERT INTO dungeon_floors (
                      id,
                      dungeon_instance_id,
                      biome_id,
                      floor_number,
                      floor_seed,
                      location_id,
                      name,
                      description,
                      ascii_map_json,
                      exits_json,
                      entry_x,
                      entry_y,
                                            procgen_features_json,
                                            generation_json,
                      validation_json,
                      created_at,
                      updated_at
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                      "floor-row",
                      "instance-row",
                      "ancient_halls",
                      1,
                      12345,
                      "dungeon:test-floor:1",
                      "Ancient Halls Test Floor",
                      "A recovered dungeon floor for encounter tests.",
                      json.dumps([
                          "#####",
                          "#...#",
                          "#.∪.#",
                          "#...#",
                          "#####",
                      ]),
                      json.dumps([
                          {
                              "x": 2,
                              "y": 2,
                              "target_location_id": "dungeon_approach",
                              "target_x": 4,
                              "target_y": 5,
                              "target_facing": "S",
                              "message": "You climb back toward the approach.",
                          }
                      ]),
                      2,
                      2,
                                            json.dumps([], sort_keys=True),
                                            json.dumps({"profile": "halls"}, sort_keys=True),
                      json.dumps({"is_valid": True}, sort_keys=True),
                      "2026-05-15T00:00:00+00:00",
                      "2026-05-15T00:00:00+00:00",
                    ),
                )
                connection.commit()

            return load_dungeon_floor("dungeon:test-floor:1", db_path=db_path)



if __name__ == "__main__":
    unittest.main()