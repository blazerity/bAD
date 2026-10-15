from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from .config import Settings, get_settings
from .db import Database
from .security import constant_time_equals, extract_bearer, verify_secret


def get_db(request: Request) -> Database:
    return request.app.state.db


def require_enrollment_token(
    authorization: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> str:
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing enrollment token"
        )

    expected = settings.enrollment_token
    if expected:
        if not constant_time_equals(expected, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
            )
        return token

    hashed = db.get_site_secret("enrollment_token_hash")
    if hashed and verify_secret(hashed, token):
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
    )


def require_api_key(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Database = Depends(get_db),
):
    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key"
        )
    device = db.find_device_by_api_key(token, verify_secret)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    return device


def admin_token_valid(token: Optional[str], settings: Settings, db: Database) -> bool:
    if not token:
        return False
    expected = settings.admin_token
    if expected:
        return constant_time_equals(expected, token)
    hashed = db.get_site_secret("admin_token_hash")
    if hashed:
        return verify_secret(hashed, token)
    return False


def require_admin_token(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
) -> str:
    token = extract_bearer(authorization)
    if not token:
        token = request.cookies.get("bad_admin_token")
    if not admin_token_valid(token, settings, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token"
        )
    return token or ""
