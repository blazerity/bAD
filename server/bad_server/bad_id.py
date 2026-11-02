"""Публичный bad-id: BAD- и 10 символов Crockford из секрета сервера."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Any, Optional

_BAD_ID_RE = re.compile(r"^BAD-[0-9A-HJKMNP-TV-Z]{6}(?:[0-9A-HJKMNP-TV-Z]{4})?$")
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_BAD_ID_BODY_LEN = 10
_KEY_NAME = "bad_id_hmac_key"


def is_bad_id(ref: str) -> bool:
    """Код панели: текущие 10 символов и прежние 6 (до пересчёта)."""
    return bool(_BAD_ID_RE.match((ref or "").strip()))


def bad_id_for_device(device_id: str, key: str) -> str:
    """Один и тот же device_id и секрет всегда дают один код.

    В расчёт берётся строка device_id как она хранится, без смены регистра:
    от регистра зависит первичный ключ, и общий регистр склеил бы две строки.
    """
    digest = hmac.new(
        key.encode("utf-8"),
        device_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return "BAD-" + _encode_crockford(digest, _BAD_ID_BODY_LEN)


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


def device_panel_href(bad_id: Optional[str], device_id: str) -> str:
    ref = (bad_id or "").strip() or device_id
    return f"/devices/{ref}"


def _encode_crockford(digest: bytes, length: int) -> str:
    bits = int.from_bytes(digest, "big")
    total_bits = len(digest) * 8
    chars: list[str] = []
    for i in range(length):
        shift = total_bits - (i + 1) * 5
        chars.append(_ALPHABET[(bits >> shift) & 31])
    return "".join(chars)
