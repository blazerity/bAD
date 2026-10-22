"""HTTP bootstrap guards: sensitive UI ops + cleartext enroll after managed TLS."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Request

from .config import Settings
from .tls_ops import tls_configured, tls_status

HTTP_SENSITIVE_MSG = (
    "Операция недоступна, пока сайт без защищённого соединения: "
    "сначала загрузите сертификат в Параметры → Сертификат."
)

ENROLL_CLEARTEXT_MSG = (
    "HTTPS required for enrollment (managed TLS active; "
    "cleartext refused). Lab: BAD_ALLOW_ENROLL_OVER_HTTP=1."
)


def request_is_cleartext(request: Request) -> bool:
    """True when the client-facing hop is HTTP (honours X-Forwarded-Proto)."""
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if proto == "https":
        return False
    if proto == "http":
        return True
    return request.url.scheme != "https"


def tls_mode_http(directory: Optional[Path] = None) -> bool:
    return (tls_status(directory).get("mode") or "http") != "https"


def sensitive_over_http_blocked(
    settings: Settings,
    *,
    directory: Optional[Path] = None,
) -> bool:
    """Block site-bundle / password saves while UI is still in HTTP bootstrap mode."""
    if settings.allow_sensitive_over_http:
        return False
    return tls_mode_http(directory)


def enroll_cleartext_blocked(
    request: Request,
    settings: Settings,
    *,
    directory: Optional[Path] = None,
) -> bool:
    """Refuse /v1/enroll on cleartext once managed TLS files are present."""
    if settings.allow_enroll_over_http:
        return False
    if not tls_configured(directory):
        return False
    return request_is_cleartext(request)
