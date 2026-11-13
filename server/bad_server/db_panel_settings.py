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

class DbPanelSettingsMixin:

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
                ) VALUES (%s, %s, %s, %s, %s)
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
                "SELECT * FROM local_users WHERE LOWER(username) = LOWER(%s)",
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
                    SET password_hash = %s, must_change_password = 0
                    WHERE LOWER(username) = LOWER(%s)
                    """,
                    (password_hash, username),
                )
            else:
                conn.execute(
                    """
                    UPDATE local_users
                    SET password_hash = %s
                    WHERE LOWER(username) = LOWER(%s)
                    """,
                    (password_hash, username),
                )


    def touch_local_user_login(self, username: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE local_users SET last_login_at = %s
                WHERE LOWER(username) = LOWER(%s)
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
        sets = [
            "enabled = %s",
            "host = %s",
            "port = %s",
            "use_ssl = %s",
            "start_tls = %s",
            "bind_dn = %s",
        ]
        params: list[Any] = [
            1 if enabled else 0,
            host,
            port,
            1 if use_ssl else 0,
            1 if start_tls else 0,
            bind_dn,
        ]
        if bind_password_enc is not None:
            sets.append("bind_password_enc = %s")
            params.append(bind_password_enc)
        sets.extend(
            [
                "user_search_base = %s",
                "user_filter_template = %s",
                "display_name_attr = %s",
                "default_role = %s",
                "allowed_group = %s",
                "tls_insecure = %s",
                "updated_at = %s",
            ]
        )
        params.extend(
            [
                user_search_base,
                user_filter_template,
                display_name_attr,
                default_role,
                allowed_group,
                1 if tls_insecure else 0,
                now,
            ]
        )
        with self.connection() as conn:
            conn.execute(
                f"UPDATE ldap_settings SET {', '.join(sets)} WHERE id = 1",
                params,
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
            "archive_password_enc": row["archive_password_enc"]
            if "archive_password_enc" in row.keys()
            else "",
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
                "release_url, synced_at, archive_password_enc FROM agent_update WHERE id = 1"
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
                "source_tag, release_url, mirrored_at, archive_password_enc "
                "FROM agent_msi_versions WHERE version = %s",
                (ver,),
            ).fetchone()
        return self._msi_row(row) if row else None


    def list_agent_msi_versions(self) -> list[dict[str, Any]]:
        """Все зеркалированные MSI, newest semver first (несортируемые — в конце)."""
        from .agent_update import parse_semver

        with self.connection() as conn:
            rows = conn.execute(
                "SELECT version, msi_name, sha256, file_path, source, "
                "source_tag, release_url, mirrored_at, archive_password_enc "
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
        archive_password_enc: str = "",
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
                  source_tag, release_url, mirrored_at, archive_password_enc
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(version) DO UPDATE SET
                  msi_name = excluded.msi_name,
                  sha256 = excluded.sha256,
                  file_path = excluded.file_path,
                  source = excluded.source,
                  source_tag = excluded.source_tag,
                  release_url = excluded.release_url,
                  mirrored_at = excluded.mirrored_at,
                  archive_password_enc = excluded.archive_password_enc
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
                    archive_password_enc or "",
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
                          source_tag, release_url, synced_at, archive_password_enc
                        ) VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(id) DO UPDATE SET
                          version = excluded.version,
                          msi_name = excluded.msi_name,
                          sha256 = excluded.sha256,
                          file_path = excluded.file_path,
                          source_tag = excluded.source_tag,
                          release_url = excluded.release_url,
                          synced_at = excluded.synced_at,
                          archive_password_enc = excluded.archive_password_enc
                        """,
                        (
                            version,
                            msi_name,
                            sha256,
                            file_path,
                            source_tag,
                            release_url,
                            now,
                            archive_password_enc or "",
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO site_secrets(key, value) VALUES (%s, %s)
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
        archive_password_enc: str = "",
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
            archive_password_enc=archive_password_enc,
        )


    def delete_agent_msi_version(self, version: str) -> bool:
        """Удалить запись каталога (файл на диске — отдельно). Обновить latest при необходимости."""
        ver = (version or "").strip()
        if not ver:
            return False
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM agent_msi_versions WHERE version = %s", (ver,)
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
                archive_password_enc=top.get("archive_password_enc") or "",
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
                "SELECT * FROM agent_policies WHERE id = %s", (policy_id,)
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name,
                    1 if enabled else 0,
                    priority,
                    _compact_json(conditions),
                    _compact_json(settings),
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
                  name = %s, enabled = %s, priority = %s,
                  conditions_json = %s, settings_json = %s, updated_at = %s
                WHERE id = %s
                """,
                (
                    name,
                    1 if enabled else 0,
                    priority,
                    _compact_json(conditions),
                    _compact_json(settings),
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
                "DELETE FROM agent_policies WHERE id = %s", (policy_id,)
            )
            return cur.rowcount > 0


    def list_device_config_overrides_map(self) -> dict[str, dict[str, Any]]:
        """bad_id → settings dict (для batch drift без N запросов)."""
        out: dict[str, dict[str, Any]] = {}
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT bad_id, settings_json FROM device_config_overrides"
            ).fetchall()
        for row in rows:
            try:
                settings = json.loads(row["settings_json"] or "{}")
            except json.JSONDecodeError:
                settings = {}
            if isinstance(settings, dict):
                out[str(row["bad_id"])] = settings
        return out


    def get_device_config_override(self, bad_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT bad_id, settings_json, updated_at
                FROM device_config_overrides WHERE bad_id = %s
                """,
                (bad_id,),
            ).fetchone()
        if not row:
            return None
        try:
            settings = json.loads(row["settings_json"] or "{}")
        except json.JSONDecodeError:
            settings = {}
        return {
            "bad_id": row["bad_id"],
            "settings": settings if isinstance(settings, dict) else {},
            "updated_at": row["updated_at"],
        }


    def set_device_config_override(
        self, bad_id: str, settings: dict[str, Any]
    ) -> dict[str, Any]:
        now = utc_now()
        payload = _compact_json(settings)
        with self.connection() as conn:
            exists = conn.execute(
                "SELECT bad_id FROM devices WHERE bad_id = %s", (bad_id,)
            ).fetchone()
            if not exists:
                raise KeyError(bad_id)
            conn.execute(
                """
                INSERT INTO device_config_overrides(bad_id, settings_json, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT(bad_id) DO UPDATE SET
                  settings_json = excluded.settings_json,
                  updated_at = excluded.updated_at
                """,
                (bad_id, payload, now),
            )
        override = self.get_device_config_override(bad_id)
        assert override is not None
        return override


    def delete_device_config_override(self, bad_id: str) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                "DELETE FROM device_config_overrides WHERE bad_id = %s",
                (bad_id,),
            )
            return cur.rowcount > 0


    def compute_device_effective_config(
        self, bad_id: str, *, use_inventory: bool = True
    ) -> Optional[dict[str, Any]]:
        from .agent_config import compute_effective_config, provenance_from_effective

        with self.connection() as conn:
            device = conn.execute(
                "SELECT * FROM devices WHERE bad_id = %s", (bad_id,)
            ).fetchone()
        if not device:
            return None
        override_row = self.get_device_config_override(bad_id)
        override = override_row["settings"] if override_row else None
        tags = self._parse_tags(device["tags_json"])
        meta = self._parse_meta(device["meta_json"])
        inventory = (
            self.latest_inventory_payload(bad_id) if use_inventory else None
        )
        result = compute_effective_config(
            hostname=device["hostname"],
            meta=meta,
            inventory_payload=inventory,
            tags=tags,
            policies=self.list_agent_policies(),
            override=override,
        )
        result["bad_id"] = bad_id
        result["override"] = override_row
        result.update(provenance_from_effective(result, meta=meta))
        return result


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
                  events_days = %s, inventory_days = %s, updated_at = %s
                WHERE id = 1
                """,
                (int(events_days), int(inventory_days), now),
            )


    def prune_expired_data(
        self, *, events_days: int, inventory_days: int
    ) -> dict[str, int]:
        """Удалить events/snapshots старше N дней. Оставить новейший snapshot на устройство."""
        events_cut = _utc_cutoff(timedelta(days=max(1, int(events_days))))
        inv_cut = _utc_cutoff(timedelta(days=max(1, int(inventory_days))))
        with self.connection() as conn:
            ev = conn.execute(
                "DELETE FROM device_events WHERE created_at < %s", (events_cut,)
            )
            # Оставить последний snapshot на каждое устройство, даже если он старый.
            keep_rows = conn.execute(
                """
                SELECT s.id FROM inventory_snapshots s
                WHERE s.id = (
                  SELECT s2.id FROM inventory_snapshots s2
                  WHERE s2.bad_id = s.bad_id
                  ORDER BY s2.received_at DESC, s2.id DESC
                  LIMIT 1
                )
                """
            ).fetchall()
            keep_ids = {int(r["id"]) for r in keep_rows}
            old_rows = conn.execute(
                """
                SELECT id FROM inventory_snapshots
                WHERE received_at < %s
                """,
                (inv_cut,),
            ).fetchall()
            delete_ids = [
                int(r["id"]) for r in old_rows if int(r["id"]) not in keep_ids
            ]
            for sid in delete_ids:
                conn.execute("DELETE FROM inventory_snapshots WHERE id = %s", (sid,))
            return {
                "events_deleted": int(ev.rowcount or 0),
                "snapshots_deleted": len(delete_ids),
            }


    # --- SMTP settings ---

    @staticmethod
    def _clamp_digest_interval_hours(raw: Any) -> int:
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = 3
        return max(1, min(val, 24))


    @staticmethod
    def _clamp_digest_lookback_hours(raw: Any) -> int:
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = 3
        return max(1, min(val, 168))


    @staticmethod
    def _clamp_digest_window_hour(raw: Any, *, default: int, hi: int) -> int:
        try:
            val = int(raw)
        except (TypeError, ValueError):
            val = default
        return max(0, min(val, hi))


    @staticmethod
    def _normalize_digest_weekdays(raw: Any) -> list[int]:
        from .smtp_mail import parse_digest_weekdays

        return parse_digest_weekdays(raw)


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
                "digest_interval_hours": 3,
                "digest_lookback_hours": 3,
                "digest_window_start_hour": 9,
                "digest_window_end_hour": 19,
                "digest_weekdays": "[0,1,2,3,4,5]",
                "updated_at": None,
            }
        data = dict(row)
        data["digest_interval_hours"] = self._clamp_digest_interval_hours(
            data.get("digest_interval_hours")
        )
        data["digest_lookback_hours"] = self._clamp_digest_lookback_hours(
            data.get("digest_lookback_hours")
        )
        data["digest_window_start_hour"] = self._clamp_digest_window_hour(
            data.get("digest_window_start_hour"), default=9, hi=23
        )
        data["digest_window_end_hour"] = self._clamp_digest_window_hour(
            data.get("digest_window_end_hour"), default=19, hi=24
        )
        data["digest_weekdays_list"] = self._normalize_digest_weekdays(
            data.get("digest_weekdays")
        )
        data["digest_weekdays"] = json.dumps(
            data["digest_weekdays_list"], separators=(",", ":")
        )
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
        digest_interval_hours: int = 3,
        digest_lookback_hours: int = 3,
        digest_window_start_hour: int = 9,
        digest_window_end_hour: int = 19,
        digest_weekdays: Optional[str] = None,
        notify_json: Optional[str] = None,
        password_enc: Optional[str] = None,
    ) -> None:
        now = utc_now()
        digest_h = self._clamp_digest_interval_hours(digest_interval_hours)
        lookback_h = self._clamp_digest_lookback_hours(digest_lookback_hours)
        start_h = self._clamp_digest_window_hour(
            digest_window_start_hour, default=9, hi=23
        )
        end_h = self._clamp_digest_window_hour(
            digest_window_end_hour, default=19, hi=24
        )
        if end_h <= start_h:
            end_h = min(24, start_h + 1)
        wd_json = digest_weekdays
        if wd_json is not None:
            wd_list = self._normalize_digest_weekdays(wd_json)
            wd_json = json.dumps(wd_list, separators=(",", ":"))
        sets = [
            "enabled = %s",
            "host = %s",
            "port = %s",
            "use_ssl = %s",
            "use_starttls = %s",
            "username = %s",
        ]
        params: list[Any] = [
            1 if enabled else 0,
            host,
            port,
            1 if use_ssl else 0,
            1 if use_starttls else 0,
            username,
        ]
        if password_enc is not None:
            sets.append("password_enc = %s")
            params.append(password_enc)
        sets.extend(["from_addr = %s", "to_addrs = %s"])
        params.extend([from_addr, to_addrs])
        if notify_json is not None:
            sets.append("notify_json = %s")
            params.append(notify_json)
        sets.extend(
            [
                "digest_interval_hours = %s",
                "digest_lookback_hours = %s",
                "digest_window_start_hour = %s",
                "digest_window_end_hour = %s",
                "updated_at = %s",
            ]
        )
        params.extend([digest_h, lookback_h, start_h, end_h, now])
        if wd_json is not None:
            sets.insert(-1, "digest_weekdays = %s")
            params.insert(-1, wd_json)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE smtp_settings SET {', '.join(sets)} WHERE id = 1",
                params,
            )


    def _active_silence(
        self, stale_after_seconds: int
    ) -> list[tuple[dict[str, Any], dict[str, str], dict[str, Any]]]:
        from .device_health import device_silence_status

        rows: list[tuple[dict[str, Any], dict[str, str], dict[str, Any]]] = []
        for device in self.list_devices(archived=False):
            silence = device_silence_status(
                device.get("last_seen_at"), stale_after_seconds=stale_after_seconds
            )
            meta = device.get("meta") or {}
            rows.append((device, silence, meta))
        return rows


    def devices_needing_stale_alert(
        self, *, stale_after_seconds: int
    ) -> list[dict[str, Any]]:
        return [
            device
            for device, silence, meta in self._active_silence(stale_after_seconds)
            if silence["status"] == "stale" and not meta.get("stale_notified_at")
        ]


    def devices_recovered_from_stale(
        self, *, stale_after_seconds: int
    ) -> list[dict[str, Any]]:
        """Было stale_notified_at, снова heartbeat — для device_back_online."""
        return [
            device
            for device, silence, meta in self._active_silence(stale_after_seconds)
            if silence["status"] != "stale" and meta.get("stale_notified_at")
        ]
