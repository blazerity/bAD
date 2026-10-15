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

    def get_device_by_id(self, device_id: str) -> Optional[sqlite3.Row]:
        with self.connection() as conn:
            return conn.execute(
                "SELECT * FROM devices WHERE device_id = ?", (device_id,)
            ).fetchone()

    def find_device_by_api_key(
        self, api_key: str, verify_fn
    ) -> Optional[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM devices").fetchall()
        for row in rows:
            if verify_fn(row["api_key_hash"], api_key):
                return row
        return None

    def update_heartbeat(
        self,
        device_id: str,
        agent_version: Optional[str],
        last_inventory_at: Optional[str] = None,
    ) -> None:
        now = utc_now()
        with self.connection() as conn:
            if last_inventory_at:
                meta = {"last_inventory_at": last_inventory_at}
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
        now = utc_now()
        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        meta_json = json.dumps(meta or {}, separators=(",", ":"), ensure_ascii=False)
        with self.connection() as conn:
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

    def list_devices(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT device_id, hostname, enrolled_at, last_seen_at,
                       agent_version, meta_json
                FROM devices
                ORDER BY COALESCE(last_seen_at, enrolled_at) DESC
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            meta = {}
            if row["meta_json"]:
                try:
                    meta = json.loads(row["meta_json"])
                except json.JSONDecodeError:
                    meta = {}
            result.append(
                {
                    "device_id": row["device_id"],
                    "hostname": row["hostname"],
                    "enrolled_at": row["enrolled_at"],
                    "last_seen_at": row["last_seen_at"],
                    "agent_version": row["agent_version"],
                    "meta": meta,
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
        meta = {}
        if device["meta_json"]:
            try:
                meta = json.loads(device["meta_json"])
            except json.JSONDecodeError:
                meta = {}
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
            "latest_inventory": inventory,
        }
