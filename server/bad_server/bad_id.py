"""Публичный bad-id (BAD-XXXXXX, Crockford base32)."""

from __future__ import annotations

import re
import secrets
from typing import Optional

_BAD_ID_RE = re.compile(r"^BAD-[0-9A-HJKMNP-TV-Z]{6}$")
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def is_bad_id(ref: str) -> bool:
    return bool(_BAD_ID_RE.match((ref or "").strip()))


def generate_bad_id() -> str:
    body = "".join(secrets.choice(_ALPHABET) for _ in range(6))
    return f"BAD-{body}"


def device_panel_href(bad_id: Optional[str], device_id: str) -> str:
    ref = (bad_id or "").strip() or device_id
    return f"/devices/{ref}"
