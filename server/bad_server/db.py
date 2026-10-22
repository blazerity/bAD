from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from .db_backend import (
    SCHEMA_SQL,
    CompatConnection,
    connect_postgres,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Database:
    """Persistence hub — Postgres через `BAD_DATABASE_URL`."""

    def __init__(self, database_url: str) -> None:
        url = (database_url or "").strip()
        if not url:
            raise RuntimeError("BAD_DATABASE_URL is required (Postgres only)")
        self.database_url = url
        self._init_schema()

    def _connect(self) -> CompatConnection:
        return connect_postgres(self.database_url)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            for table in ("ldap_settings", "retention_settings", "smtp_settings"):
                conn.execute(
                    f"INSERT INTO {table}(id) VALUES (1) ON CONFLICT DO NOTHING"
                )
            conn.commit()

    @contextmanager
    def connection(self) -> Iterator[CompatConnection]:
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
    ) -> Optional[Any]:
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
                RETURNING id
                """,
                (device_id, now, schema_version, payload_json),
            )
            row = cur.fetchone()
            snapshot_id = int(row["id"] if row else 0)

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
        sql = """
            SELECT device_id, hostname, enrolled_at, last_seen_at,
                   agent_version, meta_json, tags_json, revoked, archived
            FROM devices
        """
        params: list[Any] = []
        if archived is True:
            sql += " WHERE COALESCE(archived, 0) != 0"
        elif archived is False:
            sql += " WHERE COALESCE(archived, 0) = 0"
        sql += " ORDER BY COALESCE(last_seen_at, enrolled_at) DESC"
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
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
                # hardware ids из meta-кэша (после inventory)
                if query not in hay:
                    meta = self._parse_meta(row["meta_json"])
                    id_bits = [
                        str(meta.get("serial_number") or ""),
                        str(meta.get("smbios_uuid") or ""),
                        str(meta.get("bios_serial") or ""),
                        str(meta.get("identifying_number") or ""),
                        str(meta.get("baseboard_serial") or ""),
                    ]
                    for disk in meta.get("disk_serials") or []:
                        id_bits.append(str(disk or ""))
                    id_hay = " ".join(id_bits).casefold()
                    if query not in id_hay:
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

    def _event_list_filters(
        self,
        *,
        device_id: Optional[str],
        q: Optional[str],
        importance: Optional[str],
    ) -> tuple[str, list[Any]]:
        from .event_importance import types_at_least

        clauses: list[str] = []
        params: list[Any] = []
        if device_id:
            clauses.append("e.device_id = ?")
            params.append(device_id)
        imp = (importance or "").strip().casefold()
        if imp and imp != "all":
            types = sorted(types_at_least(imp))
            if types:
                placeholders = ",".join("?" for _ in types)
                clauses.append(f"e.type IN ({placeholders})")
                params.extend(types)
        elif imp != "all":
            # default UI: medium+
            types = sorted(types_at_least("medium"))
            if types:
                placeholders = ",".join("?" for _ in types)
                clauses.append(f"e.type IN ({placeholders})")
                params.extend(types)
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            clauses.append(
                "(e.summary ILIKE ? OR e.type ILIKE ? OR d.hostname ILIKE ? "
                "OR e.device_id ILIKE ?)"
            )
            params.extend([like, like, like, like])
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params

    def list_device_events(
        self,
        *,
        device_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        q: Optional[str] = None,
        importance: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        sql = """
            SELECT e.id, e.device_id, e.type, e.summary, e.detail_json,
                   e.created_at, d.hostname
            FROM device_events e
            LEFT JOIN devices d ON d.device_id = e.device_id
        """
        where, params = self._event_list_filters(
            device_id=device_id, q=q, importance=importance
        )
        sql += where
        sql += " ORDER BY e.created_at DESC, e.id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
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

    def count_device_events(
        self,
        *,
        device_id: Optional[str] = None,
        q: Optional[str] = None,
        importance: Optional[str] = None,
    ) -> int:
        sql = """
            SELECT COUNT(*) AS c
            FROM device_events e
            LEFT JOIN devices d ON d.device_id = e.device_id
        """
        where, params = self._event_list_filters(
            device_id=device_id, q=q, importance=importance
        )
        sql += where
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
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
            "smbios_uuid": smbios_uuid,
            "bios_serial": bios_serial,
            "identifying_number": identifying_number,
            "baseboard_serial": baseboard_serial,
            "disk_serials": disk_serials,
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
                RETURNING id
                """,
                (
                    username,
                    password_hash,
                    role,
                    1 if must_change_password else 0,
                    now,
                ),
            )
            row = cur.fetchone()
            return int(row["id"] if row else 0)

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
    def _msi_row(row: Any) -> dict[str, Any]:
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
    def _row_to_policy(row: Any) -> dict[str, Any]:
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
                RETURNING id
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
            prow = cur.fetchone()
            policy_id = int(prow["id"] if prow else 0)
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

    def list_device_config_overrides_map(self) -> dict[str, dict[str, Any]]:
        """device_id → settings dict (для batch drift без N запросов)."""
        out: dict[str, dict[str, Any]] = {}
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT device_id, settings_json FROM device_config_overrides"
            ).fetchall()
        for row in rows:
            try:
                settings = json.loads(row["settings_json"] or "{}")
            except json.JSONDecodeError:
                settings = {}
            if isinstance(settings, dict):
                out[str(row["device_id"])] = settings
        return out

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

    def latest_inventory_payloads(
        self, device_ids: list[str], *, cap: int = 500
    ) -> dict[str, dict[str, Any]]:
        """Latest inventory payload по device_id (один проход, cap для Дашборда D4/D5)."""
        ids = [d for d in device_ids if d][: max(0, int(cap))]
        if not ids:
            return {}
        out: dict[str, dict[str, Any]] = {}
        placeholders = ",".join("?" for _ in ids)
        with self.connection() as conn:
            # Postgres: DISTINCT ON; CompatConnection прокидывает как есть.
            rows = conn.execute(
                f"""
                SELECT DISTINCT ON (device_id) device_id, payload_json
                FROM inventory_snapshots
                WHERE device_id IN ({placeholders})
                ORDER BY device_id, received_at DESC, id DESC
                """,
                tuple(ids),
            ).fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                out[str(row["device_id"])] = payload
        return out

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

    # Placeholder serials (как CleanWmiString у агента) — не сигналы «та же машина».
    _WEAK_SERIAL_EXACT = frozenset(
        {
            "none",
            "n/a",
            "na",
            "default string",
            "system serial number",
            "system product name",
            "system manufacturer",
            "to be filled by o.e.m.",
            "o.e.m.",
            "oem",
            "unknown",
            "not specified",
            "not available",
            "0",
            "00000000",
        }
    )

    # Скалярные hardware-id для duplicates / meta (не PK).
    IDENTITY_SCALAR_KEYS = (
        "serial_number",
        "smbios_uuid",
        "bios_serial",
        "identifying_number",
        "baseboard_serial",
    )

    # Merge match (вариант 2, без диска/hostname) — одна функция на список и merge_devices.
    MERGE_STRONG_KEYS = ("serial_number", "smbios_uuid")
    MERGE_WEAK_KEYS = ("bios_serial", "identifying_number", "baseboard_serial")

    @classmethod
    def _identity_values_equal(cls, key: str, left: Any, right: Any) -> bool:
        if not left or not right:
            return False
        if key == "smbios_uuid":
            a = cls.normalize_smbios_uuid(left)
            b = cls.normalize_smbios_uuid(right)
            return bool(a and b and a == b)
        a = cls.normalize_serial_number(left)
        b = cls.normalize_serial_number(right)
        return bool(a and b and a.casefold() == b.casefold())

    @classmethod
    def _matched_identity_keys(
        cls,
        keys: tuple[str, ...],
        left: dict[str, Any],
        right: dict[str, Any],
    ) -> list[str]:
        return [
            key
            for key in keys
            if cls._identity_values_equal(key, left.get(key), right.get(key))
        ]

    @classmethod
    def merge_identity_matched(
        cls,
        left: Optional[dict[str, Any]],
        right: Optional[dict[str, Any]],
    ) -> list[str]:
        """Поля, дающие право на склейку (пусто = кнопки merge нет).

        Сильное: достаточно одного из ``serial_number`` / ``smbios_uuid``.
        Слабая пара: ≥2 из ``bios_serial`` / ``identifying_number`` / ``baseboard_serial``.
        Hostname и ``disk_serial*`` не входят. OEM/пустые отсекаются нормализацией.
        """
        a = left if isinstance(left, dict) else {}
        b = right if isinstance(right, dict) else {}
        strong = cls._matched_identity_keys(cls.MERGE_STRONG_KEYS, a, b)
        weak = cls._matched_identity_keys(cls.MERGE_WEAK_KEYS, a, b)
        # strong непустой → strong+weak; иначе weak только при паре (≥2).
        if strong or len(weak) >= 2:
            return strong + weak
        return []

    @staticmethod
    def normalize_smbios_uuid(raw: Any) -> Optional[str]:
        """Нормализованный SMBIOS UUID или None для пустых/placeholder (all-F / all-zero)."""
        if raw is None:
            return None
        text = str(raw).strip().casefold()
        if not text:
            return None
        if text.startswith("{") and text.endswith("}"):
            text = text[1:-1].strip()
        compact = text.replace("-", "")
        if compact == "f" * 32 or compact == "0" * 32:
            return None
        return text

    @classmethod
    def normalize_serial_number(cls, raw: Any) -> Optional[str]:
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        folded = text.casefold()
        if folded in cls._WEAK_SERIAL_EXACT:
            return None
        if folded.startswith("to be filled") or folded.startswith("fill by oem"):
            return None
        return text

    def _pick_serial(
        self,
        *candidates: Any,
    ) -> Optional[str]:
        for raw in candidates:
            value = self.normalize_serial_number(raw)
            if value:
                return value
        return None

    def _disk_serials_from_hardware(self, hw: dict[str, Any]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for disk in hw.get("disks") or []:
            if not isinstance(disk, dict):
                continue
            serial = self.normalize_serial_number(disk.get("serial_number"))
            if not serial:
                continue
            key = serial.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(serial)
        return out

    def _disk_serials_from_meta(self, meta: dict[str, Any]) -> list[str]:
        raw = meta.get("disk_serials")
        if not isinstance(raw, list):
            # одиночное значение на всякий случай
            one = self.normalize_serial_number(meta.get("disk_serial_number"))
            return [one] if one else []
        out: list[str] = []
        seen: set[str] = set()
        for item in raw:
            serial = self.normalize_serial_number(item)
            if not serial:
                continue
            key = serial.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(serial)
        return out

    def extract_identity_signals(
        self,
        *,
        meta: Optional[dict[str, Any]] = None,
        hardware: Optional[dict[str, Any]] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Сигналы «та же железка» из inventory/meta (не PK, без merge).

        Скаляры: serial_number, smbios_uuid, bios_serial, identifying_number,
        baseboard_serial. Список: disk_serials (Win32_DiskDrive.SerialNumber).
        """
        meta = meta if isinstance(meta, dict) else {}
        hw = hardware if isinstance(hardware, dict) else None
        if hw is None and isinstance(payload, dict):
            raw_hw = payload.get("hardware")
            hw = raw_hw if isinstance(raw_hw, dict) else {}
        if hw is None:
            hw = {}
        ids = meta.get("hardware_ids") if isinstance(meta.get("hardware_ids"), dict) else {}

        serial = self._pick_serial(
            hw.get("serial_number"),
            meta.get("serial_number"),
            ids.get("serial_number"),
        )
        bios_serial = self._pick_serial(
            hw.get("bios_serial"),
            meta.get("bios_serial"),
            ids.get("bios_serial"),
        )
        identifying_number = self._pick_serial(
            hw.get("identifying_number"),
            meta.get("identifying_number"),
            ids.get("identifying_number"),
        )
        baseboard_serial = self._pick_serial(
            hw.get("baseboard_serial"),
            meta.get("baseboard_serial"),
            ids.get("baseboard_serial"),
        )

        uuid = self.normalize_smbios_uuid(hw.get("smbios_uuid"))
        if not uuid:
            uuid = self.normalize_smbios_uuid(hw.get("uuid"))
        if not uuid:
            uuid = self.normalize_smbios_uuid(meta.get("smbios_uuid"))
        if not uuid:
            uuid = self.normalize_smbios_uuid(ids.get("smbios_uuid"))

        disk_serials = self._disk_serials_from_hardware(hw)
        if not disk_serials:
            disk_serials = self._disk_serials_from_meta(meta)

        return {
            "serial_number": serial,
            "smbios_uuid": uuid,
            "bios_serial": bios_serial,
            "identifying_number": identifying_number,
            "baseboard_serial": baseboard_serial,
            "disk_serials": disk_serials,
        }

    def identity_signals_for_meta(self, signals: dict[str, Any]) -> dict[str, Any]:
        """Подмножество сигналов для записи в devices.meta_json."""
        out: dict[str, Any] = {}
        for key in self.IDENTITY_SCALAR_KEYS:
            value = signals.get(key)
            if value:
                out[key] = value
        disks = signals.get("disk_serials") or []
        if isinstance(disks, list) and disks:
            out["disk_serials"] = list(disks)
        return out

    def _identity_signals_enriched(
        self, device_id: str, meta: dict[str, Any]
    ) -> dict[str, Any]:
        """meta + при пробелах — последний inventory (для старых снимков без кэша)."""
        signals = self.extract_identity_signals(meta=meta)
        need_inv = False
        for key in self.IDENTITY_SCALAR_KEYS:
            if not signals.get(key):
                need_inv = True
                break
        if not signals.get("disk_serials"):
            need_inv = True
        if not need_inv:
            return signals
        detail = self.get_device_detail(device_id)
        if not detail:
            return signals
        payload = (detail.get("latest_inventory") or {}).get("payload")
        from_inv = self.extract_identity_signals(
            meta=detail.get("meta") or meta,
            payload=payload if isinstance(payload, dict) else None,
        )
        for key in self.IDENTITY_SCALAR_KEYS:
            if not signals.get(key):
                signals[key] = from_inv.get(key)
        if not signals.get("disk_serials"):
            signals["disk_serials"] = list(from_inv.get("disk_serials") or [])
        return signals

    def duplicate_signal_index(
        self,
        *,
        devices: Optional[list[dict[str, Any]]] = None,
        meta_only: bool = False,
    ) -> dict[str, Any]:
        """Индекс дублей: hostname + hardware ids (serial/uuid/bios/board/disk).

        Без auto-merge: только подсказки. Archived учитываются.
        ``devices`` — уже загруженные строки (без второго list_devices).
        ``meta_only`` — только meta (без get_device_detail на каждую строку).
        """
        by_host: dict[str, list[str]] = {}
        by_scalar: dict[str, dict[str, list[str]]] = {
            key: {} for key in self.IDENTITY_SCALAR_KEYS
        }
        by_disk: dict[str, list[str]] = {}
        rows: list[dict[str, Any]] = []

        device_rows = (
            devices if devices is not None else self.list_devices(archived=None)
        )
        for d in device_rows:
            device_id = d["device_id"]
            meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
            if meta_only:
                signals = self.extract_identity_signals(meta=meta)
            else:
                signals = self._identity_signals_enriched(device_id, meta)
            hostname = (d.get("hostname") or "").strip()
            host_key = hostname.casefold() if hostname else ""
            scalar_keys = {
                key: (signals.get(key) or "").casefold()
                if key != "smbios_uuid"
                else (signals.get(key) or "")
                for key in self.IDENTITY_SCALAR_KEYS
            }
            # smbios already casefolded by normalize
            disk_keys = [
                s.casefold() for s in (signals.get("disk_serials") or []) if s
            ]
            row = {
                "device_id": device_id,
                "hostname": d.get("hostname"),
                "archived": d.get("archived"),
                "signals": signals,
                "host_key": host_key,
                "scalar_keys": scalar_keys,
                "disk_keys": disk_keys,
            }
            rows.append(row)
            if host_key:
                by_host.setdefault(host_key, []).append(device_id)
            for key, value in scalar_keys.items():
                if value:
                    by_scalar[key].setdefault(value, []).append(device_id)
            for disk_key in disk_keys:
                by_disk.setdefault(disk_key, []).append(device_id)

        device_signals: dict[str, dict[str, Any]] = {}
        for row in rows:
            did = row["device_id"]
            flags: dict[str, bool] = {
                "hostname": bool(
                    row["host_key"] and len(by_host.get(row["host_key"], [])) > 1
                )
            }
            for key, value in row["scalar_keys"].items():
                flags[key] = bool(value and len(by_scalar[key].get(value, [])) > 1)
            disk_dup = any(len(by_disk.get(k, [])) > 1 for k in row["disk_keys"])
            flags["disk_serial_number"] = disk_dup

            kinds = [name for name, hit in flags.items() if hit]
            signals = row["signals"]
            device_signals[did] = {
                **flags,
                "is_duplicate": bool(kinds),
                "kinds": kinds,
                "serial_value": signals.get("serial_number"),
                "smbios_uuid_value": signals.get("smbios_uuid"),
                "bios_serial_value": signals.get("bios_serial"),
                "identifying_number_value": signals.get("identifying_number"),
                "baseboard_serial_value": signals.get("baseboard_serial"),
                "disk_serials_value": list(signals.get("disk_serials") or []),
            }

        return {
            "by_hostname": by_host,
            "by_serial": by_scalar.get("serial_number") or {},
            "by_smbios_uuid": by_scalar.get("smbios_uuid") or {},
            "by_bios_serial": by_scalar.get("bios_serial") or {},
            "by_identifying_number": by_scalar.get("identifying_number") or {},
            "by_baseboard_serial": by_scalar.get("baseboard_serial") or {},
            "by_disk_serial": by_disk,
            "device_signals": device_signals,
        }

    def find_duplicate_devices(self, device_id: str) -> dict[str, list[dict[str, Any]]]:
        """Другие устройства с совпавшим hostname / hardware id.

        Сигналы «та же железка», не PK. Автослияния нет.
        Бакеты не сужаются; на каждом кандидате ``merge_matched``
        (``merge_identity_matched``) — пусто = склейка недоступна.
        """
        empty: dict[str, list[dict[str, Any]]] = {
            "hostname": [],
            "serial_number": [],
            "smbios_uuid": [],
            "bios_serial": [],
            "identifying_number": [],
            "baseboard_serial": [],
            "disk_serial_number": [],
        }
        detail = self.get_device_detail(device_id)
        if not detail:
            return empty
        payload = (detail.get("latest_inventory") or {}).get("payload")
        signals = self.extract_identity_signals(
            meta=detail.get("meta") if isinstance(detail.get("meta"), dict) else {},
            payload=payload if isinstance(payload, dict) else None,
        )
        hostname = (detail.get("hostname") or "").strip()
        my_disks = {
            s.casefold() for s in (signals.get("disk_serials") or []) if s
        }

        buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in empty}

        for other in self.list_devices(archived=None):
            if other["device_id"] == device_id:
                continue
            other_meta = other.get("meta") if isinstance(other.get("meta"), dict) else {}
            other_signals = self.extract_identity_signals(meta=other_meta)
            # Одно правило с merge_devices: пусто = UI без кнопки склейки.
            merge_matched = self.merge_identity_matched(signals, other_signals)

            base = {
                "device_id": other["device_id"],
                "hostname": other["hostname"],
                "archived": other.get("archived"),
                "merge_matched": list(merge_matched),
            }

            other_hn = (other.get("hostname") or "").strip()
            if hostname and other_hn and hostname.casefold() == other_hn.casefold():
                buckets["hostname"].append(dict(base))

            for key in (
                "serial_number",
                "smbios_uuid",
                "bios_serial",
                "identifying_number",
                "baseboard_serial",
            ):
                mine = signals.get(key)
                theirs = other_signals.get(key)
                if not mine or not theirs:
                    continue
                if key == "smbios_uuid":
                    match = mine == theirs
                else:
                    match = str(mine).casefold() == str(theirs).casefold()
                if match:
                    row = dict(base)
                    row[key] = theirs
                    buckets[key].append(row)

            other_disks = {
                s.casefold() for s in (other_signals.get("disk_serials") or []) if s
            }
            shared = sorted(my_disks & other_disks)
            if shared:
                row = dict(base)
                row["disk_serial_number"] = shared[0]
                row["disk_serials"] = shared
                buckets["disk_serial_number"].append(row)

        return buckets

    def merge_devices(
        self,
        survivor_id: str,
        donor_id: str,
        *,
        stale_after_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Ручная склейка дублей: история donor → survivor, donor в архив+revoke.

        Identity: ``merge_identity_matched`` (сильное serial/uuid или слабая
        пара bios/identifying/board). Donor — stale или archived.
        Hostname/disk в match не входят. Без UNIQUE(serial), PK не меняется.
        Одна транзакция: archive **и** revoke api_key донора.

        Raises ValueError с кодом:
        ``merge_same_device`` · ``merge_survivor_missing`` · ``merge_donor_missing``
        · ``merge_no_identity_match`` · ``merge_donor_not_stale_or_archived``.
        """
        from .device_health import device_silence_status

        survivor_id = (survivor_id or "").strip()
        donor_id = (donor_id or "").strip()
        if not survivor_id or not donor_id:
            raise ValueError("merge_survivor_missing")
        if survivor_id == donor_id:
            raise ValueError("merge_same_device")

        survivor = self.get_device_detail(survivor_id)
        if not survivor:
            raise ValueError("merge_survivor_missing")
        donor = self.get_device_detail(donor_id)
        if not donor:
            raise ValueError("merge_donor_missing")

        s_meta = survivor.get("meta") if isinstance(survivor.get("meta"), dict) else {}
        d_meta = donor.get("meta") if isinstance(donor.get("meta"), dict) else {}
        s_sig = self._identity_signals_enriched(survivor_id, s_meta)
        d_sig = self._identity_signals_enriched(donor_id, d_meta)

        matched = self.merge_identity_matched(s_sig, d_sig)
        if not matched:
            raise ValueError("merge_no_identity_match")

        donor_archived = bool(donor.get("archived"))
        if not donor_archived:
            silence = device_silence_status(
                donor.get("last_seen_at"),
                stale_after_seconds=stale_after_seconds,
            )
            if silence.get("status") != "stale":
                raise ValueError("merge_donor_not_stale_or_archived")

        donor_hostname = donor.get("hostname")
        now = utc_now()
        detail = {
            "donor_id": donor_id,
            "hostname": donor_hostname,
            "matched": matched,
        }
        detail_json = json.dumps(detail, separators=(",", ":"), ensure_ascii=False)
        summary = (
            f"Склейка с {donor_hostname}"
            if donor_hostname
            else f"Склейка с {donor_id}"
        )

        with self.connection() as conn:
            # Повторная проверка существования внутри транзакции (TOCTOU).
            s_row = conn.execute(
                "SELECT device_id FROM devices WHERE device_id = ?",
                (survivor_id,),
            ).fetchone()
            d_row = conn.execute(
                """
                SELECT device_id, hostname, last_seen_at, archived
                FROM devices WHERE device_id = ?
                """,
                (donor_id,),
            ).fetchone()
            if not s_row:
                raise ValueError("merge_survivor_missing")
            if not d_row:
                raise ValueError("merge_donor_missing")

            snap_cur = conn.execute(
                """
                UPDATE inventory_snapshots
                SET device_id = ?
                WHERE device_id = ?
                """,
                (survivor_id, donor_id),
            )
            ev_cur = conn.execute(
                """
                UPDATE device_events
                SET device_id = ?
                WHERE device_id = ?
                """,
                (survivor_id, donor_id),
            )
            # archived ≠ block auth — revoke в той же транзакции (#96 review).
            conn.execute(
                """
                UPDATE devices
                SET archived = 1, revoked = 1, api_key_lookup = NULL
                WHERE device_id = ?
                """,
                (donor_id,),
            )
            conn.execute(
                """
                INSERT INTO device_events(
                  device_id, type, summary, detail_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    survivor_id,
                    "device_merged",
                    summary,
                    detail_json,
                    now,
                ),
            )
            snapshots_moved = int(snap_cur.rowcount or 0)
            events_moved = int(ev_cur.rowcount or 0)

        return {
            "survivor_id": survivor_id,
            "donor_id": donor_id,
            "donor_hostname": donor_hostname,
            "matched": matched,
            "snapshots_moved": snapshots_moved,
            "events_moved": events_moved,
            "donor_archived": True,
            "donor_revoked": True,
        }

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
        placeholders = ",".join("?" for _ in hw_types)
        with self.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT e.id, e.device_id, e.type, e.summary, e.detail_json,
                       e.created_at, d.hostname
                FROM device_events e
                LEFT JOIN devices d ON d.device_id = e.device_id
                WHERE e.type IN ({placeholders})
                ORDER BY e.created_at DESC, e.id DESC
                LIMIT 8
                """,
                tuple(hw_types),
            ).fetchall()
        recent_hw: list[dict[str, Any]] = []
        for row in rows:
            detail: Any = None
            if row["detail_json"]:
                try:
                    detail = json.loads(row["detail_json"])
                except json.JSONDecodeError:
                    detail = {"_raw": row["detail_json"]}
            recent_hw.append(
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



def open_database(*, database_url: Optional[str] = None) -> Database:
    """Factory: требует непустой BAD_DATABASE_URL."""
    return Database(database_url or "")
