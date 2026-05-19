CREATE TABLE IF NOT EXISTS dungeon_instances (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE,
  biome_id TEXT NOT NULL,
  run_seed INTEGER NOT NULL,
  procgen_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES run_sessions(id)
);

CREATE TABLE IF NOT EXISTS dungeon_floors (
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
  procgen_features_json TEXT NOT NULL DEFAULT '[]',
  generation_json TEXT NOT NULL DEFAULT '{}',
  validation_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (dungeon_instance_id) REFERENCES dungeon_instances(id)
);
