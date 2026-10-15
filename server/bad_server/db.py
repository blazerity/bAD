from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

SCHEMA_SQL = """
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
  meta_json TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]'
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

CREATE TABLE IF NOT EXISTS local_users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL COLLATE NOCASE UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'admin',
  must_change_password INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS ldap_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  enabled INTEGER NOT NULL DEFAULT 0,
  host TEXT NOT NULL DEFAULT '',
  port INTEGER NOT NULL DEFAULT 389,
  use_ssl INTEGER NOT NULL DEFAULT 0,
  start_tls INTEGER NOT NULL DEFAULT 0,
  bind_dn TEXT NOT NULL DEFAULT '',
  bind_password_enc TEXT NOT NULL DEFAULT '',
  user_search_base TEXT NOT NULL DEFAULT '',
  user_filter_template TEXT NOT NULL DEFAULT '(uid={username})',
  display_name_attr TEXT NOT NULL DEFAULT 'cn',
  default_role TEXT NOT NULL DEFAULT 'operator',
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS agent_update (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  version TEXT NOT NULL,
  msi_name TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  file_path TEXT NOT NULL,
  source_tag TEXT,
  release_url TEXT,
  synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_policies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  priority INTEGER NOT NULL DEFAULT 100,
  conditions_json TEXT NOT NULL,
  settings_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_config_overrides (
  device_id TEXT PRIMARY KEY REFERENCES devices(device_id) ON DELETE CASCADE,
  settings_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

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
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            # Ensure single LDAP settings row exists
            conn.execute(
                "INSERT OR IGNORE INTO ldap_settings(id) VALUES (1)"
            )
            # Lightweight migrations for existing DBs (CREATE IF NOT EXISTS
            # does not add new columns).
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(devices)").fetchall()
            }
            if "tags_json" not in cols:
                conn.execute(
                    "ALTER TABLE devices ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'"
                )
            conn.commit()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_site_secret(self, key: str) -> Optional[str]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM site_secrets WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None

    def set_site_secret(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO site_secrets(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def upsert_device_on_enroll(
        self,
        device_id: str,
        hostname: Optional[str],
        api_key_hash: str,
        agent_version: Optional[str],
    ) -> None:
        now = utc_now()
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE devices
                    SET hostname = COALESCE(?, hostname),
                        api_key_hash = ?,
                        last_seen_at = ?,
                        agent_version = COALESCE(?, agent_version)
                    WHERE device_id = ?
                    """,
                    (hostname, api_key_hash, now, agent_version, device_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO devices(
                      device_id, hostname, api_key_hash, enrolled_at,
                      last_seen_at, agent_version, meta_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (device_id, hostname, api_key_hash, now, now, agent_version, None),
                )

    def find_device_by_api_key(
        self, api_key: str, verify_fn
    ) -> Optional[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM devices").fetchall()
        for row in rows:
            if verify_fn(row["api_key_hash"], api_key):
                return row
        return None

    @staticmethod
    def _parse_meta(raw: Optional[str]) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            meta = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return meta if isinstance(meta, dict) else {}

    @staticmethod
    def _parse_tags(raw: Optional[str]) -> list[str]:
        from .device_health import normalize_tags

        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return normalize_tags(raw)
        return normalize_tags(parsed)

    def update_heartbeat(
        self,
        device_id: str,
        agent_version: Optional[str],
        last_inventory_at: Optional[str] = None,
        health: Optional[dict[str, Any]] = None,
    ) -> None:
        now = utc_now()
        health = {k: v for k, v in (health or {}).items() if v is not None}
        with self.connection() as conn:
            if last_inventory_at or health:
                row = conn.execute(
                    "SELECT meta_json FROM devices WHERE device_id = ?",
                    (device_id,),
                ).fetchone()
                meta = self._parse_meta(row["meta_json"] if row else None)
                if last_inventory_at:
                    meta["last_inventory_at"] = last_inventory_at
                meta.update(health)
                conn.execute(
                    """
                    UPDATE devices
                    SET last_seen_at = ?,
                        agent_version = COALESCE(?, agent_version),
                        meta_json = ?
                    WHERE device_id = ?
                    """,
                    (now, agent_version, json.dumps(meta), device_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE devices
                    SET last_seen_at = ?,
                        agent_version = COALESCE(?, agent_version)
                    WHERE device_id = ?
                    """,
                    (now, agent_version, device_id),
                )

    def store_inventory(
        self,
        device_id: str,
        schema_version: int,
        payload: dict[str, Any],
        hostname: Optional[str],
        agent_version: Optional[str],
        meta: Optional[dict[str, Any]],
        retention: int,
    ) -> int:
        from .inventory_events import detail_json, diff_inventory_snapshots

        now = utc_now()
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        meta_json = json.dumps(meta or {}, separators=(",", ":"), ensure_ascii=False)
        with self.connection() as conn:
            prev_row = conn.execute(
                """
                SELECT payload_json FROM inventory_snapshots
                WHERE device_id = ?
                ORDER BY received_at DESC, id DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()
            previous: Optional[dict[str, Any]] = None
            if prev_row:
                try:
                    parsed = json.loads(prev_row["payload_json"])
                    if isinstance(parsed, dict):
                        previous = parsed
                except json.JSONDecodeError:
                    previous = None

            # Merge inventory meta into existing meta so heartbeat/health keys survive.
            existing = conn.execute(
                "SELECT meta_json FROM devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            merged_meta = self._parse_meta(existing["meta_json"] if existing else None)
            merged_meta.update(meta or {})
            meta_json = json.dumps(
                merged_meta, separators=(",", ":"), ensure_ascii=False
            )

            conn.execute(
                """
                UPDATE devices
                SET hostname = COALESCE(?, hostname),
                    last_seen_at = ?,
                    agent_version = COALESCE(?, agent_version),
                    meta_json = ?
                WHERE device_id = ?
                """,
                (hostname, now, agent_version, meta_json, device_id),
            )
            cur = conn.execute(
                """
                INSERT INTO inventory_snapshots(
                  device_id, received_at, schema_version, payload_json
                ) VALUES (?, ?, ?, ?)
                """,
                (device_id, now, schema_version, payload_json),
            )
            snapshot_id = int(cur.lastrowid)

            for event in diff_inventory_snapshots(previous, payload):
                conn.execute(
                    """
                    INSERT INTO device_events(
                      device_id, type, summary, detail_json, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        device_id,
                        event["type"],
                        event["summary"],
                        detail_json(event.get("detail")),
                        now,
                    ),
                )

            # prune older than retention
            conn.execute(
                """
                DELETE FROM inventory_snapshots
                WHERE device_id = ?
                  AND id NOT IN (
                    SELECT id FROM inventory_snapshots
                    WHERE device_id = ?
                    ORDER BY received_at DESC, id DESC
                    LIMIT ?
                  )
                """,
                (device_id, device_id, retention),
            )
            return snapshot_id

    def list_devices(self, tag: Optional[str] = None) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT device_id, hostname, enrolled_at, last_seen_at,
                       agent_version, meta_json, tags_json
                FROM devices
                ORDER BY COALESCE(last_seen_at, enrolled_at) DESC
                """
            ).fetchall()
        wanted = (tag or "").strip().casefold()
        result: list[dict[str, Any]] = []
        for row in rows:
            tags = self._parse_tags(row["tags_json"])
            if wanted and wanted not in {t.casefold() for t in tags}:
                continue
            result.append(
                {
                    "device_id": row["device_id"],
                    "hostname": row["hostname"],
                    "enrolled_at": row["enrolled_at"],
                    "last_seen_at": row["last_seen_at"],
                    "agent_version": row["agent_version"],
                    "meta": self._parse_meta(row["meta_json"]),
                    "tags": tags,
                }
            )
        return result

    def list_all_tags(self) -> list[str]:
        seen: dict[str, str] = {}
        for device in self.list_devices():
            for tag in device.get("tags") or []:
                key = tag.casefold()
                if key not in seen:
                    seen[key] = tag
        return sorted(seen.values(), key=str.casefold)

    def set_device_tags(self, device_id: str, tags: list[str]) -> list[str]:
        from .device_health import normalize_tags

        clean = normalize_tags(tags)
        payload = json.dumps(clean, separators=(",", ":"), ensure_ascii=False)
        with self.connection() as conn:
            cur = conn.execute(
                "UPDATE devices SET tags_json = ? WHERE device_id = ?",
                (payload, device_id),
            )
            if cur.rowcount == 0:
                raise KeyError(device_id)
        return clean

    def list_device_events(
        self,
        *,
        device_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self.connection() as conn:
            if device_id:
                rows = conn.execute(
                    """
                    SELECT e.id, e.device_id, e.type, e.summary, e.detail_json,
                           e.created_at, d.hostname
                    FROM device_events e
                    LEFT JOIN devices d ON d.device_id = e.device_id
                    WHERE e.device_id = ?
                    ORDER BY e.created_at DESC, e.id DESC
                    LIMIT ?
                    """,
                    (device_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT e.id, e.device_id, e.type, e.summary, e.detail_json,
                           e.created_at, d.hostname
                    FROM device_events e
                    LEFT JOIN devices d ON d.device_id = e.device_id
                    ORDER BY e.created_at DESC, e.id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            detail: Any = None
            if row["detail_json"]:
                try:
                    detail = json.loads(row["detail_json"])
                except json.JSONDecodeError:
                    detail = {"_raw": row["detail_json"]}
            result.append(
                {
                    "id": row["id"],
                    "device_id": row["device_id"],
                    "hostname": row["hostname"],
                    "type": row["type"],
                    "summary": row["summary"],
                    "detail": detail,
                    "created_at": row["created_at"],
                }
            )
        return result

    def get_device_detail(self, device_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            device = conn.execute(
                "SELECT * FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
            if not device:
                return None
            snap = conn.execute(
                """
                SELECT id, received_at, schema_version, payload_json
                FROM inventory_snapshots
                WHERE device_id = ?
                ORDER BY received_at DESC, id DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()
        meta = self._parse_meta(device["meta_json"])
        inventory = None
        if snap:
            try:
                payload = json.loads(snap["payload_json"])
            except json.JSONDecodeError:
                payload = {"_raw": snap["payload_json"]}
            inventory = {
                "id": snap["id"],
                "received_at": snap["received_at"],
                "schema_version": snap["schema_version"],
                "payload": payload,
            }
        return {
            "device_id": device["device_id"],
            "hostname": device["hostname"],
            "enrolled_at": device["enrolled_at"],
            "last_seen_at": device["last_seen_at"],
            "agent_version": device["agent_version"],
            "meta": meta,
            "tags": self._parse_tags(device["tags_json"] if "tags_json" in device.keys() else None),
            "latest_inventory": inventory,
        }

    # --- local users ---

    def count_local_users(self) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM local_users").fetchone()
            return int(row["c"] if row else 0)

    def create_local_user(
        self,
        username: str,
        password_hash: str,
        role: str = "admin",
        must_change_password: bool = False,
    ) -> int:
        now = utc_now()
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO local_users(
                  username, password_hash, role, must_change_password, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    role,
                    1 if must_change_password else 0,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def get_local_user(self, username: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM local_users WHERE username = ? COLLATE NOCASE",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def update_local_user_password(
        self, username: str, password_hash: str, clear_must_change: bool = True
    ) -> None:
        with self.connection() as conn:
            if clear_must_change:
                conn.execute(
                    """
                    UPDATE local_users
                    SET password_hash = ?, must_change_password = 0
                    WHERE username = ? COLLATE NOCASE
                    """,
                    (password_hash, username),
                )
            else:
                conn.execute(
                    """
                    UPDATE local_users
                    SET password_hash = ?
                    WHERE username = ? COLLATE NOCASE
                    """,
                    (password_hash, username),
                )

    def touch_local_user_login(self, username: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE local_users SET last_login_at = ?
                WHERE username = ? COLLATE NOCASE
                """,
                (utc_now(), username),
            )

    # --- LDAP settings ---

    def get_ldap_settings(self) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM ldap_settings WHERE id = 1").fetchone()
        if not row:
            return {
                "id": 1,
                "enabled": 0,
                "host": "",
                "port": 389,
                "use_ssl": 0,
                "start_tls": 0,
                "bind_dn": "",
                "bind_password_enc": "",
                "user_search_base": "",
                "user_filter_template": "(uid={username})",
                "display_name_attr": "cn",
                "default_role": "operator",
                "updated_at": None,
            }
        return dict(row)

    def update_ldap_settings(
        self,
        *,
        enabled: bool,
        host: str,
        port: int,
        use_ssl: bool,
        start_tls: bool,
        bind_dn: str,
        user_search_base: str,
        user_filter_template: str,
        display_name_attr: str,
        default_role: str,
        bind_password_enc: Optional[str] = None,
    ) -> None:
        now = utc_now()
        with self.connection() as conn:
            if bind_password_enc is not None:
                conn.execute(
                    """
                    UPDATE ldap_settings SET
                      enabled = ?, host = ?, port = ?, use_ssl = ?, start_tls = ?,
                      bind_dn = ?, bind_password_enc = ?,
                      user_search_base = ?, user_filter_template = ?,
                      display_name_attr = ?, default_role = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        1 if enabled else 0,
                        host,
                        port,
                        1 if use_ssl else 0,
                        1 if start_tls else 0,
                        bind_dn,
                        bind_password_enc,
                        user_search_base,
                        user_filter_template,
                        display_name_attr,
                        default_role,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE ldap_settings SET
                      enabled = ?, host = ?, port = ?, use_ssl = ?, start_tls = ?,
                      bind_dn = ?,
                      user_search_base = ?, user_filter_template = ?,
                      display_name_attr = ?, default_role = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        1 if enabled else 0,
                        host,
                        port,
                        1 if use_ssl else 0,
                        1 if start_tls else 0,
                        bind_dn,
                        user_search_base,
                        user_filter_template,
                        display_name_attr,
                        default_role,
                        now,
                    ),
                )

    # --- agent update mirror ---

    def get_agent_update(self) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT version, msi_name, sha256, file_path, source_tag, "
                "release_url, synced_at FROM agent_update WHERE id = 1"
            ).fetchone()
        if not row:
            return None
        return {
            "version": row["version"],
            "msi_name": row["msi_name"],
            "sha256": row["sha256"],
            "file_path": row["file_path"],
            "source_tag": row["source_tag"],
            "release_url": row["release_url"],
            "synced_at": row["synced_at"],
        }

    def set_agent_update(
        self,
        *,
        version: str,
        msi_name: str,
        sha256: str,
        file_path: str,
        source_tag: Optional[str] = None,
        release_url: Optional[str] = None,
    ) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_update(
                  id, version, msi_name, sha256, file_path,
                  source_tag, release_url, synced_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  version = excluded.version,
                  msi_name = excluded.msi_name,
                  sha256 = excluded.sha256,
                  file_path = excluded.file_path,
                  source_tag = excluded.source_tag,
                  release_url = excluded.release_url,
                  synced_at = excluded.synced_at
                """,
                (version, msi_name, sha256, file_path, source_tag, release_url, now),
            )
        return {
            "version": version,
            "msi_name": msi_name,
            "sha256": sha256,
            "file_path": file_path,
            "source_tag": source_tag,
            "release_url": release_url,
            "synced_at": now,
        }

    # --- agent remote config (policies + per-device overrides) ---

    @staticmethod
    def _row_to_policy(row: sqlite3.Row) -> dict[str, Any]:
        try:
            conditions = json.loads(row["conditions_json"] or "[]")
        except json.JSONDecodeError:
            conditions = []
        try:
            settings = json.loads(row["settings_json"] or "{}")
        except json.JSONDecodeError:
            settings = {}
        return {
            "id": row["id"],
            "name": row["name"],
            "enabled": bool(row["enabled"]),
            "priority": int(row["priority"]),
            "conditions": conditions if isinstance(conditions, list) else [],
            "settings": settings if isinstance(settings, dict) else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_agent_policies(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent_policies
                ORDER BY priority ASC, id ASC
                """
            ).fetchall()
        return [self._row_to_policy(r) for r in rows]

    def get_agent_policy(self, policy_id: int) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM agent_policies WHERE id = ?", (policy_id,)
            ).fetchone()
        return self._row_to_policy(row) if row else None

    def create_agent_policy(
        self,
        *,
        name: str,
        enabled: bool,
        priority: int,
        conditions: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        now = utc_now()
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO agent_policies(
                  name, enabled, priority, conditions_json, settings_json,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    1 if enabled else 0,
                    priority,
                    json.dumps(conditions, separators=(",", ":"), ensure_ascii=False),
                    json.dumps(settings, separators=(",", ":"), ensure_ascii=False),
                    now,
                    now,
                ),
            )
            policy_id = int(cur.lastrowid)
        policy = self.get_agent_policy(policy_id)
        assert policy is not None
        return policy

    def update_agent_policy(
        self,
        policy_id: int,
        *,
        name: str,
        enabled: bool,
        priority: int,
        conditions: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        now = utc_now()
        with self.connection() as conn:
            cur = conn.execute(
                """
                UPDATE agent_policies SET
                  name = ?, enabled = ?, priority = ?,
                  conditions_json = ?, settings_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    1 if enabled else 0,
                    priority,
                    json.dumps(conditions, separators=(",", ":"), ensure_ascii=False),
                    json.dumps(settings, separators=(",", ":"), ensure_ascii=False),
                    now,
                    policy_id,
                ),
            )
            if cur.rowcount == 0:
                return None
        return self.get_agent_policy(policy_id)

    def delete_agent_policy(self, policy_id: int) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM agent_policies WHERE id = ?", (policy_id,)
            )
            return cur.rowcount > 0

    def get_device_config_override(self, device_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT device_id, settings_json, updated_at
                FROM device_config_overrides WHERE device_id = ?
                """,
                (device_id,),
            ).fetchone()
        if not row:
            return None
        try:
            settings = json.loads(row["settings_json"] or "{}")
        except json.JSONDecodeError:
            settings = {}
        return {
            "device_id": row["device_id"],
            "settings": settings if isinstance(settings, dict) else {},
            "updated_at": row["updated_at"],
        }

    def set_device_config_override(
        self, device_id: str, settings: dict[str, Any]
    ) -> dict[str, Any]:
        now = utc_now()
        payload = json.dumps(settings, separators=(",", ":"), ensure_ascii=False)
        with self.connection() as conn:
            exists = conn.execute(
                "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
            if not exists:
                raise KeyError(device_id)
            conn.execute(
                """
                INSERT INTO device_config_overrides(device_id, settings_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                  settings_json = excluded.settings_json,
                  updated_at = excluded.updated_at
                """,
                (device_id, payload, now),
            )
        override = self.get_device_config_override(device_id)
        assert override is not None
        return override

    def delete_device_config_override(self, device_id: str) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM device_config_overrides WHERE device_id = ?",
                (device_id,),
            )
            return cur.rowcount > 0

    def latest_inventory_payload(self, device_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            snap = conn.execute(
                """
                SELECT payload_json FROM inventory_snapshots
                WHERE device_id = ?
                ORDER BY received_at DESC, id DESC
                LIMIT 1
                """,
                (device_id,),
            ).fetchone()
        if not snap:
            return None
        try:
            payload = json.loads(snap["payload_json"])
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def compute_device_effective_config(self, device_id: str) -> Optional[dict[str, Any]]:
        from .agent_config import compute_effective_config

        with self.connection() as conn:
            device = conn.execute(
                "SELECT * FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
        if not device:
            return None
        override_row = self.get_device_config_override(device_id)
        override = override_row["settings"] if override_row else None
        tags = self._parse_tags(
            device["tags_json"] if "tags_json" in device.keys() else None
        )
        result = compute_effective_config(
            hostname=device["hostname"],
            meta=self._parse_meta(device["meta_json"]),
            inventory_payload=self.latest_inventory_payload(device_id),
            tags=tags,
            policies=self.list_agent_policies(),
            override=override,
        )
        result["device_id"] = device_id
        result["override"] = override_row
        return result

