CREATE TABLE IF NOT EXISTS npc_player_memories (
  player_id TEXT NOT NULL,
  npc_instance_id TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  last_player_message TEXT NOT NULL DEFAULT '',
  last_npc_reply TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,
  PRIMARY KEY (player_id, npc_instance_id),
  FOREIGN KEY (player_id) REFERENCES player_profiles(id),
  FOREIGN KEY (npc_instance_id) REFERENCES npc_instances(id)
);

INSERT OR IGNORE INTO npc_player_memories (
  player_id,
  npc_instance_id,
  summary,
  last_player_message,
  last_npc_reply,
  updated_at
)
SELECT player_id, npc_instance_id, summary, '', '', updated_at
FROM conversation_summaries;

UPDATE npc_player_memories
SET summary = (
  SELECT conversation_summaries.summary
  FROM conversation_summaries
  WHERE conversation_summaries.player_id = npc_player_memories.player_id
    AND conversation_summaries.npc_instance_id = npc_player_memories.npc_instance_id
),
updated_at = (
  SELECT conversation_summaries.updated_at
  FROM conversation_summaries
  WHERE conversation_summaries.player_id = npc_player_memories.player_id
    AND conversation_summaries.npc_instance_id = npc_player_memories.npc_instance_id
)
WHERE EXISTS (
  SELECT 1
  FROM conversation_summaries
  WHERE conversation_summaries.player_id = npc_player_memories.player_id
    AND conversation_summaries.npc_instance_id = npc_player_memories.npc_instance_id
);

CREATE TABLE IF NOT EXISTS npc_shared_knowledge (
  id TEXT PRIMARY KEY,
  npc_instance_id TEXT NOT NULL,
  category TEXT NOT NULL,
  content TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (npc_instance_id, category, content),
  FOREIGN KEY (npc_instance_id) REFERENCES npc_instances(id)
);

CREATE INDEX IF NOT EXISTS idx_npc_shared_knowledge_npc_updated
ON npc_shared_knowledge (npc_instance_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS player_quests (
  id TEXT PRIMARY KEY,
  player_id TEXT NOT NULL,
  template_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  offered_by_npc_id TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  objective_text TEXT NOT NULL,
  objective_kind TEXT NOT NULL,
  target_location_id TEXT,
  target_biome_id TEXT,
  target_floor_number INTEGER,
  target_count INTEGER NOT NULL DEFAULT 0,
  progress_value INTEGER NOT NULL DEFAULT 0,
  progress_target INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,
  completion_summary TEXT,
  offered_at TEXT NOT NULL,
  accepted_at TEXT,
  completed_at TEXT,
  declined_at TEXT,
  updated_at TEXT NOT NULL,
  UNIQUE (player_id, template_id),
  FOREIGN KEY (player_id) REFERENCES player_profiles(id),
  FOREIGN KEY (run_id) REFERENCES run_sessions(id),
  FOREIGN KEY (offered_by_npc_id) REFERENCES npc_instances(id)
);

CREATE INDEX IF NOT EXISTS idx_player_quests_player_status_updated
ON player_quests (player_id, status, updated_at DESC);