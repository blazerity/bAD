from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def generate_data_key() -> str:
    """Вернуть url-safe ключ Fernet (base64)."""
    return Fernet.generate_key().decode("ascii")


def _fernet_from_key(raw_key: str) -> Fernet:
    # Принять ключ Fernet или вывести из произвольной секретной строки.
    try:
        return Fernet(raw_key.encode("ascii") if isinstance(raw_key, str) else raw_key)
    except Exception:
        digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(data_key: str, plaintext: str) -> str:
    return _fernet_from_key(data_key).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(data_key: str, ciphertext: str) -> Optional[str]:
    if not ciphertext:
        return None
    try:
        return _fernet_from_key(data_key).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, Exception):
        return None


def generate_session_secret() -> str:
    return secrets.token_urlsafe(48)
