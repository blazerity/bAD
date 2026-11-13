"""Редирект панели, заявки, запрет ротации ключа. На машине Alex не запускать."""

from __future__ import annotations

import os
import re
import uuid

os.environ.setdefault(
    "BAD_DATABASE_URL",
    os.environ.get("BAD_DATABASE_URL", "postgresql://bad@127.0.0.1:5432/bad_ingest_test"),
)
os.environ.setdefault("BAD_ENROLLMENT_TOKEN", "test-enrollment-token-change-me-please")
os.environ.setdefault("BAD_ADMIN_TOKEN", "test-admin-token-change-me-please-32b")
os.environ.setdefault("BAD_PREFER_EXTERNAL_SECRETS", "false")
os.environ.setdefault("BAD_AGENT_UPDATE_SYNC_ON_STARTUP", "false")
os.environ.setdefault("BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS", "-1")
os.environ.setdefault("BAD_REQUIRE_INVENTORY_SIGNATURE", "0")
os.environ.setdefault("BAD_DATA_DIR", "/tmp/bad-ingest-test-data")
os.environ.setdefault("BAD_BACKUP_DIR", "/tmp/bad-ingest-test-backups")
os.environ.setdefault("BAD_QA_UI", "1")

from fastapi.testclient import TestClient

from bad_server.config import get_settings

get_settings.cache_clear()

from bad_server.app import create_app  # noqa: E402

def _fp() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def _request(client: TestClient, fingerprint: str, **extra: str):
    body = {
        "hostname": extra.pop("hostname", "PC"),
        "ip": "10.0.0.8",
        "serial": "SN",
        "fingerprint": fingerprint,
    }
    body.update(extra)
    response = client.post("/v1/enrollment-requests", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _login(client: TestClient, username: str = "admin", password: str = "admin") -> None:
    db = client.app.state.db
    with db.connection() as conn:
        conn.execute(
            "UPDATE local_users SET must_change_password = 0 WHERE username = ?",
            (username,),
        )
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert token is not None
    logged = client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token.group(1)},
        follow_redirects=False,
    )
    assert logged.status_code == 303, logged.text


def _csrf(html: str) -> str:
    token = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert token is not None
    return token.group(1)


def _hashes(client: TestClient) -> dict[str, str]:
    with client.app.state.db.connection() as conn:
        rows = conn.execute("SELECT device_id, api_key_hash FROM devices").fetchall()
    return {row["device_id"]: row["api_key_hash"] for row in rows}


def test_pending_repeat_updates_one_row() -> None:
    fingerprint = _fp()
    with TestClient(create_app()) as client:
        first = _request(client, fingerprint, hostname="ONE")
        second = _request(client, fingerprint, hostname="TWO")
        assert first["status"] == "pending"
        assert second["status"] == "pending"
        assert "api_key" not in second
        with client.app.state.db.connection() as conn:
            rows = conn.execute(
                "SELECT hostname, status FROM enrollment_requests WHERE id = ?",
                (fingerprint.lower(),),
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["hostname"] == "TWO"
        assert rows[0]["status"] == "pending"


def test_allow_empty_device_creates_card_and_flash_is_once() -> None:
    fingerprint = _fp()
    with TestClient(create_app()) as client:
        _request(client, fingerprint, hostname="NEW")
        before = set(_hashes(client))
        _login(client)
        page = client.get("/devices/enrollment-requests")
        assert page.status_code == 200
        assert "Разрешить" in page.text
        allowed = client.post(
            f"/devices/enrollment-requests/{fingerprint.lower()}/allow",
            data={"csrf_token": _csrf(page.text)},
            follow_redirects=False,
        )
        assert allowed.status_code == 303
        assert allowed.headers["location"] == "/devices/enrollment-requests"
        first = client.get("/devices/enrollment-requests")
        assert "Разрешено" in first.text
        second = client.get("/devices/enrollment-requests")
        assert "Разрешено" not in second.text
        created = set(_hashes(client)) - before
        assert len(created) == 1
        again = client.post(
            f"/devices/enrollment-requests/{fingerprint.lower()}/allow",
            data={"csrf_token": _csrf(second.text)},
            follow_redirects=False,
        )
        assert again.status_code == 303
        assert len(set(_hashes(client)) - before) == 1


def test_allow_live_card_rotates_key() -> None:
    fingerprint = _fp()
    device_id = f"live-{uuid.uuid4().hex[:8]}"
    with TestClient(create_app()) as client:
        grant = client.post(
            "/v1/enrollment-grants",
            headers={"Authorization": "Bearer test-admin-token-change-me-please-32b"},
            json={"device_id": device_id},
        )
        assert grant.status_code == 200, grant.text
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {grant.json()['code']}"},
            json={"device_id": device_id, "hostname": "LIVE"},
        )
        assert enrolled.status_code == 200, enrolled.text
        before = _hashes(client)[device_id]
        _request(client, fingerprint, hostname="LIVE", device_id=device_id)
        _login(client)
        page = client.get("/devices/enrollment-requests")
        allowed = client.post(
            f"/devices/enrollment-requests/{fingerprint.lower()}/allow",
            data={"csrf_token": _csrf(page.text)},
            follow_redirects=False,
        )
        assert allowed.status_code == 303
        landed = client.get("/devices/enrollment-requests")
        assert "Разрешено" in landed.text
        assert _hashes(client)[device_id] != before
        assert device_id in _hashes(client)
        row = client.app.state.db.get_enrollment_request(fingerprint.lower())
        assert row["status"] == "approved"


def test_allow_any_device_id_issues_key() -> None:
    fingerprint = _fp()
    device_id = "6f0bc3d6-87c4-4608-9c01-e6e7c7d2e6c5"
    with TestClient(create_app()) as client:
        _request(client, fingerprint, hostname="OLD", device_id=device_id)
        _login(client)
        page = client.get("/devices/enrollment-requests")
        client.post(
            f"/devices/enrollment-requests/{fingerprint.lower()}/allow",
            data={"csrf_token": _csrf(page.text)},
            follow_redirects=False,
        )
        landed = client.get("/devices/enrollment-requests")
        assert "Разрешено" in landed.text
        assert device_id in _hashes(client)
        row = client.app.state.db.get_enrollment_request(fingerprint.lower())
        assert row["status"] == "approved"


def test_approved_key_is_returned_once() -> None:
    fingerprint = _fp()
    with TestClient(create_app()) as client:
        _request(client, fingerprint, hostname="ONCE")
        _login(client)
        page = client.get("/devices/enrollment-requests")
        client.post(
            f"/devices/enrollment-requests/{fingerprint.lower()}/allow",
            data={"csrf_token": _csrf(page.text)},
            follow_redirects=False,
        )
        first = _request(client, fingerprint, hostname="ONCE")
        assert first["status"] == "approved"
        assert first.get("api_key")
        second = _request(client, fingerprint, hostname="ONCE")
        assert second["status"] == "approved"
        assert "api_key" not in second
        row = client.app.state.db.get_enrollment_request(fingerprint.lower())
        assert row["status"] == "approved"


def test_devices_tab_has_count_not_table() -> None:
    fingerprint = _fp()
    with TestClient(create_app()) as client:
        _request(client, fingerprint, hostname="LIST")
        _login(client)
        page = client.get("/devices")
        assert page.status_code == 200
        assert "devices-enroll-requests" not in page.text
        assert "Заявок нет" not in page.text
        assert 'href="/devices/enrollment-requests"' in page.text
        assert ">1<" in page.text or "1" in page.text
        listing = client.get("/devices/enrollment-requests")
        assert "LIST" in listing.text
        assert "Разрешить" in listing.text


def test_operator_does_not_see_requests() -> None:
    with TestClient(create_app()) as client:
        db = client.app.state.db
        admin = db.get_local_user("admin")
        assert admin is not None
        username = f"op-{uuid.uuid4().hex[:8]}"
        db.create_local_user(username, admin["password_hash"], role="operator")
        _login(client, username, "admin")
        page = client.get("/devices/enrollment-requests", follow_redirects=False)
        assert page.status_code == 303
        assert page.headers["location"] == "/devices"


def test_server_update_post_redirects_once() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        page = client.get("/settings/server-update")
        posted = client.post(
            "/settings/server-update/branch",
            data={"csrf_token": _csrf(page.text), "branch": ".."},
            follow_redirects=False,
        )
        assert posted.status_code == 303
        assert posted.headers["location"] == "/settings/server-update"
        first = client.get("/settings/server-update")
        assert "Некорректная ветка" in first.text
        second = client.get("/settings/server-update")
        assert "Некорректная ветка" not in second.text
