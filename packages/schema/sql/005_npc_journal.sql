CREATE TABLE IF NOT EXISTS npc_journal_entries (
  id TEXT PRIMARY KEY,
  player_id TEXT NOT NULL,
  npc_instance_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  turn_count INTEGER NOT NULL DEFAULT 0,
  visit_started_at TEXT NOT NULL,
  visit_ended_at TEXT NOT NULL,
  summary TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (player_id) REFERENCES player_profiles(id),
  FOREIGN KEY (npc_instance_id) REFERENCES npc_instances(id),
  FOREIGN KEY (run_id) REFERENCES run_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_npc_journal_entries_player_created
  ON npc_journal_entries (player_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_npc_journal_entries_player_npc
  ON npc_journal_entries (player_id, npc_instance_id, visit_ended_at DESC);