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
  api_key_lookup TEXT,
  enrolled_at TEXT NOT NULL,
  last_seen_at TEXT,
  agent_version TEXT,
  meta_json TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  revoked INTEGER NOT NULL DEFAULT 0,
  archived INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_devices_api_key_lookup
  ON devices(api_key_lookup);

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
  allowed_group TEXT NOT NULL DEFAULT '',
  tls_insecure INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS retention_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  events_days INTEGER NOT NULL DEFAULT 90,
  inventory_days INTEGER NOT NULL DEFAULT 180,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS smtp_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  enabled INTEGER NOT NULL DEFAULT 0,
  host TEXT NOT NULL DEFAULT '',
  port INTEGER NOT NULL DEFAULT 587,
  use_ssl INTEGER NOT NULL DEFAULT 0,
  use_starttls INTEGER NOT NULL DEFAULT 1,
  username TEXT NOT NULL DEFAULT '',
  password_enc TEXT NOT NULL DEFAULT '',
  from_addr TEXT NOT NULL DEFAULT '',
  to_addrs TEXT NOT NULL DEFAULT '',
  notify_json TEXT NOT NULL DEFAULT '',
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

-- Каталог зеркалированных MSI (несколько версий; agent_update = указатель на latest).
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
            # Гарантировать наличие singleton-строк settings
            conn.execute("INSERT OR IGNORE INTO ldap_settings(id) VALUES (1)")
            conn.execute("INSERT OR IGNORE INTO retention_settings(id) VALUES (1)")
            conn.execute("INSERT OR IGNORE INTO smtp_settings(id) VALUES (1)")
            # Лёгкие миграции для существующих БД (CREATE IF NOT EXISTS
            # не добавляет новые колонки).
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(devices)").fetchall()
            }
            if "tags_json" not in cols:
                conn.execute(
                    "ALTER TABLE devices ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'"
                )
            if "revoked" not in cols:
                conn.execute(
                    "ALTER TABLE devices ADD COLUMN revoked INTEGER NOT NULL DEFAULT 0"
                )
            if "archived" not in cols:
                conn.execute(
                    "ALTER TABLE devices ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
                )
            if "api_key_lookup" not in cols:
                conn.execute("ALTER TABLE devices ADD COLUMN api_key_lookup TEXT")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_devices_api_key_lookup "
                "ON devices(api_key_lookup)"
            )
            ldap_cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(ldap_settings)").fetchall()
            }
            if "allowed_group" not in ldap_cols:
                conn.execute(
                    "ALTER TABLE ldap_settings ADD COLUMN allowed_group "
                    "TEXT NOT NULL DEFAULT ''"
                )
            if "tls_insecure" not in ldap_cols:
                conn.execute(
                    "ALTER TABLE ldap_settings ADD COLUMN tls_insecure "
                    "INTEGER NOT NULL DEFAULT 0"
                )
            # Multi-version MSI mirror (0.10): migrate singleton agent_update → catalog.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_msi_versions (
                  version TEXT PRIMARY KEY,
                  msi_name TEXT NOT NULL,
                  sha256 TEXT NOT NULL,
                  file_path TEXT NOT NULL,
                  source TEXT NOT NULL DEFAULT 'github',
                  source_tag TEXT,
                  release_url TEXT,
                  mirrored_at TEXT NOT NULL
                )
                """
            )
            legacy = conn.execute(
                "SELECT version, msi_name, sha256, file_path, source_tag, "
                "release_url, synced_at FROM agent_update WHERE id = 1"
            ).fetchone()
            if legacy:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO agent_msi_versions(
                      version, msi_name, sha256, file_path, source,
                      source_tag, release_url, mirrored_at
                    ) VALUES (?, ?, ?, ?, 'github', ?, ?, ?)
                    """,
                    (
                        legacy["version"],
                        legacy["msi_name"],
                        legacy["sha256"],
                        legacy["file_path"],
                        legacy["source_tag"],
                        legacy["release_url"],
                        legacy["synced_at"],
                    ),
                )
            smtp_cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(smtp_settings)").fetchall()
            }
            if "notify_json" not in smtp_cols:
                conn.execute(
                    "ALTER TABLE smtp_settings ADD COLUMN notify_json "
                    "TEXT NOT NULL DEFAULT ''"
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

    def delete_site_secret(self, key: str) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM site_secrets WHERE key = ?", (key,))

    def get_device_auth_row(self, device_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT device_id, api_key_hash, revoked "
                "FROM devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_device_on_enroll(
        self,
        device_id: str,
        hostname: Optional[str],
        api_key_hash: str,
        agent_version: Optional[str],
        *,
        api_key_lookup: Optional[str] = None,
        allow_existing: bool = False,
    ) -> bool:
        """Создать устройство или (при allow_existing) обновить ключ.

        True — создана новая строка. Без allow_existing повторный enroll
        существующего device_id не делается (SEC-001).
        """
        now = utc_now()
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT device_id, revoked FROM devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
            if existing:
                if not allow_existing:
                    raise ValueError("device_already_enrolled")
                if existing["revoked"]:
                    raise ValueError("device_revoked")
                conn.execute(
                    """
                    UPDATE devices
                    SET hostname = COALESCE(?, hostname),
                        api_key_hash = ?,
                        api_key_lookup = ?,
                        last_seen_at = ?,
                        agent_version = COALESCE(?, agent_version),
                        revoked = 0
                    WHERE device_id = ?
                    """,
                    (
                        hostname,
                        api_key_hash,
                        api_key_lookup,
                        now,
                        agent_version,
                        device_id,
                    ),
                )
                return False
            conn.execute(
                """
                INSERT INTO devices(
                  device_id, hostname, api_key_hash, api_key_lookup, enrolled_at,
                  last_seen_at, agent_version, meta_json, revoked, archived
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (
                    device_id,
                    hostname,
                    api_key_hash,
                    api_key_lookup,
                    now,
                    now,
                    agent_version,
                    None,
                ),
            )
            return True

    def find_device_by_api_key(
        self,
        api_key: str,
        verify_fn,
        *,
        lookup_hash: Optional[str] = None,
    ) -> Optional[sqlite3.Row]:
        """O(1) lookup by HMAC index, then one Argon2 verify (SEC-006).

        Legacy rows without api_key_lookup are scanned once and backfilled.
        """
        with self.connection() as conn:
            row = None
            if lookup_hash:
                row = conn.execute(
                    "SELECT * FROM devices WHERE api_key_lookup = ?",
                    (lookup_hash,),
                ).fetchone()
            if row is not None:
                if verify_fn(row["api_key_hash"], api_key):
                    return row
                return None

            # Migration: only devices missing lookup index (bounded set).
            legacy = conn.execute(
                """
                SELECT * FROM devices
                WHERE api_key_lookup IS NULL OR api_key_lookup = ''
                """
            ).fetchall()
            for candidate in legacy:
                if verify_fn(candidate["api_key_hash"], api_key):
                    if lookup_hash:
                        conn.execute(
                            "UPDATE devices SET api_key_lookup = ? WHERE device_id = ?",
                            (lookup_hash, candidate["device_id"]),
                        )
                    return candidate
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
        config_local: Any = None,
        *,
        config_local_provided: bool = False,
    ) -> None:
        """Update last_seen (+ optional health / config_local in meta).

        ``config_local_provided``: False → leave meta.config_local; True with empty
        keys → clear; True with keys → atomic replace of the config_local block.
        """
        now = utc_now()
        health = {k: v for k, v in (health or {}).items() if v is not None}
        touch_meta = bool(last_inventory_at or health or config_local_provided)
        with self.connection() as conn:
            if touch_meta:
                row = conn.execute(
                    "SELECT meta_json FROM devices WHERE device_id = ?",
                    (device_id,),
                ).fetchone()
                meta = self._parse_meta(row["meta_json"] if row else None)
                if last_inventory_at:
                    meta["last_inventory_at"] = last_inventory_at
                meta.update(health)
                if config_local_provided:
                    from .agent_config import sanitize_config_local

                    cleaned = sanitize_config_local(config_local)
                    # keys:[] clears agent_local knobs; keep block if display-only
                    # server_url is still present (agent ServerUrlLocal, no safe knobs).
                    if not cleaned.get("keys") and not cleaned.get("server_url"):
                        meta.pop("config_local", None)
                    else:
                        block = dict(cleaned)
                        block["reported_at"] = now
                        meta["config_local"] = block
                conn.execute(
                    """
                    UPDATE devices
                    SET last_seen_at = ?,
                        agent_version = COALESCE(?, agent_version),
                        meta_json = ?
                    WHERE device_id = ?
                    """,
                    (now, agent_version, json.dumps(meta, ensure_ascii=False), device_id),
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
    ) -> dict[str, Any]:
        from .inventory_events import diff_inventory_snapshots

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

            # Слить inventory meta с существующим meta, чтобы ключи heartbeat/health сохранились.
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

            events = diff_inventory_snapshots(previous, payload)
            for event in events:
                detail = event.get("detail")
                detail_payload = json.dumps(
                    detail if detail is not None else {},
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
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
                        detail_payload,
                        now,
                    ),
                )

            # удалить старше лимита retention по числу на устройство (env BAD_SNAPSHOT_RETENTION)
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
            return {"snapshot_id": snapshot_id, "events": events}

    def list_devices(
        self,
        tag: Optional[str] = None,
        *,
        archived: Optional[bool] = False,
        q: Optional[str] = None,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT device_id, hostname, enrolled_at, last_seen_at,
                       agent_version, meta_json, tags_json, revoked, archived
                FROM devices
                ORDER BY COALESCE(last_seen_at, enrolled_at) DESC
                """
            ).fetchall()
        wanted = (tag or "").strip().casefold()
        query = (q or "").strip().casefold()
        result: list[dict[str, Any]] = []
        for row in rows:
            is_archived = bool(row["archived"])
            if archived is False and is_archived:
                continue
            if archived is True and not is_archived:
                continue
            tags = self._parse_tags(row["tags_json"])
            if wanted and wanted not in {t.casefold() for t in tags}:
                continue
            device_id = row["device_id"]
            hostname = row["hostname"] or ""
            if query:
                hay = " ".join(
                    [
                        device_id.casefold(),
                        hostname.casefold(),
                    ]
                )
                # serial из последнего inventory дорогой; сначала id/hostname
                if query not in hay:
                    # опционально serial через meta-кэш, если есть
                    meta = self._parse_meta(row["meta_json"])
                    serial = str(meta.get("serial_number") or "").casefold()
                    if query not in serial:
                        continue
            result.append(
                {
                    "device_id": device_id,
                    "hostname": row["hostname"],
                    "enrolled_at": row["enrolled_at"],
                    "last_seen_at": row["last_seen_at"],
                    "agent_version": row["agent_version"],
                    "meta": self._parse_meta(row["meta_json"]),
                    "tags": tags,
                    "revoked": bool(row["revoked"]),
                    "archived": is_archived,
                }
            )
        if offset or limit is not None:
            start = max(0, int(offset))
            if limit is None:
                return result[start:]
            end = start + max(1, int(limit))
            return result[start:end]
        return result

    def count_devices(
        self,
        tag: Optional[str] = None,
        *,
        archived: Optional[bool] = False,
        q: Optional[str] = None,
    ) -> int:
        return len(self.list_devices(tag=tag, archived=archived, q=q))

    def list_all_tags(self) -> list[str]:
        seen: dict[str, str] = {}
        for device in self.list_devices():
            for tag in device.get("tags") or []:
                key = tag.casefold()
                if key not in seen:
                    seen[key] = tag
        return sorted(seen.values(), key=str.casefold)

    def set_device_tags(self, device_id: str, tags: Any) -> list[str]:
        """Нормализовать и сохранить tags. Единая точка записи для очистки тегов."""
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
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        sql = """
            SELECT e.id, e.device_id, e.type, e.summary, e.detail_json,
                   e.created_at, d.hostname
            FROM device_events e
            LEFT JOIN devices d ON d.device_id = e.device_id
        """
        params: list[Any]
        if device_id:
            sql += " WHERE e.device_id = ?"
            params = [device_id, limit, offset]
        else:
            params = [limit, offset]
        sql += " ORDER BY e.created_at DESC, e.id DESC LIMIT ? OFFSET ?"
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
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

    def count_device_events(self, *, device_id: Optional[str] = None) -> int:
        with self.connection() as conn:
            if device_id:
                row = conn.execute(
                    "SELECT COUNT(*) AS c FROM device_events WHERE device_id = ?",
                    (device_id,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS c FROM device_events").fetchone()
        return int(row["c"] if row else 0)

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
        serial_number = None
        model = None
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
            if isinstance(payload, dict):
                hw = payload.get("hardware")
                if isinstance(hw, dict):
                    serial_number = hw.get("serial_number")
                    model = hw.get("model")
        return {
            "device_id": device["device_id"],
            "hostname": device["hostname"],
            "enrolled_at": device["enrolled_at"],
            "last_seen_at": device["last_seen_at"],
            "agent_version": device["agent_version"],
            "meta": meta,
            "tags": self._parse_tags(device["tags_json"]),
            "revoked": bool(device["revoked"]),
            "archived": bool(device["archived"]),
            "serial_number": serial_number,
            "model": model,
            "latest_inventory": inventory,
        }

    # --- локальные пользователи ---

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
                "allowed_group": "",
                "tls_insecure": 0,
                "updated_at": None,
            }
        data = dict(row)
        data.setdefault("allowed_group", "")
        data.setdefault("tls_insecure", 0)
        return data

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
        allowed_group: str = "",
        tls_insecure: bool = False,
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
                      display_name_attr = ?, default_role = ?,
                      allowed_group = ?, tls_insecure = ?, updated_at = ?
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
                        allowed_group,
                        1 if tls_insecure else 0,
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
                      display_name_attr = ?, default_role = ?,
                      allowed_group = ?, tls_insecure = ?, updated_at = ?
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
                        allowed_group,
                        1 if tls_insecure else 0,
                        now,
                    ),
                )

    # --- зеркало agent update (каталог версий + указатель latest) ---

    @staticmethod
    def _msi_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "version": row["version"],
            "msi_name": row["msi_name"],
            "sha256": row["sha256"],
            "file_path": row["file_path"],
            "source": row["source"] if "source" in row.keys() else "github",
            "source_tag": row["source_tag"],
            "release_url": row["release_url"],
            "mirrored_at": row["mirrored_at"]
            if "mirrored_at" in row.keys()
            else row["synced_at"]
            if "synced_at" in row.keys()
            else None,
            "synced_at": row["synced_at"]
            if "synced_at" in row.keys()
            else row["mirrored_at"]
            if "mirrored_at" in row.keys()
            else None,
        }

    def get_agent_update(self) -> Optional[dict[str, Any]]:
        """Указатель на latest (или лучшая версия из каталога)."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT version, msi_name, sha256, file_path, source_tag, "
                "release_url, synced_at FROM agent_update WHERE id = 1"
            ).fetchone()
        if row:
            data = self._msi_row(row)
            data["source"] = "latest-pointer"
            return data
        versions = self.list_agent_msi_versions()
        return versions[0] if versions else None

    def get_agent_msi_version(self, version: str) -> Optional[dict[str, Any]]:
        ver = (version or "").strip()
        if not ver:
            return None
        with self.connection() as conn:
            row = conn.execute(
                "SELECT version, msi_name, sha256, file_path, source, "
                "source_tag, release_url, mirrored_at "
                "FROM agent_msi_versions WHERE version = ?",
                (ver,),
            ).fetchone()
        return self._msi_row(row) if row else None

    def list_agent_msi_versions(self) -> list[dict[str, Any]]:
        """Все зеркалированные MSI, newest semver first (несортируемые — в конце)."""
        from .agent_update import parse_semver

        with self.connection() as conn:
            rows = conn.execute(
                "SELECT version, msi_name, sha256, file_path, source, "
                "source_tag, release_url, mirrored_at "
                "FROM agent_msi_versions"
            ).fetchall()
        items = [self._msi_row(r) for r in rows]

        def sort_key(item: dict[str, Any]) -> tuple:
            parsed = parse_semver(item.get("version") or "")
            if parsed is None:
                return (0, (0, 0, 0), item.get("version") or "")
            return (1, parsed, item.get("version") or "")

        items.sort(key=sort_key, reverse=True)
        return items

    def upsert_agent_msi_version(
        self,
        *,
        version: str,
        msi_name: str,
        sha256: str,
        file_path: str,
        source: str = "github",
        source_tag: Optional[str] = None,
        release_url: Optional[str] = None,
        set_as_latest: bool = True,
        force_latest: bool = False,
    ) -> dict[str, Any]:
        """Добавить/обновить версию в каталоге; опционально обновить указатель latest.

        При обычной заливке старой версии указатель latest не понижается.
        ``force_latest=True`` — явный set-latest / rollback указателя.
        """
        from .agent_update import is_newer

        now = utc_now()
        src = (source or "github").strip() or "github"
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_msi_versions(
                  version, msi_name, sha256, file_path, source,
                  source_tag, release_url, mirrored_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(version) DO UPDATE SET
                  msi_name = excluded.msi_name,
                  sha256 = excluded.sha256,
                  file_path = excluded.file_path,
                  source = excluded.source,
                  source_tag = excluded.source_tag,
                  release_url = excluded.release_url,
                  mirrored_at = excluded.mirrored_at
                """,
                (
                    version,
                    msi_name,
                    sha256,
                    file_path,
                    src,
                    source_tag,
                    release_url,
                    now,
                ),
            )
            if set_as_latest:
                current = conn.execute(
                    "SELECT version FROM agent_update WHERE id = 1"
                ).fetchone()
                should_point = True
                if (
                    not force_latest
                    and current
                    and current["version"]
                    and not is_newer(version, current["version"])
                    and version != current["version"]
                ):
                    # Не понижать указатель latest при обычной заливке старой версии.
                    should_point = False
                if should_point:
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
                        (
                            version,
                            msi_name,
                            sha256,
                            file_path,
                            source_tag,
                            release_url,
                            now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO site_secrets(key, value) VALUES (?, ?)
                        ON CONFLICT(key) DO UPDATE SET value = excluded.value
                        """,
                        ("agent_msi_latest_version", version),
                    )
        record = {
            "version": version,
            "msi_name": msi_name,
            "sha256": sha256,
            "file_path": file_path,
            "source": src,
            "source_tag": source_tag,
            "release_url": release_url,
            "mirrored_at": now,
            "synced_at": now,
        }
        return record

    def set_agent_update(
        self,
        *,
        version: str,
        msi_name: str,
        sha256: str,
        file_path: str,
        source_tag: Optional[str] = None,
        release_url: Optional[str] = None,
        source: str = "github",
    ) -> dict[str, Any]:
        """Совместимость: upsert в каталог + указатель latest."""
        return self.upsert_agent_msi_version(
            version=version,
            msi_name=msi_name,
            sha256=sha256,
            file_path=file_path,
            source=source,
            source_tag=source_tag,
            release_url=release_url,
            set_as_latest=True,
        )

    def delete_agent_msi_version(self, version: str) -> bool:
        """Удалить запись каталога (файл на диске — отдельно). Обновить latest при необходимости."""
        ver = (version or "").strip()
        if not ver:
            return False
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM agent_msi_versions WHERE version = ?", (ver,)
            )
            if cur.rowcount <= 0:
                return False
            pointer = conn.execute(
                "SELECT version FROM agent_update WHERE id = 1"
            ).fetchone()
            if pointer and pointer["version"] == ver:
                conn.execute("DELETE FROM agent_update WHERE id = 1")
        # Переставить указатель на новую latest.
        remaining = self.list_agent_msi_versions()
        if remaining:
            top = remaining[0]
            self.upsert_agent_msi_version(
                version=top["version"],
                msi_name=top["msi_name"],
                sha256=top["sha256"],
                file_path=top["file_path"],
                source=top.get("source") or "github",
                source_tag=top.get("source_tag"),
                release_url=top.get("release_url"),
                set_as_latest=True,
            )
        return True

    # --- remote config агента (policies + per-device overrides) ---

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
        from .agent_config import compute_effective_config, provenance_from_effective

        with self.connection() as conn:
            device = conn.execute(
                "SELECT * FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
        if not device:
            return None
        override_row = self.get_device_config_override(device_id)
        override = override_row["settings"] if override_row else None
        tags = self._parse_tags(device["tags_json"])
        meta = self._parse_meta(device["meta_json"])
        result = compute_effective_config(
            hostname=device["hostname"],
            meta=meta,
            inventory_payload=self.latest_inventory_payload(device_id),
            tags=tags,
            policies=self.list_agent_policies(),
            override=override,
        )
        result["device_id"] = device_id
        result["override"] = override_row
        result.update(provenance_from_effective(result, meta=meta))
        return result

    # --- жизненный цикл устройства (revoke / archive / delete) ---

    def _set_device_flag(self, device_id: str, column: str, value: bool) -> bool:
        if column not in {"revoked", "archived"}:
            raise ValueError(f"unsupported device flag: {column}")
        with self.connection() as conn:
            cur = conn.execute(
                f"UPDATE devices SET {column} = ? WHERE device_id = ?",
                (1 if value else 0, device_id),
            )
            return cur.rowcount > 0

    def set_device_revoked(self, device_id: str, revoked: bool) -> bool:
        return self._set_device_flag(device_id, "revoked", revoked)

    def rotate_device_api_key(
        self,
        device_id: str,
        api_key_hash: str,
        *,
        api_key_lookup: Optional[str] = None,
    ) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                """
                UPDATE devices
                SET api_key_hash = ?, api_key_lookup = ?, revoked = 0
                WHERE device_id = ?
                """,
                (api_key_hash, api_key_lookup, device_id),
            )
            return cur.rowcount > 0

    def set_device_archived(self, device_id: str, archived: bool) -> bool:
        return self._set_device_flag(device_id, "archived", archived)

    def delete_device(self, device_id: str) -> bool:
        """Жёстко удалить device и связанные строки (snapshots + cascades)."""
        with self.connection() as conn:
            exists = conn.execute(
                "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
            if not exists:
                return False
            conn.execute(
                "DELETE FROM inventory_snapshots WHERE device_id = ?", (device_id,)
            )
            conn.execute(
                "DELETE FROM device_events WHERE device_id = ?", (device_id,)
            )
            conn.execute(
                "DELETE FROM device_config_overrides WHERE device_id = ?", (device_id,)
            )
            conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
            return True

    def find_duplicate_devices(self, device_id: str) -> dict[str, list[dict[str, Any]]]:
        """Другие устройства с тем же hostname (ci) или serial_number из последнего inventory."""
        detail = self.get_device_detail(device_id)
        if not detail:
            return {"hostname": [], "serial_number": []}
        hostname = (detail.get("hostname") or "").strip()
        serial = (detail.get("serial_number") or "").strip()
        by_host: list[dict[str, Any]] = []
        by_serial: list[dict[str, Any]] = []
        # При поиске дубликатов учитывать и archived
        for other in self.list_devices(archived=None):
            if other["device_id"] == device_id:
                continue
            other_hn = (other.get("hostname") or "").strip()
            if hostname and other_hn and hostname.casefold() == other_hn.casefold():
                by_host.append(
                    {
                        "device_id": other["device_id"],
                        "hostname": other["hostname"],
                        "archived": other.get("archived"),
                    }
                )
            other_serial = (other.get("meta") or {}).get("serial_number")
            if not other_serial:
                od = self.get_device_detail(other["device_id"])
                other_serial = (od or {}).get("serial_number")
            if (
                serial
                and other_serial
                and str(serial).strip().casefold()
                == str(other_serial).strip().casefold()
            ):
                by_serial.append(
                    {
                        "device_id": other["device_id"],
                        "hostname": other["hostname"],
                        "serial_number": other_serial,
                        "archived": other.get("archived"),
                    }
                )
        return {"hostname": by_host, "serial_number": by_serial}

    def count_enrolled_since(self, since_iso: Optional[str] = None) -> int:
        """Active (non-archived) devices enrolled strictly after ``since_iso``.

        If ``since_iso`` is empty — count all active devices (never rotated).
        Strict ``>`` so successful rotate immediately clears ``rotation_due``.
        """
        with self.connection() as conn:
            if since_iso:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM devices
                    WHERE COALESCE(archived, 0) = 0
                      AND enrolled_at IS NOT NULL
                      AND enrolled_at > ?
                    """,
                    (since_iso,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM devices
                    WHERE COALESCE(archived, 0) = 0
                    """
                ).fetchone()
        return int(row["c"] if row else 0)

    def overview_stats(self, *, stale_after_seconds: int) -> dict[str, Any]:
        from .device_health import device_silence_status

        active = self.list_devices(archived=False)
        archived = self.list_devices(archived=True)
        online = 0
        stale = 0
        versions: dict[str, int] = {}
        for d in active:
            silence = device_silence_status(
                d.get("last_seen_at"), stale_after_seconds=stale_after_seconds
            )
            if silence["status"] == "ok":
                online += 1
            else:
                stale += 1
            ver = (d.get("agent_version") or "—").strip() or "—"
            versions[ver] = versions.get(ver, 0) + 1
        version_breakdown = [
            {"version": v, "count": c}
            for v, c in sorted(versions.items(), key=lambda x: (-x[1], x[0]))
        ]
        from .smtp_mail import HARDWARE_ALERT_TYPES

        recent_hw = [
            e
            for e in self.list_device_events(limit=40)
            if e.get("type") in HARDWARE_ALERT_TYPES
        ][:10]
        return {
            "total_active": len(active),
            "online": online,
            "stale": stale,
            "archived": len(archived),
            "total_all": len(active) + len(archived),
            "agent_versions": version_breakdown,
            "recent_hardware_events": recent_hw,
        }

    def devices_for_csv(
        self,
        *,
        tag: Optional[str] = None,
        archived: Optional[bool] = False,
        q: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for d in self.list_devices(tag=tag, archived=archived, q=q):
            detail = self.get_device_detail(d["device_id"]) or d
            inv = (detail.get("latest_inventory") or {}).get("payload") or {}
            hw = inv.get("hardware") if isinstance(inv, dict) else {}
            if not isinstance(hw, dict):
                hw = {}
            host = inv.get("host") if isinstance(inv, dict) else {}
            if not isinstance(host, dict):
                host = {}
            cpu = hw.get("cpu") if isinstance(hw.get("cpu"), dict) else {}
            rows.append(
                {
                    "device_id": d["device_id"],
                    "hostname": d.get("hostname") or "",
                    "tags": ",".join(d.get("tags") or []),
                    "agent_version": d.get("agent_version") or "",
                    "last_seen_at": d.get("last_seen_at") or "",
                    "enrolled_at": d.get("enrolled_at") or "",
                    "archived": "1" if d.get("archived") else "0",
                    "revoked": "1" if d.get("revoked") else "0",
                    "serial_number": hw.get("serial_number") or "",
                    "model": hw.get("model") or "",
                    "manufacturer": hw.get("manufacturer") or "",
                    "cpu": cpu.get("name") or "",
                    "ram_bytes": hw.get("ram_bytes")
                    if hw.get("ram_bytes") is not None
                    else "",
                    "domain": host.get("domain") or "",
                    "os": (host.get("os") or {}).get("caption")
                    if isinstance(host.get("os"), dict)
                    else "",
                }
            )
        return rows

    # --- retention ---

    def get_retention_settings(self) -> dict[str, Any]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM retention_settings WHERE id = 1"
            ).fetchone()
        if not row:
            return {
                "events_days": 90,
                "inventory_days": 180,
                "updated_at": None,
            }
        return {
            "events_days": int(row["events_days"]),
            "inventory_days": int(row["inventory_days"]),
            "updated_at": row["updated_at"],
        }

    def update_retention_settings(
        self, *, events_days: int, inventory_days: int
    ) -> None:
        now = utc_now()
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE retention_settings SET
                  events_days = ?, inventory_days = ?, updated_at = ?
                WHERE id = 1
                """,
                (int(events_days), int(inventory_days), now),
            )

    def prune_expired_data(
        self, *, events_days: int, inventory_days: int
    ) -> dict[str, int]:
        """Удалить events/snapshots старше N дней. Оставить новейший snapshot на устройство."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        events_cut = (
            now - timedelta(days=max(1, int(events_days)))
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        inv_cut = (
            now - timedelta(days=max(1, int(inventory_days)))
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with self.connection() as conn:
            ev = conn.execute(
                "DELETE FROM device_events WHERE created_at < ?", (events_cut,)
            )
            # Оставить последний snapshot на каждое устройство, даже если он старый.
            keep_rows = conn.execute(
                """
                SELECT s.id FROM inventory_snapshots s
                WHERE s.id = (
                  SELECT s2.id FROM inventory_snapshots s2
                  WHERE s2.device_id = s.device_id
                  ORDER BY s2.received_at DESC, s2.id DESC
                  LIMIT 1
                )
                """
            ).fetchall()
            keep_ids = {int(r["id"]) for r in keep_rows}
            old_rows = conn.execute(
                """
                SELECT id FROM inventory_snapshots
                WHERE received_at < ?
                """,
                (inv_cut,),
            ).fetchall()
            delete_ids = [
                int(r["id"]) for r in old_rows if int(r["id"]) not in keep_ids
            ]
            for sid in delete_ids:
                conn.execute("DELETE FROM inventory_snapshots WHERE id = ?", (sid,))
            return {
                "events_deleted": int(ev.rowcount or 0),
                "snapshots_deleted": len(delete_ids),
            }

    # --- SMTP settings ---

    def get_smtp_settings(self) -> dict[str, Any]:
        from .smtp_mail import dump_notify_flags, parse_notify_flags

        with self.connection() as conn:
            row = conn.execute("SELECT * FROM smtp_settings WHERE id = 1").fetchone()
        if not row:
            return {
                "enabled": 0,
                "host": "",
                "port": 587,
                "use_ssl": 0,
                "use_starttls": 1,
                "username": "",
                "password_enc": "",
                "from_addr": "",
                "to_addrs": "",
                "notify_json": dump_notify_flags({}),
                "notify": parse_notify_flags({}),
                "updated_at": None,
            }
        data = dict(row)
        data["notify"] = parse_notify_flags(data.get("notify_json"))
        if not (data.get("notify_json") or "").strip():
            data["notify_json"] = dump_notify_flags(data["notify"])
        return data

    def update_smtp_settings(
        self,
        *,
        enabled: bool,
        host: str,
        port: int,
        use_ssl: bool,
        use_starttls: bool,
        username: str,
        from_addr: str,
        to_addrs: str,
        notify_json: Optional[str] = None,
        password_enc: Optional[str] = None,
    ) -> None:
        now = utc_now()
        with self.connection() as conn:
            if password_enc is not None and notify_json is not None:
                conn.execute(
                    """
                    UPDATE smtp_settings SET
                      enabled = ?, host = ?, port = ?, use_ssl = ?, use_starttls = ?,
                      username = ?, password_enc = ?, from_addr = ?, to_addrs = ?,
                      notify_json = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        1 if enabled else 0,
                        host,
                        port,
                        1 if use_ssl else 0,
                        1 if use_starttls else 0,
                        username,
                        password_enc,
                        from_addr,
                        to_addrs,
                        notify_json,
                        now,
                    ),
                )
            elif password_enc is not None:
                conn.execute(
                    """
                    UPDATE smtp_settings SET
                      enabled = ?, host = ?, port = ?, use_ssl = ?, use_starttls = ?,
                      username = ?, password_enc = ?, from_addr = ?, to_addrs = ?,
                      updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        1 if enabled else 0,
                        host,
                        port,
                        1 if use_ssl else 0,
                        1 if use_starttls else 0,
                        username,
                        password_enc,
                        from_addr,
                        to_addrs,
                        now,
                    ),
                )
            elif notify_json is not None:
                conn.execute(
                    """
                    UPDATE smtp_settings SET
                      enabled = ?, host = ?, port = ?, use_ssl = ?, use_starttls = ?,
                      username = ?, from_addr = ?, to_addrs = ?,
                      notify_json = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        1 if enabled else 0,
                        host,
                        port,
                        1 if use_ssl else 0,
                        1 if use_starttls else 0,
                        username,
                        from_addr,
                        to_addrs,
                        notify_json,
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE smtp_settings SET
                      enabled = ?, host = ?, port = ?, use_ssl = ?, use_starttls = ?,
                      username = ?, from_addr = ?, to_addrs = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        1 if enabled else 0,
                        host,
                        port,
                        1 if use_ssl else 0,
                        1 if use_starttls else 0,
                        username,
                        from_addr,
                        to_addrs,
                        now,
                    ),
                )

    def patch_device_meta(self, device_id: str, updates: dict[str, Any]) -> None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT meta_json FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()
            if not row:
                return
            meta = self._parse_meta(row["meta_json"])
            for key, value in updates.items():
                if value is None:
                    meta.pop(key, None)
                else:
                    meta[key] = value
            conn.execute(
                "UPDATE devices SET meta_json = ? WHERE device_id = ?",
                (json.dumps(meta, separators=(",", ":"), ensure_ascii=False), device_id),
            )

    def devices_needing_stale_alert(
        self, *, stale_after_seconds: int
    ) -> list[dict[str, Any]]:
        from .device_health import device_silence_status

        out: list[dict[str, Any]] = []
        for d in self.list_devices(archived=False):
            silence = device_silence_status(
                d.get("last_seen_at"), stale_after_seconds=stale_after_seconds
            )
            meta = d.get("meta") or {}
            if silence["status"] == "stale":
                if meta.get("stale_notified_at"):
                    continue
                out.append(d)
            elif meta.get("stale_notified_at"):
                # Восстановилось — сбросить флаг, чтобы следующий сбой снова алертил.
                self.patch_device_meta(d["device_id"], {"stale_notified_at": None})
        return out

