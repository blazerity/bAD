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


def enrollment_code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def new_device_signing_key() -> tuple[str, str, str]:
    """Ed25519 (private_b64, public_b64, sha256 fingerprint). Private key shown once."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    raw_private = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    raw_public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (
        base64.b64encode(raw_private).decode("ascii"),
        base64.b64encode(raw_public).decode("ascii"),
        hashlib.sha256(raw_public).hexdigest(),
    )


def inventory_signing_bytes(payload: dict) -> bytes:
    body = {key: value for key, value in payload.items() if key != "signature"}
    import json

    return json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def verify_inventory_signature(
    public_b64: str, payload: dict, signature_b64: str
) -> bool:
    import base64

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        public = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64))
        public.verify(base64.b64decode(signature_b64), inventory_signing_bytes(payload))
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True


def extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None
