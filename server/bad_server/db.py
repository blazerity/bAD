from __future__ import annotations

import json
import logging
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Optional

from .bad_id import is_bad_id
from .db_backend import (
    SCHEMA_SQL,
    CompatConnection,
    connect_postgres,
)
from .postgres_ddl import ensure_trgm_search_indexes, set_lock_timeout

logger = logging.getLogger(__name__)

# Очередь «Ожидает разрешения»: старые pending снимаются, сверх потолка новая не пишется.
PENDING_ENROLLMENT_CAP = 200
PENDING_ENROLLMENT_TTL = timedelta(days=7)


def utc_now() -> str:
    return _utc_iso(datetime.now(timezone.utc))


def _utc_cutoff(age: timedelta) -> str:
    return _utc_iso(datetime.now(timezone.utc) - age)


def _utc_iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


from .db_devices import DbDevicesMixin
from .db_events import DbEventsMixin
from .db_identity import DbIdentityMixin
from .db_ingest import DbIngestMixin
from .db_panel_settings import DbPanelSettingsMixin

class Database(DbIngestMixin, DbDevicesMixin, DbEventsMixin, DbIdentityMixin, DbPanelSettingsMixin):

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
            conn.execute(
                "ALTER TABLE device_events ADD COLUMN IF NOT EXISTS mailed_at TEXT"
            )
            conn.execute(
                "ALTER TABLE devices ADD COLUMN IF NOT EXISTS signing_pubkey TEXT"
            )
            conn.execute(
                "ALTER TABLE devices ADD COLUMN IF NOT EXISTS signing_key_fingerprint TEXT"
            )
            conn.execute(
                "ALTER TABLE devices ADD COLUMN IF NOT EXISTS shared_exchange_at TEXT"
            )
            conn.execute(
                """
                ALTER TABLE smtp_settings
                ADD COLUMN IF NOT EXISTS digest_interval_hours INTEGER NOT NULL DEFAULT 3
                """
            )
            conn.execute(
                """
                ALTER TABLE smtp_settings
                ADD COLUMN IF NOT EXISTS digest_lookback_hours INTEGER NOT NULL DEFAULT 3
                """
            )
            conn.execute(
                """
                ALTER TABLE smtp_settings
                ADD COLUMN IF NOT EXISTS digest_window_start_hour INTEGER NOT NULL DEFAULT 9
                """
            )
            conn.execute(
                """
                ALTER TABLE smtp_settings
                ADD COLUMN IF NOT EXISTS digest_window_end_hour INTEGER NOT NULL DEFAULT 19
                """
            )
            conn.execute(
                """
                ALTER TABLE smtp_settings
                ADD COLUMN IF NOT EXISTS digest_weekdays TEXT NOT NULL DEFAULT '[0,1,2,3,4,5]'
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS archive_password_enc TEXT
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS seen_at TEXT
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS link_at TEXT
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS archive_total INTEGER
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS archive_received INTEGER
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS link_state TEXT
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS link_error TEXT
                """
            )
            conn.execute(
                """
                ALTER TABLE enrollment_requests
                ADD COLUMN IF NOT EXISTS proof_sha256 TEXT
                """
            )
            legacy = conn.execute(
                """
                SELECT id FROM enrollment_requests
                WHERE (proof_sha256 IS NULL OR proof_sha256 = '')
                  AND id ~ '^[0-9a-fA-F]{64}$'
                """
            ).fetchall()
            for old in legacy:
                old_id = str(old["id"])
                conn.execute(
                    """
                    UPDATE enrollment_requests
                    SET proof_sha256 = %s, id = %s
                    WHERE id = %s
                      AND (proof_sha256 IS NULL OR proof_sha256 = '')
                    """,
                    (old_id.lower(), "enr_" + secrets.token_hex(16), old_id),
                )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_enrollment_requests_proof
                ON enrollment_requests(proof_sha256)
                """
            )
            conn.execute(
                """
                ALTER TABLE agent_msi_versions
                ADD COLUMN IF NOT EXISTS archive_password_enc TEXT NOT NULL DEFAULT ''
                """
            )
            conn.execute(
                """
                ALTER TABLE agent_update
                ADD COLUMN IF NOT EXISTS archive_password_enc TEXT NOT NULL DEFAULT ''
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_device_events_unmailed
                ON device_events(mailed_at) WHERE mailed_at IS NULL
                """
            )
            boot = conn.execute(
                "SELECT value FROM site_secrets WHERE key = %s",
                ("mail_digest_schema_v1",),
            ).fetchone()
            if not boot:
                conn.execute(
                    """
                    UPDATE device_events
                    SET mailed_at = created_at
                    WHERE mailed_at IS NULL
                    """
                )
                conn.execute(
                    "INSERT INTO site_secrets(key, value) VALUES(%s, %s) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    ("mail_digest_schema_v1", "1"),
                )
            for table in ("ldap_settings", "retention_settings", "smtp_settings"):
                conn.execute(
                    f"INSERT INTO {table}(id) VALUES (1) ON CONFLICT DO NOTHING"
                )
            try:
                set_lock_timeout(conn)
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_devices_last_seen
                    ON devices (last_seen_at DESC NULLS LAST)
                    """
                )
            except Exception as exc:
                logger.warning(
                    "idx_devices_last_seen skipped on start (retry later): %s", exc
                )
        ensure_trgm_search_indexes(self.database_url)
        from .bad_id import ensure_bad_id_key

        ensure_bad_id_key(self)


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


    def get_bool_setting(self, key: str, default: bool) -> bool:
        raw = self.get_site_secret(key)
        if raw is None or str(raw).strip() == "":
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}


    def get_site_secret(self, key: str) -> Optional[str]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM site_secrets WHERE key = %s", (key,)
            ).fetchone()
            return row["value"] if row else None


    def set_site_secret(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO site_secrets(key, value) VALUES(%s, %s) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )


    def delete_site_secret(self, key: str) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM site_secrets WHERE key = %s", (key,))


    def enrollment_grant_usable(self, code_hash: str, bad_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT bad_id, used_at FROM enrollment_grants
                WHERE code_hash = %s
                """,
                (code_hash,),
            ).fetchone()
        if not row or row["used_at"]:
            return False
        bound = row["bad_id"] or ""
        return bound == bad_id or bound == ""


    def create_enrollment_grant(self, bad_id: str, code_hash: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO enrollment_grants(code_hash, bad_id, created_at)
                VALUES (%s, %s, %s)
                """,
                (code_hash, bad_id, utc_now()),
            )


    def take_enrollment_secrets(self, proof_sha256: str) -> Optional[dict[str, Any]]:
        """Отдать шифротекст одобренной заявки. Обнуление делает clear_enrollment_secrets."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT bad_id, status, api_key_enc, signing_key_enc, archive_password_enc
                FROM enrollment_requests WHERE proof_sha256 = %s
                FOR UPDATE
                """,
                (proof_sha256,),
            ).fetchone()
        if not row:
            return None
        if row["status"] != "approved" or not row["api_key_enc"]:
            return {"status": row["status"], "bad_id": row["bad_id"]}
        return {
            "status": "approved",
            "bad_id": row["bad_id"],
            "api_key_enc": row["api_key_enc"],
            "signing_key_enc": row["signing_key_enc"],
            "archive_password_enc": row["archive_password_enc"],
        }


    def clear_enrollment_secrets(self, bad_id: str) -> None:
        """Стереть шифротекст, когда клиент уже пришёл со своим ключом."""
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE enrollment_requests
                SET api_key_enc = NULL, signing_key_enc = NULL,
                    archive_password_enc = NULL, claimed_at = %s
                WHERE bad_id = %s AND status = 'approved'
                  AND api_key_enc IS NOT NULL AND btrim(api_key_enc) <> ''
                """,
                (utc_now(), bad_id),
            )


    def last_nonempty_smbios_uuid(self, bad_id: str) -> Optional[str]:
        """Первый непустой hardware.smbios_uuid среди снимков карточки, с нового."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM inventory_snapshots
                WHERE bad_id = %s
                ORDER BY received_at DESC, id DESC
                """,
                (bad_id,),
            ).fetchall()
        for row in rows:
            payload = self._snapshot_payload(row["payload_json"])
            if not isinstance(payload, dict):
                continue
            hardware = payload.get("hardware")
            if not isinstance(hardware, dict):
                continue
            found = self.normalize_smbios_uuid(hardware.get("smbios_uuid"))
            if found:
                return found
        return None


    def reissue_existing_device_for_request(
        self,
        bad_id: str,
        api_key_hash: str,
        api_key_lookup: Optional[str],
        signing_pubkey: str,
        signing_key_fingerprint: str,
        request_id: str,
        api_key_enc: str,
        signing_key_enc: str,
        archive_password_enc: str,
    ) -> bool:
        """Новый ключ уже лежащей карточки и шифротекст заявки одним commit."""
        with self.connection() as conn:
            existing = conn.execute(
                """
                SELECT bad_id, revoked FROM devices WHERE bad_id = %s
                FOR UPDATE
                """,
                (bad_id,),
            ).fetchone()
            if not existing or existing["revoked"]:
                return False
            conn.execute(
                """
                UPDATE devices
                SET api_key_hash = %s, api_key_lookup = %s,
                    signing_pubkey = %s, signing_key_fingerprint = %s
                WHERE bad_id = %s AND COALESCE(revoked, 0) = 0
                """,
                (
                    api_key_hash,
                    api_key_lookup,
                    signing_pubkey,
                    signing_key_fingerprint,
                    bad_id,
                ),
            )
            updated = conn.execute(
                """
                UPDATE enrollment_requests
                SET status = 'approved', bad_id = %s,
                    api_key_enc = %s, signing_key_enc = %s,
                    archive_password_enc = %s
                WHERE id = %s AND status = 'pending'
                """,
                (
                    bad_id,
                    api_key_enc,
                    signing_key_enc,
                    archive_password_enc or "",
                    request_id,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("request_not_pending")
        return True


    def get_device_auth_row(self, bad_id: str) -> Optional[dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT bad_id, api_key_hash, revoked, shared_exchange_at "
                "FROM devices WHERE bad_id = %s",
                (bad_id,),
            ).fetchone()
        return dict(row) if row else None


    def claim_device_signing_key(
        self, bad_id: str, pubkey: str, fingerprint: str
    ) -> bool:
        """Записать первую пару. Уже лежащий открытый ключ не меняется."""
        with self.connection() as conn:
            updated = conn.execute(
                """
                UPDATE devices
                SET signing_pubkey = %s, signing_key_fingerprint = %s
                WHERE bad_id = %s
                  AND (signing_pubkey IS NULL OR signing_pubkey = '')
                """,
                (pubkey, fingerprint, bad_id),
            )
        return updated.rowcount == 1


    def replace_device_signing_key(
        self, bad_id: str, pubkey: str, fingerprint: str
    ) -> bool:
        """Заменить открытый ключ карточки. Вызывает только кнопка панели."""
        with self.connection() as conn:
            updated = conn.execute(
                """
                UPDATE devices
                SET signing_pubkey = %s, signing_key_fingerprint = %s
                WHERE bad_id = %s
                """,
                (pubkey, fingerprint, bad_id),
            )
        return updated.rowcount == 1


    def upsert_device_on_enroll(
        self,
        bad_id: str,
        hostname: Optional[str],
        api_key_hash: str,
        agent_version: Optional[str],
        *,
        api_key_lookup: Optional[str] = None,
        allow_existing: bool = False,
        grant_code_hash: Optional[str] = None,
        signing_pubkey: Optional[str] = None,
        signing_key_fingerprint: Optional[str] = None,
    ) -> bool:
        """Создать устройство или (при allow_existing) обновить ключ.

        True — создана новая строка. Без allow_existing повторный enroll
        существующего bad_id не делается (SEC-001).
        """
        now = utc_now()
        with self.connection() as conn:
            if grant_code_hash:
                spent = conn.execute(
                    """
                UPDATE enrollment_grants
                SET used_at = %s,
                    bad_id = CASE WHEN bad_id = '' THEN %s ELSE bad_id END
                WHERE code_hash = %s AND used_at IS NULL
                  AND (bad_id = %s OR bad_id = '')
                """,
                (now, bad_id, grant_code_hash, bad_id),
            )
                if spent.rowcount != 1:
                    raise ValueError("grant_invalid")
            existing = conn.execute(
                """
                SELECT bad_id, revoked FROM devices WHERE bad_id = %s
                FOR UPDATE
                """,
                (bad_id,),
            ).fetchone()
            if existing:
                if not allow_existing:
                    raise ValueError("device_already_enrolled")
                if existing["revoked"]:
                    raise ValueError("device_revoked")
                if signing_pubkey and signing_key_fingerprint:
                    conn.execute(
                        """
                        UPDATE devices
                        SET hostname = COALESCE(%s, hostname),
                            api_key_hash = %s,
                            api_key_lookup = %s,
                            last_seen_at = %s,
                            agent_version = COALESCE(%s, agent_version),
                            signing_pubkey = %s,
                            signing_key_fingerprint = %s
                        WHERE bad_id = %s
                        """,
                        (
                            hostname,
                            api_key_hash,
                            api_key_lookup,
                            now,
                            agent_version,
                            signing_pubkey,
                            signing_key_fingerprint,
                            bad_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE devices
                        SET hostname = COALESCE(%s, hostname),
                            api_key_hash = %s,
                            api_key_lookup = %s,
                            last_seen_at = %s,
                            agent_version = COALESCE(%s, agent_version)
                        WHERE bad_id = %s
                        """,
                        (
                            hostname,
                            api_key_hash,
                            api_key_lookup,
                            now,
                            agent_version,
                            bad_id,
                        ),
                    )
                return False
            conn.execute(
                """
                INSERT INTO devices(
                  bad_id, hostname, api_key_hash, api_key_lookup,
                  enrolled_at, last_seen_at, agent_version, meta_json,
                  revoked, archived, signing_pubkey, signing_key_fingerprint
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0, %s, %s)
                """,
                (
                    bad_id,
                    hostname,
                    api_key_hash,
                    api_key_lookup,
                    now,
                    now,
                    agent_version,
                    None,
                    signing_pubkey,
                    signing_key_fingerprint,
                ),
            )
            return True


    def insert_device_and_approve_request(
        self,
        bad_id: str,
        hostname: Optional[str],
        api_key_hash: str,
        api_key_lookup: Optional[str],
        signing_pubkey: str,
        signing_key_fingerprint: str,
        request_id: str,
        api_key_enc: str,
        signing_key_enc: str,
        archive_password_enc: str,
    ) -> bool:
        """Новая карточка и шифротекст заявки одним commit. False — строка уже есть."""
        now = utc_now()
        with self.connection() as conn:
            existing = conn.execute(
                """
                SELECT bad_id FROM devices WHERE bad_id = %s
                FOR UPDATE
                """,
                (bad_id,),
            ).fetchone()
            if existing:
                return False
            inserted = conn.execute(
                """
                INSERT INTO devices(
                  bad_id, hostname, api_key_hash, api_key_lookup,
                  enrolled_at, last_seen_at, agent_version, meta_json,
                  revoked, archived, signing_pubkey, signing_key_fingerprint
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0, %s, %s)
                ON CONFLICT (bad_id) DO NOTHING
                """,
                (
                    bad_id,
                    hostname,
                    api_key_hash,
                    api_key_lookup,
                    now,
                    now,
                    None,
                    None,
                    signing_pubkey,
                    signing_key_fingerprint,
                ),
            )
            if inserted.rowcount != 1:
                return False
            updated = conn.execute(
                """
                UPDATE enrollment_requests
                SET status = 'approved', bad_id = %s,
                    api_key_enc = %s, signing_key_enc = %s,
                    archive_password_enc = %s
                WHERE id = %s AND status = 'pending'
                """,
                (
                    bad_id,
                    api_key_enc,
                    signing_key_enc,
                    archive_password_enc or "",
                    request_id,
                ),
            )
            if updated.rowcount != 1:
                raise ValueError("request_not_pending")
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
                    "SELECT * FROM devices WHERE api_key_lookup = %s",
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
                            "UPDATE devices SET api_key_lookup = %s WHERE bad_id = %s",
                            (lookup_hash, candidate["bad_id"]),
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


    def _lock_device_meta(self, conn: CompatConnection, bad_id: str) -> dict[str, Any]:
        row = conn.execute(
            "SELECT meta_json FROM devices WHERE bad_id = %s FOR UPDATE",
            (bad_id,),
        ).fetchone()
        if not row:
            raise KeyError(bad_id)
        return self._parse_meta(row["meta_json"])


    def _save_device_meta(
        self, conn: CompatConnection, bad_id: str, meta: dict[str, Any]
    ) -> None:
        conn.execute(
            "UPDATE devices SET meta_json = %s WHERE bad_id = %s",
            (
                _compact_json(meta),
                bad_id,
            ),
        )


    @staticmethod
    def _device_row_dict(row: Any) -> dict[str, Any]:
        return {
            "bad_id": row["bad_id"],
            "hostname": row["hostname"],
            "enrolled_at": row["enrolled_at"],
            "last_seen_at": row["last_seen_at"],
            "agent_version": row["agent_version"],
            "meta": Database._parse_meta(row["meta_json"]),
            "tags": Database._parse_tags(row["tags_json"]),
            "revoked": bool(row["revoked"]),
            "archived": bool(row["archived"]),
            "shared_exchange_at": str(
                (row["shared_exchange_at"] if "shared_exchange_at" in row else "") or ""
            ).strip(),
        }


    def rotate_device_api_key(
        self,
        bad_id: str,
        api_key_hash: str,
        *,
        api_key_lookup: Optional[str] = None,
    ) -> bool:
        with self.connection() as conn:
            cur = conn.execute(
                """
                UPDATE devices
                SET api_key_hash = %s, api_key_lookup = %s, revoked = 0
                WHERE bad_id = %s
                """,
                (api_key_hash, api_key_lookup, bad_id),
            )
            return cur.rowcount > 0

def open_database(*, database_url: Optional[str] = None) -> Database:
    """Factory: требует непустой BAD_DATABASE_URL."""
    return Database(database_url or "")
