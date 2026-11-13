"""Номер машины: BAD- и 8 hex. HMAC прежний, сообщение — MachineGuid и UUID."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Any, Optional

_BAD_ID_RE = re.compile(r"^BAD-[0-9A-F]{8}$")
_KEY_NAME = "bad_id_hmac_key"


def is_bad_id(ref: str) -> bool:
    return _BAD_ID_RE.match((ref or "").strip()) is not None


def normalize_machine_guid(raw: Optional[str]) -> str:
    """Пробелы, одна пара фигурных скобок, нижний регистр. Дефисы остаются."""
    text = (raw or "").strip()
    if len(text) >= 2 and text.startswith("{") and text.endswith("}"):
        text = text[1:-1].strip()
    return text.lower()


def bad_id_from_board(machine_guid: str, smbios_uuid: str, key: str) -> str:
    """HMAC-SHA256, UTF-8. Первые 4 байта дайджеста — восемь верхних hex."""
    message = f"{machine_guid}\n{smbios_uuid}"
    digest = hmac.new(
        key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return "BAD-" + digest[:4].hex().upper()


def random_bad_id() -> str:
    return "BAD-" + secrets.token_hex(4).upper()


def ensure_bad_id_key(db: Any) -> str:
    """Секрет формулы. Уже записанный ключ не заменяется."""
    existing = db.get_site_secret(_KEY_NAME)
    if existing:
        return str(existing)
    fresh = secrets.token_hex(32)
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO site_secrets(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO NOTHING",
            (_KEY_NAME, fresh),
        )
    stored = db.get_site_secret(_KEY_NAME)
    if not stored:
        raise RuntimeError("bad_id key was not stored")
    return str(stored)
