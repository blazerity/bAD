from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import __version__
from .auth import admin_token_valid, get_db
from .config import Settings, get_settings
from .db import Database

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["app_version"] = __version__

router = APIRouter(tags=["web"])


def _admin_from_request(request: Request, settings: Settings, db: Database) -> Optional[str]:
    token = request.cookies.get("bad_admin_token")
    if admin_token_valid(token, settings, db):
        return token
    return None


@router.get("/", response_class=HTMLResponse)
def home(request: Request, settings: Settings = Depends(get_settings), db: Database = Depends(get_db)):
    if not _admin_from_request(request, settings, db):
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/devices", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": error},
    )


@router.post("/login")
def login_submit(
    request: Request,
    admin_token: str = Form(...),
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
):
    if not admin_token_valid(admin_token.strip(), settings, db):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid admin token"},
            status_code=401,
        )
    resp = RedirectResponse(url="/devices", status_code=303)
    resp.set_cookie(
        key="bad_admin_token",
        value=admin_token.strip(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("bad_admin_token", path="/")
    return resp


@router.get("/devices", response_class=HTMLResponse)
def devices_page(
    request: Request,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
):
    if not _admin_from_request(request, settings, db):
        return RedirectResponse(url="/login", status_code=303)
    devices = db.list_devices()
    return templates.TemplateResponse(
        request,
        "devices.html",
        {"devices": devices},
    )


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail_page(
    device_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    db: Database = Depends(get_db),
):
    if not _admin_from_request(request, settings, db):
        return RedirectResponse(url="/login", status_code=303)
    detail = db.get_device_detail(device_id)
    if not detail:
        return templates.TemplateResponse(
            request,
            "device_missing.html",
            {"device_id": device_id},
            status_code=404,
        )
    inventory_pretty = None
    latest = detail.get("latest_inventory")
    if latest and latest.get("payload") is not None:
        inventory_pretty = json.dumps(latest["payload"], indent=2, ensure_ascii=False)
    return templates.TemplateResponse(
        request,
        "device_detail.html",
        {"device": detail, "inventory_pretty": inventory_pretty},
    )
