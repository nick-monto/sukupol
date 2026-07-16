from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.content import load_world_content
from app.db.connection import connect, initialize_database
from app.db.dungeons import create_dungeon_instance, load_dungeon_floor, persist_dungeon_floor
from app.procgen.generator import generate_floor


class ProcgenGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = load_world_content()

    def test_generate_floor_is_deterministic(self) -> None:
        biome = self.world.dungeon_biomes["ancient_halls"]

        first = generate_floor(run_seed=10101, biome=biome, floor_number=2)
        second = generate_floor(run_seed=10101, biome=biome, floor_number=2)

        self.assertEqual(first.ascii_map, second.ascii_map)
        self.assertEqual(first.features, second.features)
        self.assertEqual(first.generation, second.generation)

    def test_profiles_generate_distinct_feature_signatures(self) -> None:
        halls = generate_floor(run_seed=20202, biome=self.world.dungeon_biomes["ancient_halls"], floor_number=2)
        archive = generate_floor(run_seed=20202, biome=self.world.dungeon_biomes["sunken_archive"], floor_number=2)

        hall_variants = {feature.get("variant") for feature in halls.features}
        archive_variants = {feature.get("variant") for feature in archive.features}

        self.assertEqual("halls", halls.generation["profile"])
        self.assertEqual("flooded_archive", archive.generation["profile"])
        self.assertIn("rubble", hall_variants)
        self.assertIn("wet", archive_variants)

    def test_depth_progression_increases_generation_budget(self) -> None:
        biome = self.world.dungeon_biomes["sunken_archive"]
        shallow = generate_floor(run_seed=30303, biome=biome, floor_number=1)
        deeper = generate_floor(run_seed=30303, biome=biome, floor_number=4)

        self.assertGreaterEqual(deeper.generation["room_count"], shallow.generation["room_count"])
        self.assertGreaterEqual(deeper.generation["hazard_count"], shallow.generation["hazard_count"])
        self.assertGreaterEqual(deeper.generation["loop_count"], shallow.generation["loop_count"])

    def test_features_respect_reserved_entry_exit_tiles(self) -> None:
        biome = self.world.dungeon_biomes["ancient_halls"]
        layout = generate_floor(run_seed=40404, biome=biome, floor_number=3)

        reserved_tiles = {(layout.entry_x, layout.entry_y)}
        exit_x = next(exit_node["x"] for exit_node in layout.exits)
        exit_y = next(exit_node["y"] for exit_node in layout.exits)
        reserved_tiles.add((exit_x, exit_y))
        for origin_x, origin_y in list(reserved_tiles):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                reserved_tiles.add((origin_x + dx, origin_y + dy))

        self.assertTrue(layout.validation["is_valid"])
        for feature in layout.features:
            self.assertNotIn((feature["x"], feature["y"]), reserved_tiles)

    def test_persisted_floor_round_trips_procgen_metadata(self) -> None:
        biome = self.world.dungeon_biomes["sunken_archive"]
        layout = generate_floor(run_seed=50505, biome=biome, floor_number=2)

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "procgen.db"
            initialize_database(self.world, db_path=db_path)
            with connect(db_path) as connection:
                connection.execute(
                    """
                    INSERT INTO player_profiles (id, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    ("player-1", "Wayfarer", "2026-05-15T00:00:00+00:00", "2026-05-15T00:00:00+00:00"),
                )
                connection.execute(
                    """
                    INSERT INTO run_sessions (
                      id,
                      player_id,
                      player_name,
                      location_id,
                      player_x,
                      player_y,
                      facing,
                      hp,
                      max_hp,
                      gold,
                      status,
                      snapshot_json,
                      created_at,
                      updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "run-1",
                        "player-1",
                        "Wayfarer",
                        self.world.player_spawn["location_id"],
                        self.world.player_spawn["x"],
                        self.world.player_spawn["y"],
                        "N",
                        12,
                        12,
                        0,
                        "exploring",
                        "{}",
                        "2026-05-15T00:00:00+00:00",
                        "2026-05-15T00:00:00+00:00",
                    ),
                )
                connection.commit()
            instance = create_dungeon_instance(
                run_id="run-1",
                biome_id=biome["id"],
                run_seed=50505,
                procgen_version=biome["procgen_version"],
                db_path=db_path,
            )
            persist_dungeon_floor(
                dungeon_instance_id=instance.id,
                biome_id=biome["id"],
                floor_number=layout.floor_number,
                floor_seed=layout.floor_seed,
                location_id=layout.location_id,
                name=layout.name,
                description=layout.description,
                ascii_map=layout.ascii_map,
                exits=layout.exits,
                entry_x=layout.entry_x,
                entry_y=layout.entry_y,
                procgen_features=layout.features,
                generation=layout.generation,
                validation=layout.validation,
                db_path=db_path,
            )

            loaded = load_dungeon_floor(layout.location_id, db_path=db_path)

        self.assertIsNotNone(loaded)
        self.assertEqual(layout.features, loaded["procgen_features"])
        self.assertEqual(layout.generation, loaded["procgen_generation"])


if __name__ == "__main__":
    unittest.main()