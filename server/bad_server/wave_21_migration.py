"""Одноразовая миграция meta + bad_id (wave 2.1)."""

from __future__ import annotations

import json
import logging
from typing import Any

from .bad_id import generate_bad_id, is_bad_id
from .db import Database
from .device_meta import apply_user_presence_patch, enrich_hardware_meta
from .fleet_buckets import sort_ipv4_addresses
from .postgres_ddl import ensure_devices_bad_id_index, set_lock_timeout

logger = logging.getLogger(__name__)

_FLAG = "wave_21_meta_v1"
_META_BATCH = 40
_BAD_ID_BATCH = 100


def _ensure_bad_id_column(db: Database) -> None:
    with db.connection() as conn:
        set_lock_timeout(conn)
        conn.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS bad_id TEXT")


def _backfill_bad_ids(db: Database) -> None:
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT device_id FROM devices
            WHERE bad_id IS NULL OR bad_id = ''
            ORDER BY enrolled_at ASC, device_id ASC
            """
        ).fetchall()
    pending = [str(r["device_id"]) for r in rows]
    if not pending:
        return
    logger.info("wave 2.1: backfill bad_id for %s devices", len(pending))
    for i in range(0, len(pending), _BAD_ID_BATCH):
        chunk = pending[i : i + _BAD_ID_BATCH]
        with db.connection() as conn:
            set_lock_timeout(conn)
            for device_id in chunk:
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


def _backfill_device_meta(db: Database) -> None:
    with db.connection() as conn:
        rows = conn.execute("SELECT device_id, meta_json FROM devices").fetchall()
    if not rows:
        return
    logger.info("wave 2.1: enrich meta for %s devices", len(rows))
    for i in range(0, len(rows), _META_BATCH):
        batch = rows[i : i + _META_BATCH]
        with db.connection() as conn:
            set_lock_timeout(conn)
            for drow in batch:
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
                hw = (
                    payload.get("hardware")
                    if isinstance(payload.get("hardware"), dict)
                    else {}
                )
                host = (
                    payload.get("host") if isinstance(payload.get("host"), dict) else {}
                )
                users = (
                    payload.get("users")
                    if isinstance(payload.get("users"), dict)
                    else {}
                )
                network = (
                    payload.get("network")
                    if isinstance(payload.get("network"), dict)
                    else {}
                )
                enrich_hardware_meta(meta, hardware=hw, host=host, network=network)
                apply_user_presence_patch(meta, users, existing=meta)
                if not meta.get("last_logged_on"):
                    logged = meta.get("logged_on")
                    if isinstance(logged, list) and logged:
                        meta["last_logged_on"] = logged[0]
                        meta["user_presence"] = "last"
                ips = meta.get("ipv4_addresses")
                if isinstance(ips, list):
                    meta["ipv4_addresses"] = sort_ipv4_addresses(
                        [str(x) for x in ips]
                    )
                conn.execute(
                    "UPDATE devices SET meta_json = ? WHERE device_id = ?",
                    (
                        json.dumps(meta, separators=(",", ":"), ensure_ascii=False),
                        did,
                    ),
                )


def _try_bad_id_not_null(db: Database) -> None:
    with db.connection() as conn:
        set_lock_timeout(conn)
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM devices WHERE bad_id IS NULL OR bad_id = ''"
        ).fetchone()
        if int(row["n"] or 0) > 0:
            logger.warning(
                "wave 2.1: skip NOT NULL on bad_id (%s rows still empty)",
                row["n"],
            )
            return
        try:
            conn.execute("ALTER TABLE devices ALTER COLUMN bad_id SET NOT NULL")
        except Exception as exc:
            logger.warning("wave 2.1: ALTER bad_id SET NOT NULL skipped: %s", exc)


def run_wave_21_migration(db: Database) -> None:
    _ensure_bad_id_column(db)
    ensure_devices_bad_id_index(db.database_url)
    if db.get_site_secret(_FLAG):
        return
    _backfill_bad_ids(db)
    _backfill_device_meta(db)
    _try_bad_id_not_null(db)
    db.set_site_secret(_FLAG, "1")
    ensure_devices_bad_id_index(db.database_url)
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
