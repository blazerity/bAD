"""CSRF synchronizer (double-submit cookie) for web HTML forms.

Contract (UI + Server):
- Cookie: ``bad_csrf`` (readable by browser; SameSite=Lax)
- Form field: ``csrf_token`` (hidden input on every state-changing POST)
- Validate: cookie value must equal form field (constant-time)
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Request
from fastapi.responses import Response

from .security import constant_time_equals

CSRF_COOKIE = "bad_csrf"
CSRF_FIELD = "csrf_token"
CSRF_MAX_AGE = 60 * 60 * 12  # align with session


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_request_csrf(request: Request) -> str:
    """Token already attached to request.state (middleware) or from cookie."""
    token = getattr(request.state, "csrf_token", None)
    if token:
        return str(token)
    return request.cookies.get(CSRF_COOKIE) or ""


def ensure_request_csrf(request: Request) -> str:
    """Ensure request.state.csrf_token; reuse cookie when present."""
    existing = getattr(request.state, "csrf_token", None)
    if existing:
        return str(existing)
    cookie = request.cookies.get(CSRF_COOKIE) or ""
    token = cookie if cookie else new_csrf_token()
    request.state.csrf_token = token
    request.state.csrf_set_cookie = not cookie
    return token


def csrf_cookie_needs_set(request: Request) -> bool:
    return bool(getattr(request.state, "csrf_set_cookie", False))


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        httponly=False,
        samesite="lax",
        max_age=CSRF_MAX_AGE,
        path="/",
    )


def validate_csrf(cookie_token: Optional[str], form_token: Optional[str]) -> bool:
    return constant_time_equals(cookie_token or "", form_token or "")
