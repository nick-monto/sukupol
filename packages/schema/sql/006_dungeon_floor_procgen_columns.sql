-- Idempotency is enforced by the Python apply loop (PRAGMA table_info guard).
ALTER TABLE dungeon_floors ADD COLUMN procgen_features_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE dungeon_floors ADD COLUMN generation_json TEXT NOT NULL DEFAULT '{}';
