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

class DbDevicesMixin:

    def save_enrollment_request(
        self,
        request_id: str,
        hostname: str,
        ip: str,
        serial: str,
        bad_id: str = "",
        machine_guid: str = "",
        smbios_uuid: str = "",
    ) -> Optional[str]:
        """Создать или обновить заявку по отпечатку. None — pending уже на потолке.

        Уже лежащий BAD- не заменяется. Текст не вида BAD- и 8 hex номером не пишется.
        """
        now = utc_now()
        raw_kept = (bad_id or "").strip()
        kept_id = raw_kept if raw_kept and is_bad_id(raw_kept) else None
        guid = machine_guid or ""
        uuid = smbios_uuid or ""
        cutoff = _utc_cutoff(PENDING_ENROLLMENT_TTL)
        with self.connection() as conn:
            conn.execute(
                """
                DELETE FROM enrollment_requests
                WHERE status = 'pending' AND created_at < %s
                """,
                (cutoff,),
            )
            row = conn.execute(
                "SELECT status FROM enrollment_requests WHERE id = %s",
                (request_id,),
            ).fetchone()
            if row:
                status_name = str(row["status"])
                if status_name == "pending":
                    conn.execute(
                        """
                        UPDATE enrollment_requests
                        SET hostname = %s, ip = %s, serial = %s,
                            bad_id = COALESCE(%s, bad_id),
                            machine_guid = %s,
                            smbios_uuid = %s,
                            seen_at = %s
                        WHERE id = %s AND status = 'pending'
                        """,
                        (hostname, ip, serial, kept_id, guid, uuid, now, request_id),
                    )
                    return status_name
                return status_name
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM enrollment_requests WHERE status = 'pending'"
            ).fetchone()
            if int(pending["n"]) >= PENDING_ENROLLMENT_CAP:
                return None
            conn.execute(
                """
                INSERT INTO enrollment_requests(
                  id, hostname, ip, serial, created_at, status, bad_id,
                  machine_guid, smbios_uuid, seen_at
                ) VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)
                """,
                (request_id, hostname, ip, serial, now, kept_id, guid, uuid, now),
            )
        return "pending"


    def list_pending_enrollment_requests(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, hostname, ip, serial, created_at, seen_at
                FROM enrollment_requests
                WHERE status = 'pending'
                ORDER BY created_at
                """
            ).fetchall()
        return [dict(row) for row in rows]


    def list_approved_enrollment_requests(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, hostname, ip, bad_id, seen_at, link_at,
                       archive_total, archive_received, link_state, link_error
                FROM enrollment_requests
                WHERE status = 'approved'
                ORDER BY created_at
                """
            ).fetchall()
        return [dict(row) for row in rows]


    def set_link_progress(
        self,
        bad_id: str,
        received: int,
        total: int,
        state: str,
        error: str,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE enrollment_requests
                SET archive_received = %s, archive_total = %s,
                    link_state = %s, link_error = %s, link_at = %s
                WHERE bad_id = %s AND status = 'approved'
                """,
                (int(received), int(total), state or "", error or "", utc_now(), bad_id),
            )


    def mark_enrollment_installed(self, bad_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE enrollment_requests
                SET status = 'installed'
                WHERE bad_id = %s AND status = 'approved'
                """,
                (bad_id,),
            )


    def approved_enrollment_bad_ids(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT bad_id FROM enrollment_requests
                WHERE status = 'approved' AND bad_id IS NOT NULL
                """
            ).fetchall()
        return [str(row["bad_id"]) for row in rows if row["bad_id"]]


    def get_enrollment_request(self, request_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM enrollment_requests WHERE id = %s",
                (request_id,),
            ).fetchone()
        return dict(row) if row else None


    def mark_enrollment_request_approved(
        self,
        request_id: str,
        bad_id: str,
        api_key_enc: str,
        signing_key_enc: str,
        archive_password_enc: str = "",
    ) -> bool:
        with self.connection() as conn:
            updated = conn.execute(
                """
                UPDATE enrollment_requests
                SET status = 'approved', bad_id = %s,
                    api_key_enc = %s, signing_key_enc = %s,
                    archive_password_enc = %s
                WHERE id = %s AND status = 'pending'
                """,
                (bad_id, api_key_enc, signing_key_enc, archive_password_enc or "", request_id),
            )
        return updated.rowcount == 1


    def get_device_meta(self, bad_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT meta_json FROM devices WHERE bad_id = %s",
                (bad_id,),
            ).fetchone()
        if not row:
            return None
        return self._parse_meta(row["meta_json"])


    def _devices_filter_sql(
        self,
        *,
        tag: Optional[str],
        archived: Optional[bool],
        q: Optional[str],
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if archived is True:
            clauses.append("COALESCE(archived, 0) != 0")
        elif archived is False:
            clauses.append("COALESCE(archived, 0) = 0")
        wanted = (tag or "").strip()
        if wanted:
            clauses.append("tags_json ILIKE %s")
            params.append(f"%{wanted}%")
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            clauses.append(
                "(hostname ILIKE %s OR bad_id ILIKE %s "
                "OR COALESCE(meta_json, '') ILIKE %s "
                "OR COALESCE(tags_json, '') ILIKE %s)"
            )
            params.extend([like, like, like, like])
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params


    def list_devices(
        self,
        tag: Optional[str] = None,
        *,
        archived: Optional[bool] = False,
        q: Optional[str] = None,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        where, params = self._devices_filter_sql(
            tag=tag, archived=archived, q=q
        )
        sql = f"""
            SELECT bad_id, hostname, enrolled_at, last_seen_at,
                   agent_version, meta_json, tags_json, revoked, archived,
                   shared_exchange_at
            FROM devices
            {where}
            ORDER BY COALESCE(last_seen_at, enrolled_at) DESC NULLS LAST
        """
        wanted_cf = (tag or "").strip().casefold()
        paginate_sql = not wanted_cf
        if paginate_sql and limit is not None:
            sql += " LIMIT %s OFFSET %s"
            params.extend([max(1, int(limit)), max(0, int(offset))])
        elif paginate_sql and offset:
            sql += " OFFSET %s"
            params.append(max(0, int(offset)))
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        result = [self._device_row_dict(row) for row in rows]
        if wanted_cf:
            result = [
                d
                for d in result
                if wanted_cf in {t.casefold() for t in (d.get("tags") or [])}
            ]
            if limit is not None:
                start = max(0, int(offset))
                end = start + max(1, int(limit))
                result = result[start:end]
        return result


    def count_devices(
        self,
        tag: Optional[str] = None,
        *,
        archived: Optional[bool] = False,
        q: Optional[str] = None,
    ) -> int:
        where, params = self._devices_filter_sql(
            tag=tag, archived=archived, q=q
        )
        wanted_cf = (tag or "").strip().casefold()
        if not wanted_cf:
            sql = f"SELECT COUNT(*) AS c FROM devices{where}"
            with self.connection() as conn:
                row = conn.execute(sql, params).fetchone()
            return int(row["c"] if row else 0)
        return len(self.list_devices(tag=tag, archived=archived, q=q))


    def search_devices_global(
        self, q: str, *, limit: int = 25
    ) -> list[dict[str, Any]]:
        """ILIKE по hostname, bad_id, meta_json и tags_json."""
        query = (q or "").strip()
        if not query:
            return []
        cap = max(1, int(limit))
        like = f"%{query}%"
        sql = """
            SELECT bad_id, hostname, enrolled_at, last_seen_at,
                   agent_version, meta_json, tags_json, revoked, archived
            FROM devices
            WHERE hostname ILIKE %s
               OR bad_id ILIKE %s
               OR COALESCE(meta_json, '') ILIKE %s
               OR COALESCE(tags_json, '') ILIKE %s
            ORDER BY COALESCE(last_seen_at, enrolled_at) DESC NULLS LAST
            LIMIT %s
        """
        with self.connection() as conn:
            rows = conn.execute(
                sql, (like, like, like, like, cap)
            ).fetchall()
        return [self._device_row_dict(row) for row in rows]


    def list_all_tags(self) -> list[str]:
        seen: dict[str, str] = {}
        for device in self.list_devices():
            for tag in device.get("tags") or []:
                key = tag.casefold()
                if key not in seen:
                    seen[key] = tag
        return sorted(seen.values(), key=str.casefold)


    def set_device_tags(self, bad_id: str, tags: Any) -> list[str]:
        """Нормализовать и сохранить tags. Единая точка записи для очистки тегов."""
        from .device_health import normalize_tags

        clean = normalize_tags(tags)
        payload = _compact_json(clean)
        with self.connection() as conn:
            cur = conn.execute(
                "UPDATE devices SET tags_json = %s WHERE bad_id = %s",
                (payload, bad_id),
            )
            if cur.rowcount == 0:
                raise KeyError(bad_id)
        return clean


    def get_device_detail(self, bad_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            device = conn.execute(
                "SELECT * FROM devices WHERE bad_id = %s", (bad_id,)
            ).fetchone()
            if not device:
                return None
            snap = conn.execute(
                """
                SELECT id, received_at, schema_version, payload_json
                FROM inventory_snapshots
                WHERE bad_id = %s
                ORDER BY received_at DESC, id DESC
                LIMIT 1
                """,
                (bad_id,),
            ).fetchone()
        meta = self._parse_meta(device["meta_json"])
        inventory = None
        serial_number = None
        smbios_uuid = None
        bios_serial = None
        identifying_number = None
        baseboard_serial = None
        disk_serials: list[str] = []
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
                signals = self.extract_identity_signals(meta=meta, payload=payload)
                serial_number = signals.get("serial_number") or serial_number
                smbios_uuid = signals.get("smbios_uuid")
                bios_serial = signals.get("bios_serial")
                identifying_number = signals.get("identifying_number")
                baseboard_serial = signals.get("baseboard_serial")
                disk_serials = list(signals.get("disk_serials") or [])
        from_meta = self.extract_identity_signals(meta=meta)
        serial_number = serial_number or from_meta.get("serial_number")
        smbios_uuid = smbios_uuid or from_meta.get("smbios_uuid")
        bios_serial = bios_serial or from_meta.get("bios_serial")
        identifying_number = identifying_number or from_meta.get("identifying_number")
        baseboard_serial = baseboard_serial or from_meta.get("baseboard_serial")
        if not disk_serials:
            disk_serials = list(from_meta.get("disk_serials") or [])
        return {
            "bad_id": device["bad_id"],
            "hostname": device["hostname"],
            "enrolled_at": device["enrolled_at"],
            "last_seen_at": device["last_seen_at"],
            "agent_version": device["agent_version"],
            "meta": meta,
            "tags": self._parse_tags(device["tags_json"]),
            "revoked": bool(device["revoked"]),
            "archived": bool(device["archived"]),
            "serial_number": serial_number,
            "smbios_uuid": smbios_uuid,
            "bios_serial": bios_serial,
            "identifying_number": identifying_number,
            "baseboard_serial": baseboard_serial,
            "disk_serials": disk_serials,
            "model": model,
            "chassis_type": meta.get("chassis_type"),
            "latest_inventory": inventory,
        }


    # --- жизненный цикл устройства (revoke / archive / delete) ---

    def _set_device_flag(self, bad_id: str, column: str, value: bool) -> bool:
        if column not in {"revoked", "archived"}:
            raise ValueError(f"unsupported device flag: {column}")
        with self.connection() as conn:
            cur = conn.execute(
                f"UPDATE devices SET {column} = %s WHERE bad_id = %s",
                (1 if value else 0, bad_id),
            )
            return cur.rowcount > 0


    def set_device_revoked(self, bad_id: str, revoked: bool) -> bool:
        return self._set_device_flag(bad_id, "revoked", revoked)


    def set_device_archived(self, bad_id: str, archived: bool) -> bool:
        return self._set_device_flag(bad_id, "archived", archived)


    def delete_device(self, bad_id: str) -> bool:
        """Жёстко удалить device и связанные строки (snapshots + cascades)."""
        with self.connection() as conn:
            exists = conn.execute(
                "SELECT bad_id FROM devices WHERE bad_id = %s", (bad_id,)
            ).fetchone()
            if not exists:
                return False
            conn.execute(
                "DELETE FROM inventory_snapshots WHERE bad_id = %s", (bad_id,)
            )
            conn.execute(
                "DELETE FROM device_events WHERE bad_id = %s", (bad_id,)
            )
            conn.execute(
                "DELETE FROM device_config_overrides WHERE bad_id = %s", (bad_id,)
            )
            conn.execute("DELETE FROM devices WHERE bad_id = %s", (bad_id,))
            return True


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
                      AND enrolled_at > %s
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


    def list_fleet_active_archived(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Один проход по таблице devices для Обзора/Дашборда."""
        all_rows = self.list_devices(archived=None)
        active = [d for d in all_rows if not d.get("archived")]
        archived = [d for d in all_rows if d.get("archived")]
        return active, archived


    def overview_stats(
        self,
        *,
        stale_after_seconds: int,
        active: Optional[list[dict[str, Any]]] = None,
        archived: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        from .device_health import device_silence_status

        if active is None or archived is None:
            active, archived = self.list_fleet_active_archived()
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

        hw_types = sorted(HARDWARE_ALERT_TYPES)
        placeholders = ",".join("%s" for _ in hw_types)
        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT e.id, e.bad_id, e.type, e.summary, e.detail_json,
                       e.created_at, d.hostname
                FROM device_events e
                LEFT JOIN devices d ON d.bad_id = e.bad_id
                WHERE e.type IN ({placeholders})
                ORDER BY e.created_at DESC, e.id DESC
                LIMIT 16
                """,
                tuple(hw_types),
            ).fetchall()
        recent_hw = self._device_event_rows(rows, include_detail=False)
        total_active = len(active)
        archived_n = len(archived)
        return {
            "total_active": total_active,
            "online": online,
            "stale": stale,
            "archived": archived_n,
            "total_all": total_active + archived_n,
            "park": {
                "online": online,
                "stale": stale,
                "archived": archived_n,
                "total_active": total_active,
            },
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
            detail = self.get_device_detail(d["bad_id"]) or d
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
                    "bad_id": d["bad_id"],
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
                    "bad_id": d.get("bad_id") or "",
                }
            )
        return rows


    def patch_device_meta(self, bad_id: str, updates: dict[str, Any]) -> None:
        with self.connection() as conn:
            try:
                meta = self._lock_device_meta(conn, bad_id)
            except KeyError:
                return
            for key, value in updates.items():
                if value is None:
                    meta.pop(key, None)
                else:
                    meta[key] = value
            self._save_device_meta(conn, bad_id, meta)
