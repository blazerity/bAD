-- Initial schema (also applied by Database._init_schema at runtime)
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS devices (
  device_id TEXT PRIMARY KEY,
  hostname TEXT,
  api_key_hash TEXT NOT NULL,
  enrolled_at TEXT NOT NULL,
  last_seen_at TEXT,
  agent_version TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS inventory_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL REFERENCES devices(device_id),
  received_at TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_device_received
  ON inventory_snapshots(device_id, received_at DESC);

CREATE TABLE IF NOT EXISTS site_secrets (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
