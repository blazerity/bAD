-- Device inventory change events + tags (JSON array on devices)
ALTER TABLE devices ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]';

CREATE TABLE IF NOT EXISTS device_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  summary TEXT NOT NULL,
  detail_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_device_events_created
  ON device_events(created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_device_events_device_created
  ON device_events(device_id, created_at DESC, id DESC);
