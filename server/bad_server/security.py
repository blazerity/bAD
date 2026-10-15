from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()


def generate_token(prefix: str, nbytes: int = 32) -> str:
    return f"{prefix}{secrets.token_urlsafe(nbytes)}"


def hash_secret(value: str) -> str:
    return _ph.hash(value)


def verify_secret(hashed: str, value: str) -> bool:
    try:
        return _ph.verify(hashed, value)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def api_key_lookup(pepper: str, api_key: str) -> str:
    """Keyed lookup index so API auth is O(1), not O(n) Argon2."""
    if not pepper or not api_key:
        return ""
    return hmac.new(
        pepper.encode("utf-8"),
        api_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
