"""Заявки внешних программ и ключ только на чтение карточки."""

from __future__ import annotations

import logging
import re
import secrets
from typing import Annotated, Any, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from .auth import admin_token_valid, get_db
from .config import Settings, get_settings
from .crypto_util import decrypt_secret, encrypt_secret
from .db import Database, utc_now
from .security import api_key_lookup, extract_bearer, generate_token, hash_secret, verify_secret

logger = logging.getLogger(__name__)

_ID_RE = re.compile(r"^int_[0-9a-f]{16}$")
_OPEN_LIMIT = 20
_STATUS_LABELS = {
    "pending": "Ожидает подтверждения",
    "approved": "Ключ ждёт программу",
    "active": "Подключена",
    "rejected": "Отклонена",
    "revoked": "Отозвана",
}


class IntegrationError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def is_integration_id(value: str) -> bool:
    return bool(_ID_RE.match(value or ""))


def list_integrations(db: Database) -> list[dict[str, Any]]:
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, status, created_at, approved_at, last_used_at, use_count
            FROM integrations
            ORDER BY CASE status
                WHEN 'pending' THEN 0
                WHEN 'approved' THEN 1
                WHEN 'active' THEN 2
                ELSE 3
            END, created_at DESC
            LIMIT 100
            """
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["status_label"] = _STATUS_LABELS.get(item["status"], item["status"])
        items.append(item)
    return items


def create_request(db: Database, data_key: str, name: str) -> dict[str, str]:
    cleaned = _clean_name(name)
    if not data_key:
        raise IntegrationError("no_data_key")
    with db.connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM integrations
            WHERE status IN ('pending', 'approved')
            """
        ).fetchone()
        if int(row["n"] or 0) >= _OPEN_LIMIT:
            raise IntegrationError("too_many")
        integration_id = _new_id(conn)
        poll_secret = generate_token("bad_ps_")
        now = utc_now()
        conn.execute(
            """
            INSERT INTO integrations(
              id, name, status, poll_lookup, poll_hash, token_enc, created_at, use_count
            ) VALUES (?, ?, 'pending', ?, ?, '', ?, 0)
            """,
            (
                integration_id,
                cleaned,
                api_key_lookup(data_key, poll_secret),
                hash_secret(poll_secret),
                now,
            ),
        )
    logger.info("Заявка на интеграцию %s", integration_id)
    return {
        "id": integration_id,
        "status": "pending",
        "poll_secret": poll_secret,
    }


def poll_request(
    db: Database,
    data_key: str,
    integration_id: str,
    poll_secret: str,
) -> dict[str, str]:
    row = _row_by_poll(db, data_key, integration_id, poll_secret)
    if row["status"] != "approved":
        return {"id": row["id"], "status": row["status"]}
    token = decrypt_secret(data_key, row.get("token_enc") or "")
    if not token:
        logger.error("У заявки %s нет ключа для выдачи", row["id"])
        raise IntegrationError("token_missing")
    with db.connection() as conn:
        cur = conn.execute(
            """
            UPDATE integrations
            SET status = 'active', token_enc = ''
            WHERE id = ? AND status = 'approved'
            """,
            (row["id"],),
        )
        taken = int(cur.rowcount or 0) == 1
    if not taken:
        return {"id": row["id"], "status": "active"}
    logger.info("Программа забрала ключ интеграции %s", row["id"])
    return {"id": row["id"], "status": "active", "token": token}


def approve(db: Database, data_key: str, integration_id: str) -> None:
    if not data_key:
        raise IntegrationError("no_data_key")
    token = generate_token("bad_in_")
    now = utc_now()
    with db.connection() as conn:
        cur = conn.execute(
            """
            UPDATE integrations
            SET status = 'approved',
                approved_at = ?,
                token_lookup = ?,
                token_hash = ?,
                token_enc = ?
            WHERE id = ? AND status = 'pending'
            """,
            (
                now,
                api_key_lookup(data_key, token),
                hash_secret(token),
                encrypt_secret(data_key, token),
                integration_id,
            ),
        )
        if int(cur.rowcount or 0) != 1:
            raise IntegrationError("state")
    logger.info("Заявка на интеграцию подтверждена %s", integration_id)


def reject(db: Database, integration_id: str) -> None:
    _set_status(db, integration_id, from_status="pending", to_status="rejected")
    logger.info("Заявка на интеграцию отклонена %s", integration_id)


def revoke(db: Database, integration_id: str) -> None:
    with db.connection() as conn:
        cur = conn.execute(
            """
            UPDATE integrations
            SET status = 'revoked', token_lookup = NULL, token_hash = NULL, token_enc = ''
            WHERE id = ? AND status IN ('approved', 'active')
            """,
            (integration_id,),
        )
        if int(cur.rowcount or 0) != 1:
            raise IntegrationError("state")
    logger.info("Интеграция отозвана %s", integration_id)


def record_use(db: Database, integration_id: str) -> None:
    with db.connection() as conn:
        conn.execute(
            """
            UPDATE integrations
            SET use_count = use_count + 1, last_used_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (utc_now(), integration_id),
        )


def integration_from_token(
    db: Database,
    data_key: str,
    token: str,
) -> Optional[dict[str, Any]]:
    if not token.startswith("bad_in_") or not data_key:
        return None
    lookup = api_key_lookup(data_key, token)
    with db.connection() as conn:
        row = conn.execute(
            """
            SELECT id, status, token_hash
            FROM integrations
            WHERE token_lookup = ? AND status = 'active'
            """,
            (lookup,),
        ).fetchone()
    if not row or not verify_secret(row["token_hash"] or "", token):
        return None
    return {"id": row["id"], "status": row["status"]}


def require_device_reader(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> dict[str, str]:
    """Админский токен или ключ интеграции со статусом «подключена»."""
    token = extract_bearer(authorization) or ""
    if admin_token_valid(token, settings, db):
        return {"kind": "admin"}
    data_key = getattr(request.app.state, "data_key", "") or ""
    row = integration_from_token(db, data_key, token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return {"kind": "integration", "id": row["id"]}


def _clean_name(name: str) -> str:
    cleaned = " ".join((name or "").split())
    if not cleaned or len(cleaned) > 80:
        raise IntegrationError("name")
    if any(ord(ch) < 32 for ch in cleaned):
        raise IntegrationError("name")
    return cleaned


def _new_id(conn: Any) -> str:
    for _ in range(5):
        integration_id = "int_" + secrets.token_hex(8)
        row = conn.execute(
            "SELECT 1 FROM integrations WHERE id = ?",
            (integration_id,),
        ).fetchone()
        if not row:
            return integration_id
    raise IntegrationError("id")


def _row_by_poll(
    db: Database,
    data_key: str,
    integration_id: str,
    poll_secret: str,
) -> dict[str, Any]:
    if not is_integration_id(integration_id) or not poll_secret or not data_key:
        raise IntegrationError("not_found")
    lookup = api_key_lookup(data_key, poll_secret)
    with db.connection() as conn:
        row = conn.execute(
            "SELECT * FROM integrations WHERE id = ? AND poll_lookup = ?",
            (integration_id, lookup),
        ).fetchone()
    if not row or not verify_secret(row["poll_hash"] or "", poll_secret):
        raise IntegrationError("not_found")
    return dict(row)


def _set_status(
    db: Database,
    integration_id: str,
    *,
    from_status: str,
    to_status: str,
) -> None:
    with db.connection() as conn:
        cur = conn.execute(
            """
            UPDATE integrations
            SET status = ?
            WHERE id = ? AND status = ?
            """,
            (to_status, integration_id, from_status),
        )
        if int(cur.rowcount or 0) != 1:
            raise IntegrationError("state")

