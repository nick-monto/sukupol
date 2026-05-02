PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS player_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_sessions (
  id TEXT PRIMARY KEY,
  player_id TEXT NOT NULL,
  player_name TEXT NOT NULL,
  location_id TEXT NOT NULL,
  player_x INTEGER NOT NULL,
  player_y INTEGER NOT NULL,
  facing TEXT NOT NULL,
  hp INTEGER NOT NULL,
  max_hp INTEGER NOT NULL,
  gold INTEGER NOT NULL,
  status TEXT NOT NULL,
  snapshot_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (player_id) REFERENCES player_profiles(id)
);

CREATE TABLE IF NOT EXISTS npc_definitions (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL,
  system_prompt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS npc_instances (
  id TEXT PRIMARY KEY,
  definition_id TEXT NOT NULL,
  location_id TEXT NOT NULL,
  x INTEGER NOT NULL,
  y INTEGER NOT NULL,
  relationship INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (definition_id) REFERENCES npc_definitions(id)
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
  player_id TEXT NOT NULL,
  npc_instance_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (player_id, npc_instance_id),
  FOREIGN KEY (player_id) REFERENCES player_profiles(id),
  FOREIGN KEY (npc_instance_id) REFERENCES npc_instances(id)
);
