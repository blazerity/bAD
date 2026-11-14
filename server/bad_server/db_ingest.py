from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .bad_id import is_bad_id
from .db_backend import CompatConnection
from .db import (
    PENDING_ENROLLMENT_CAP,
    PENDING_ENROLLMENT_TTL,
    _compact_json,
    _utc_cutoff,
    logger,
    utc_now,
)
from .device_refresh import _utc_iso_ge

class DbIngestMixin:

    def update_heartbeat(
        self,
        bad_id: str,
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
            meta = None
            if touch_meta:
                meta = self._lock_device_meta(conn, bad_id)
                stale_inventory_ack = bool(
                    last_inventory_at
                    and _utc_iso_ge(meta.get("last_inventory_at"), last_inventory_at)
                )
                if last_inventory_at and not stale_inventory_ack:
                    meta["last_inventory_at"] = last_inventory_at
                meta.update(health)
                if config_local_provided and not stale_inventory_ack:
                    from .agent_config import sanitize_config_local

                    cleaned = sanitize_config_local(config_local)
                    if not cleaned.get("keys") and not cleaned.get("server_url"):
                        meta.pop("config_local", None)
                    else:
                        block = dict(cleaned)
                        block["reported_at"] = now
                        meta["config_local"] = block
            conn.execute(
                """
                UPDATE devices
                SET last_seen_at = %s,
                    agent_version = COALESCE(%s, agent_version)
                WHERE bad_id = %s
                """,
                (now, agent_version, bad_id),
            )
            if meta is not None:
                self._save_device_meta(conn, bad_id, meta)


    def store_inventory(
        self,
        bad_id: str,
        schema_version: int,
        payload: dict[str, Any],
        hostname: Optional[str],
        agent_version: Optional[str],
        meta: Optional[dict[str, Any]],
        retention: int,
    ) -> dict[str, Any]:
        from .inventory_events import diff_inventory_snapshots

        now = utc_now()
        payload_json = _compact_json(payload)
        with self.connection() as conn:
            prev_row = self._latest_snapshot_row(conn, bad_id)
            previous = (
                self._snapshot_payload(prev_row["payload_json"]) if prev_row else None
            )
            if previous and prev_row and self._inventory_payload_superseded(
                previous, payload
            ):
                return {
                    "snapshot_id": int(prev_row["id"]),
                    "events": [],
                }

            merged_meta = self._lock_device_meta(conn, bad_id)
            merged_meta.update(meta or {})
            users_block = (
                payload.get("users")
                if isinstance(payload.get("users"), dict)
                else None
            )
            from .device_meta import apply_user_presence_patch

            apply_user_presence_patch(
                merged_meta, users_block, existing=merged_meta
            )
            meta_json = _compact_json(merged_meta)
            conn.execute(
                """
                UPDATE devices
                SET hostname = COALESCE(%s, hostname),
                    last_seen_at = %s,
                    agent_version = COALESCE(%s, agent_version),
                    meta_json = %s
                WHERE bad_id = %s
                """,
                (hostname, now, agent_version, meta_json, bad_id),
            )
            cur = conn.execute(
                """
                INSERT INTO inventory_snapshots(
                  bad_id, received_at, schema_version, payload_json
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (bad_id, now, schema_version, payload_json),
            )
            row = cur.fetchone()
            snapshot_id = int(row["id"] if row else 0)

            events = diff_inventory_snapshots(previous, payload)
            for event in events:
                detail = event.get("detail")
                self._insert_device_event(
                    conn,
                    bad_id,
                    event["type"],
                    event["summary"],
                    _compact_json(detail if detail is not None else {}),
                    now,
                )

            # удалить старше лимита retention по числу на устройство (env BAD_SNAPSHOT_RETENTION)
            conn.execute(
                """
                DELETE FROM inventory_snapshots
                WHERE bad_id = %s
                  AND id NOT IN (
                    SELECT id FROM inventory_snapshots
                    WHERE bad_id = %s
                    ORDER BY received_at DESC, id DESC
                    LIMIT %s
                  )
                """,
                (bad_id, bad_id, retention),
            )
            return {"snapshot_id": snapshot_id, "events": events}


    def latest_snapshot_payload(self, bad_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = self._latest_snapshot_row(conn, bad_id)
        if not row:
            return None
        return self._snapshot_payload(row["payload_json"])


    def _latest_snapshot_row(self, conn: CompatConnection, bad_id: str) -> Any:
        return conn.execute(
            """
            SELECT id, payload_json FROM inventory_snapshots
            WHERE bad_id = %s
            ORDER BY received_at DESC, id DESC
            LIMIT 1
            """,
            (bad_id,),
        ).fetchone()

    @staticmethod
    def _inventory_payload_superseded(
        latest: dict[str, Any], incoming: dict[str, Any]
    ) -> bool:
        """True if incoming must not replace latest by collected_at."""
        from .device_health import parse_utc

        latest_raw = latest.get("collected_at")
        latest_at = (
            parse_utc(str(latest_raw)) if latest_raw not in (None, "") else None
        )
        if latest_at is None:
            return False

        incoming_raw = incoming.get("collected_at")
        incoming_at = (
            parse_utc(str(incoming_raw))
            if incoming_raw not in (None, "")
            else None
        )
        if incoming_at is None:
            return True
        return incoming_at < latest_at


    @staticmethod
    def _snapshot_payload(raw: Any) -> Optional[dict[str, Any]]:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None


    def latest_inventory_payload(self, bad_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            snap = self._latest_snapshot_row(conn, bad_id)
        if not snap:
            return None
        return self._snapshot_payload(snap["payload_json"])


    def latest_inventory_payloads(
        self, bad_ids: list[str], *, cap: int = 500
    ) -> dict[str, dict[str, Any]]:
        """Latest inventory payload по bad_id (один проход, cap для Дашборда D4/D5)."""
        ids = [d for d in bad_ids if d][: max(0, int(cap))]
        if not ids:
            return {}
        out: dict[str, dict[str, Any]] = {}
        placeholders = ",".join("%s" for _ in ids)
        with self.connection() as conn:
            # Postgres: DISTINCT ON; CompatConnection прокидывает как есть.
            rows = conn.execute(
                f"""
                SELECT DISTINCT ON (bad_id) bad_id, payload_json
                FROM inventory_snapshots
                WHERE bad_id IN ({placeholders})
                ORDER BY bad_id, received_at DESC, id DESC
                """,
                tuple(ids),
            ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                out[str(row["bad_id"])] = payload
        return out
