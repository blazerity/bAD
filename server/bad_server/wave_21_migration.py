"""Одноразовая миграция meta + bad_id (wave 2.1)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from .bad_id import bad_id_for_device, ensure_bad_id_key, is_bad_id
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
    key = ensure_bad_id_key(db)
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
                code = bad_id_for_device(device_id, key)
                dup = conn.execute(
                    "SELECT device_id FROM devices WHERE bad_id = ?",
                    (code,),
                ).fetchone()
                if dup and str(dup["device_id"]) != device_id:
                    logger.error(
                        "wave 2.1: bad_id collision, пропуск device_id=%s",
                        device_id,
                    )
                    continue
                conn.execute(
                    "UPDATE devices SET bad_id = ? WHERE device_id = ?",
                    (code, device_id),
                )


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


_FORMULA_FLAG = "bad_id_formula_v1"
_FORMULA_ATTEMPTS = 3
_PENDING_PREFIX = "pending:"


def run_bad_id_formula_migration(db: Database) -> None:
    """Переписать случайные bad-id формулой. Повторный запуск ничего не меняет.

    Уникальный индекс не даёт сразу записать новый код, если им ещё владеет
    другая строка. Сначала все меняемые коды уходят во временные значения,
    затем записывается формула.
    """
    if db.get_site_secret(_FORMULA_FLAG):
        return
    key = ensure_bad_id_key(db)
    last_exc: Exception | None = None
    for attempt in range(1, _FORMULA_ATTEMPTS + 1):
        try:
            _rewrite_bad_ids(db, key)
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "bad-id: попытка %s из %s не удалась: %s",
                attempt,
                _FORMULA_ATTEMPTS,
                exc,
            )
            if attempt < _FORMULA_ATTEMPTS:
                time.sleep(1)
    raise RuntimeError("bad-id formula migration failed") from last_exc


def _rewrite_bad_ids(db: Database, key: str) -> None:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT device_id, bad_id FROM devices ORDER BY device_id ASC"
        ).fetchall()
    current = {
        str(row["device_id"]): ("" if row["bad_id"] is None else str(row["bad_id"]))
        for row in rows
    }
    desired: dict[str, str] = {}
    owner: dict[str, str] = {}
    colliding: set[str] = set()
    for device_id in current:
        code = bad_id_for_device(device_id, key)
        desired[device_id] = code
        previous = owner.get(code)
        if previous is not None:
            colliding.add(previous)
            colliding.add(device_id)
        else:
            owner[code] = device_id
    if colliding:
        logger.error(
            "bad-id: код совпал, строки не переписаны: %s",
            ", ".join(sorted(colliding)),
        )
    changing = [
        device_id
        for device_id, code in desired.items()
        if device_id not in colliding and current[device_id] != code
    ]
    if changing:
        logger.info("bad-id: пересчёт для %s устройств", len(changing))
        _assign_bad_ids(
            db,
            {device_id: _PENDING_PREFIX + device_id for device_id in changing},
        )
        _assign_bad_ids(
            db,
            {device_id: desired[device_id] for device_id in changing},
        )
    db.set_site_secret(_FORMULA_FLAG, "1")
    logger.info("bad-id formula migration applied (%s)", _FORMULA_FLAG)


def _assign_bad_ids(db: Database, codes: dict[str, str]) -> None:
    items = sorted(codes.items())
    for i in range(0, len(items), _BAD_ID_BATCH):
        chunk = items[i : i + _BAD_ID_BATCH]
        with db.connection() as conn:
            set_lock_timeout(conn)
            for device_id, code in chunk:
                conn.execute(
                    "UPDATE devices SET bad_id = ? WHERE device_id = ?",
                    (code, device_id),
                )


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
