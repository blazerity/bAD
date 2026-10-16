"""Загрузка TLS cert/key из UI: валидация PEM, staging, запрос apply nginx."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .db import utc_now

logger = logging.getLogger(__name__)

DEFAULT_TLS_DIR = Path("/etc/bad/tls")
CERT_NAME = "fullchain.pem"
KEY_NAME = "privkey.pem"
STAGING_DIRNAME = "staging"
APPLY_REQUEST = "apply.request"
APPLY_STATUS = "apply.status"
MAX_UPLOAD_BYTES = 1_000_000

_PEM_CERT_RE = re.compile(
    rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
    re.DOTALL,
)
_PEM_KEY_RE = re.compile(
    rb"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----.*?"
    rb"-----END (?:RSA |EC )?PRIVATE KEY-----",
    re.DOTALL,
)


def tls_dir(settings_tls_dir: Optional[Path] = None) -> Path:
    return Path(settings_tls_dir) if settings_tls_dir else DEFAULT_TLS_DIR


def staging_dir(directory: Optional[Path] = None) -> Path:
    return tls_dir(directory) / STAGING_DIRNAME


def cert_path(directory: Optional[Path] = None) -> Path:
    return tls_dir(directory) / CERT_NAME


def key_path(directory: Optional[Path] = None) -> Path:
    return tls_dir(directory) / KEY_NAME


def apply_request_path(directory: Optional[Path] = None) -> Path:
    return tls_dir(directory) / APPLY_REQUEST


def apply_status_path(directory: Optional[Path] = None) -> Path:
    return tls_dir(directory) / APPLY_STATUS


def _normalize_pem(raw: bytes | str) -> bytes:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.replace(b"\r\n", b"\n").strip() + b"\n"


def _load_size_check(raw: bytes, label: str) -> None:
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError(f"{label}: файл больше {MAX_UPLOAD_BYTES} байт")


def _iso_z(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_pem_pair(
    cert_pem: bytes | str,
    key_pem: bytes | str,
    *,
    chain_pem: bytes | str = b"",
    domain: str = "",
) -> tuple[bool, str, dict[str, Any]]:
    """Проверить PEM leaf (+chain) и private key; ключ = пара к leaf.

    Возвращает (ok, russian_error, info). info без plaintext ключа.
    В info кладётся `_normalized_cert` / `_normalized_key` для записи.
    """
    try:
        cert_bytes = _normalize_pem(cert_pem)
        key_bytes = _normalize_pem(key_pem)
        _load_size_check(cert_bytes, "certificate")
        _load_size_check(key_bytes, "private_key")
        chain_bytes = b""
        if chain_pem:
            chain_bytes = _normalize_pem(chain_pem)
            _load_size_check(chain_bytes, "chain")
    except ValueError as exc:
        return False, str(exc), {}

    cert_blocks = _PEM_CERT_RE.findall(cert_bytes)
    if not cert_blocks:
        return False, "Не удалось разобрать сертификат: нужен PEM (BEGIN CERTIFICATE).", {}

    if chain_bytes:
        chain_blocks = _PEM_CERT_RE.findall(chain_bytes)
        if not chain_blocks:
            return False, "Цепочка (chain): нужен PEM с BEGIN CERTIFICATE.", {}
        full_blocks = [cert_blocks[0]] + chain_blocks
    else:
        full_blocks = cert_blocks

    key_blocks = _PEM_KEY_RE.findall(key_bytes)
    if not key_blocks:
        return (
            False,
            "Не удалось разобрать private key: нужен PEM (BEGIN PRIVATE KEY / RSA / EC).",
            {},
        )
    if len(key_blocks) > 1:
        return False, "В файле ключа несколько PRIVATE KEY — загрузите один ключ.", {}

    try:
        leaf = x509.load_pem_x509_certificate(full_blocks[0] + b"\n")
    except Exception:  # noqa: BLE001
        return False, "Сертификат повреждён или не в формате PEM.", {}

    for i, block in enumerate(full_blocks[1:], start=2):
        try:
            x509.load_pem_x509_certificate(block + b"\n")
        except Exception:  # noqa: BLE001
            return False, f"Цепочка сертификатов: блок #{i} не читается как PEM.", {}

    try:
        key = serialization.load_pem_private_key(key_blocks[0] + b"\n", password=None)
    except TypeError:
        return (
            False,
            "Private key защищён паролем — загрузите незашифрованный PEM.",
            {},
        )
    except Exception:  # noqa: BLE001
        return False, "Private key повреждён или не в формате PEM.", {}

    try:
        cert_pub = leaf.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        key_pub = key.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
    except Exception:  # noqa: BLE001
        return False, "Не удалось сравнить публичные ключи сертификата и ключа.", {}

    if cert_pub != key_pub:
        return False, "Private key не соответствует загруженному сертификату.", {}

    info = cert_info_from_leaf(leaf, chain_len=len(full_blocks))
    warnings: list[str] = []
    now = datetime.now(timezone.utc)
    if leaf.not_valid_after_utc < now:
        warnings.append("Срок действия сертификата уже истёк.")
    else:
        days = (leaf.not_valid_after_utc - now).days
        if days <= 14:
            warnings.append(f"Сертификат истекает через {days} дн.")

    domain = (domain or "").strip()
    if domain and domain != "_":
        sans = {s.casefold() for s in info.get("san") or []}
        try:
            for attr in leaf.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME):
                sans.add(str(attr.value).casefold())
        except Exception:  # noqa: BLE001
            pass
        d = domain.casefold()
        matched = d in sans or any(
            s.startswith("*.") and (d.endswith(s[1:]) or d == s[2:]) for s in sans
        )
        if not matched:
            warnings.append(
                f"CN/SAN сертификата может не покрывать BAD_DOMAIN={domain}."
            )

    info["warnings"] = warnings
    info["_normalized_cert"] = b"\n".join(full_blocks) + b"\n"
    info["_normalized_key"] = key_blocks[0] + b"\n"
    return True, "", info


def cert_info_from_leaf(leaf: x509.Certificate, *, chain_len: int = 1) -> dict[str, Any]:
    subject = leaf.subject.rfc4514_string()
    issuer = leaf.issuer.rfc4514_string()
    fp = leaf.fingerprint(hashes.SHA256()).hex()
    sans: list[str] = []
    try:
        ext = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        for name in ext.value:
            if isinstance(name, x509.DNSName):
                sans.append(name.value)
            else:
                sans.append(str(name.value))
    except Exception:  # noqa: BLE001
        pass
    return {
        "subject": subject,
        "issuer": issuer,
        "not_after": _iso_z(leaf.not_valid_after_utc),
        "fingerprint_sha256": fp,
        "san": sans,
        "chain_length": chain_len,
    }


def read_installed_cert_info(directory: Optional[Path] = None) -> Optional[dict[str, Any]]:
    path = cert_path(directory)
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
        blocks = _PEM_CERT_RE.findall(raw)
        if not blocks:
            return None
        leaf = x509.load_pem_x509_certificate(blocks[0] + b"\n")
        info = cert_info_from_leaf(leaf, chain_len=len(blocks))
        info["has_private_key"] = key_path(directory).is_file()
        try:
            info["cert_mtime"] = _iso_z(
                datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            )
        except OSError:
            info["cert_mtime"] = None
        return info
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cannot read installed cert: %s", exc)
        return None


def tls_configured(directory: Optional[Path] = None) -> bool:
    # Symlink bootstrap from old install still counts (both paths present).
    return cert_path(directory).is_file() and key_path(directory).is_file()


def read_domain_from_env() -> str:
    """BAD_DOMAIN из site.env (read-only в UI)."""
    site_env = Path("/etc/bad/site.env")
    if site_env.is_file():
        try:
            for line in site_env.read_text(encoding="utf-8").splitlines():
                if line.startswith("BAD_DOMAIN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return os.environ.get("BAD_DOMAIN", "").strip()


def save_tls_materials(
    cert_pem: bytes | str,
    key_pem: bytes | str,
    *,
    chain_pem: bytes | str = b"",
    directory: Optional[Path] = None,
) -> dict[str, Any]:
    """Валидировать, записать в staging/, запросить apply (root unit).

    Боевые fullchain/privkey меняет только apply-скрипт после nginx -t.
    Private key никогда не возвращается.
    """
    domain = read_domain_from_env()
    ok, err, info = validate_pem_pair(
        cert_pem, key_pem, chain_pem=chain_pem, domain=domain
    )
    if not ok:
        raise ValueError(err)

    root = tls_dir(directory)
    stage = staging_dir(directory)
    root.mkdir(parents=True, exist_ok=True)
    stage.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o750)
        stage.chmod(0o750)
    except OSError:
        pass

    cert_bytes: bytes = info.pop("_normalized_cert")
    key_bytes: bytes = info.pop("_normalized_key")

    c_tmp = stage / f".{CERT_NAME}.tmp"
    k_tmp = stage / f".{KEY_NAME}.tmp"
    c_dest = stage / CERT_NAME
    k_dest = stage / KEY_NAME
    c_tmp.write_bytes(cert_bytes)
    k_tmp.write_bytes(key_bytes)
    try:
        c_tmp.chmod(0o644)
        k_tmp.chmod(0o600)
    except OSError:
        pass
    c_tmp.replace(c_dest)
    k_tmp.replace(k_dest)

    request_apply(directory)
    info["has_private_key"] = True
    info["saved_at"] = utc_now()
    info["domain"] = domain
    logger.info(
        "TLS staging saved subject=%s fp=%s",
        info.get("subject"),
        (info.get("fingerprint_sha256") or "")[:16],
    )
    return info


def request_apply(directory: Optional[Path] = None) -> None:
    path = apply_request_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"requested_at": utc_now()}
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    try:
        path.chmod(0o640)
    except OSError:
        pass


def read_apply_status(directory: Optional[Path] = None) -> dict[str, Any]:
    path = apply_status_path(directory)
    if not path.is_file():
        return {
            "ok": None,
            "message": "apply ещё не выполнялся",
            "mode": "http" if not tls_configured(directory) else "https",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"ok": False, "message": "status corrupt"}
    except Exception:  # noqa: BLE001
        return {"ok": False, "message": "не удалось прочитать apply.status"}


def wait_for_apply(
    directory: Optional[Path] = None,
    *,
    since: str = "",
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Дождаться нового apply.status (path unit → root script)."""
    import time

    deadline = time.time() + max(0.5, timeout_seconds)
    while time.time() < deadline:
        st = read_apply_status(directory)
        applied = str(st.get("applied_at") or "")
        if applied and (not since or applied >= since):
            if st.get("ok") is not None:
                return st
        time.sleep(0.25)
    return read_apply_status(directory)


def tls_status(directory: Optional[Path] = None) -> dict[str, Any]:
    configured = tls_configured(directory)
    apply = read_apply_status(directory)
    mode = apply.get("mode") or ("https" if configured else "http")
    return {
        "configured": configured,
        "mode": mode,
        "domain": read_domain_from_env(),
        "cert": read_installed_cert_info(directory),
        "apply": apply,
        "cert_path": str(cert_path(directory)),
        "has_private_key": key_path(directory).is_file(),
    }
