"""CSRF synchronizer (double-submit cookie) for web HTML forms."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import Response

CSRF_COOKIE = "bad_csrf"
CSRF_FORM_FIELD = "csrf_token"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_csrf_token(request: Request) -> str:
    existing = request.cookies.get(CSRF_COOKIE)
    if existing and len(existing) >= 16:
        return existing
    cached = getattr(request.state, "csrf_token", None)
    if cached:
        return cached
    token = new_csrf_token()
    request.state.csrf_token = token
    return token


def set_csrf_cookie(
    response: Response,
    token: str,
    *,
    secure: bool = False,
) -> None:
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=12 * 3600,
        path="/",
    )


def validate_csrf(request: Request, form_token: Optional[str]) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE) or getattr(
        request.state, "csrf_token", None
    )
    if not cookie or not form_token:
        return False
    return secrets.compare_digest(str(cookie), str(form_token))


async def ensure_csrf(request: Request) -> None:
    """Router dependency: validate CSRF on POST web forms (SEC-010).

    Runs before Form() params so ``request.form()`` is cached for handlers.
    """
    if request.method != "POST":
        return
    form = await request.form()
    token = form.get(CSRF_FORM_FIELD)
    if isinstance(token, list):
        token = token[0] if token else None
    if not validate_csrf(request, str(token) if token else None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


def cookie_secure_for_request(request: Request, settings_secure: Optional[bool]) -> bool:
    if settings_secure is True:
        return True
    if settings_secure is False:
        return False
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if proto == "https":
        return True
    return request.url.scheme == "https"
