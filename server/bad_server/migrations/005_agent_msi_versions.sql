-- 0.10.0: каталог нескольких версий MSI (зеркало GitHub + ручная заливка).
CREATE TABLE IF NOT EXISTS agent_msi_versions (
  version TEXT PRIMARY KEY,
  msi_name TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  file_path TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'github',
  source_tag TEXT,
  release_url TEXT,
  mirrored_at TEXT NOT NULL
);
