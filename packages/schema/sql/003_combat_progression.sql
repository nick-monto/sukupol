CREATE TABLE IF NOT EXISTS item_definitions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  item_type TEXT NOT NULL,
  damage INTEGER NOT NULL DEFAULT 0,
  healing INTEGER NOT NULL DEFAULT 0,
  stackable INTEGER NOT NULL DEFAULT 0,
  value INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS enemy_definitions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  max_hp INTEGER NOT NULL,
  damage INTEGER NOT NULL,
  defence INTEGER NOT NULL DEFAULT 0,
  gold_min INTEGER NOT NULL DEFAULT 0,
  gold_max INTEGER NOT NULL DEFAULT 0,
  loot_json TEXT NOT NULL DEFAULT '[]',
  description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS encounter_definitions (
  id TEXT PRIMARY KEY,
  biome_id TEXT NOT NULL,
  floor_number INTEGER NOT NULL,
  enemy_ids_json TEXT NOT NULL,
  message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_outcomes (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE,
  player_id TEXT NOT NULL,
  result TEXT NOT NULL,
  depth_reached INTEGER NOT NULL,
  enemies_defeated INTEGER NOT NULL,
  gold_earned INTEGER NOT NULL,
  items_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES run_sessions(id),
  FOREIGN KEY (player_id) REFERENCES player_profiles(id)
);

CREATE TABLE IF NOT EXISTS player_progression (
  player_id TEXT PRIMARY KEY,
  total_runs INTEGER NOT NULL DEFAULT 0,
  total_victories INTEGER NOT NULL DEFAULT 0,
  deepest_depth INTEGER NOT NULL DEFAULT 0,
  last_outcome TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (player_id) REFERENCES player_profiles(id)
);
