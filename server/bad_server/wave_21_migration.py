"""Одноразовая миграция meta + bad_id (wave 2.1)."""

from __future__ import annotations

import json
import logging
from typing import Any

from .bad_id import generate_bad_id, is_bad_id
from .db import Database
from .device_meta import apply_user_presence_patch, enrich_hardware_meta
from .fleet_buckets import sort_ipv4_addresses

logger = logging.getLogger(__name__)

_FLAG = "wave_21_meta_v1"


def run_wave_21_migration(db: Database) -> None:
    if db.get_site_secret(_FLAG):
        return
    with db.connection() as conn:
        conn.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS bad_id TEXT")
        rows = conn.execute(
            """
            SELECT device_id, meta_json FROM devices
            WHERE bad_id IS NULL OR bad_id = ''
            ORDER BY enrolled_at ASC, device_id ASC
            """
        ).fetchall()
        for row in rows:
            device_id = row["device_id"]
            for _ in range(8):
                code = generate_bad_id()
                dup = conn.execute(
                    "SELECT 1 FROM devices WHERE bad_id = ?", (code,)
                ).fetchone()
                if dup:
                    continue
                conn.execute(
                    "UPDATE devices SET bad_id = ? WHERE device_id = ?",
                    (code, device_id),
                )
                break
        # backfill meta from latest snapshot
        devices = conn.execute(
            "SELECT device_id, meta_json FROM devices"
        ).fetchall()
        for drow in devices:
            did = drow["device_id"]
            meta = db._parse_meta(drow["meta_json"])
            snap = conn.execute(
                """
                SELECT payload_json FROM inventory_snapshots
                WHERE device_id = ?
                ORDER BY received_at DESC, id DESC
                LIMIT 1
                """,
                (did,),
            ).fetchone()
            payload: dict[str, Any] = {}
            if snap:
                try:
                    parsed = json.loads(snap["payload_json"])
                    if isinstance(parsed, dict):
                        payload = parsed
                except json.JSONDecodeError:
                    payload = {}
            hw = payload.get("hardware") if isinstance(payload.get("hardware"), dict) else {}
            host = payload.get("host") if isinstance(payload.get("host"), dict) else {}
            users = payload.get("users") if isinstance(payload.get("users"), dict) else {}
            network = payload.get("network") if isinstance(payload.get("network"), dict) else {}
            enrich_hardware_meta(meta, hardware=hw, host=host, network=network)
            apply_user_presence_patch(meta, users, existing=meta)
            if not meta.get("last_logged_on"):
                logged = meta.get("logged_on")
                if isinstance(logged, list) and logged:
                    meta["last_logged_on"] = logged[0]
                    meta["user_presence"] = "last"
            ips = meta.get("ipv4_addresses")
            if isinstance(ips, list):
                meta["ipv4_addresses"] = sort_ipv4_addresses([str(x) for x in ips])
            conn.execute(
                "UPDATE devices SET meta_json = ? WHERE device_id = ?",
                (
                    json.dumps(meta, separators=(",", ":"), ensure_ascii=False),
                    did,
                ),
            )
        try:
            conn.execute("ALTER TABLE devices ALTER COLUMN bad_id SET NOT NULL")
        except Exception:
            pass
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_devices_bad_id ON devices(bad_id)"
        )
        conn.execute(
            "INSERT INTO site_secrets(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_FLAG, "1"),
        )
    logger.info("wave 2.1 migration applied (%s)", _FLAG)


def resolve_device_ref(db: Database, ref: str) -> str | None:
    text = (ref or "").strip()
    if not text:
        return None
    if is_bad_id(text):
        with db.connection() as conn:
            row = conn.execute(
                "SELECT device_id FROM devices WHERE bad_id = ?", (text,)
            ).fetchone()
        return row["device_id"] if row else None
    row = db.get_device_detail(text)
    return row["device_id"] if row else None
