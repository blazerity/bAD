"""Формат bad-agent-<версия>.arc: BADARC1, соль, nonce, AES-256-GCM."""

from __future__ import annotations

import io
import secrets
import sys
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"BADARC1\n"
PBKDF2_ITERS = 100_000


def new_password() -> str:
    return secrets.token_urlsafe(24)


def zip_directory(src: Path) -> bytes:
    buf = io.BytesIO()
    root = src.resolve()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if ".." in rel.split("/"):
                continue
            # В архив не кладём службу-загрузчик. BadAgent.exe остаётся.
            if path.name == "bADagent.exe":
                continue
            zf.write(path, rel)
    return buf.getvalue()


def encrypt_zip(payload: bytes, password: str) -> bytes:
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERS,
    ).derive(password.encode("utf-8"))
    sealed = AESGCM(key).encrypt(nonce, payload, None)
    return MAGIC + salt + nonce + sealed


def pack_publish(src: Path, dest: Path) -> str:
    password = new_password()
    dest.write_bytes(encrypt_zip(zip_directory(src), password))
    return password


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[1] != "pack":
        return 2
    src = Path(argv[2])
    dest = Path(argv[3])
    password_path = dest.with_suffix(dest.suffix + ".password")
    password = pack_publish(src, dest)
    password_path.write_text(password, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
