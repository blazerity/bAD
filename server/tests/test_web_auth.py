from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["BAD_ENROLLMENT_TOKEN"] = "test-enrollment-token-abcdefghijklmnopqrstuvwxyz"
os.environ["BAD_ADMIN_TOKEN"] = "test-admin-token-abcdefghijklmnopqrstuvwxyz"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "bad.db"
    monkeypatch.setenv("BAD_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "BAD_ENROLLMENT_TOKEN",
        "test-enrollment-token-abcdefghijklmnopqrstuvwxyz",
    )
    monkeypatch.setenv(
        "BAD_ADMIN_TOKEN",
        "test-admin-token-abcdefghijklmnopqrstuvwxyz",
    )
    monkeypatch.setenv("BAD_SESSION_SECRET", "test-session-secret-abcdefghijklmnopqrstuvwxyz")

    from bad_server.config import get_settings

    get_settings.cache_clear()

    from bad_server.app import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()


def _login(client: TestClient, username: str = "admin", password: str = "admin"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_local_login_success(client: TestClient):
    r = _login(client)
    assert r.status_code == 303
    assert "bad_session" in r.cookies


def test_local_login_failure(client: TestClient):
    r = _login(client, password="wrong")
    assert r.status_code == 401
    assert "Invalid username or password" in r.text
    assert "bad_session" not in r.cookies


def test_devices_require_session(client: TestClient):
    r = client.get("/devices", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

    detail = client.get("/devices/nope", follow_redirects=False)
    assert detail.status_code == 303
    assert detail.headers["location"] == "/login"


def test_admin_api_token_bearer_only(client: TestClient):
    # Cookie session must not unlock admin API
    _login(client)
    r = client.get("/v1/devices")
    assert r.status_code == 401

    ok = client.get(
        "/v1/devices",
        headers={"Authorization": "Bearer test-admin-token-abcdefghijklmnopqrstuvwxyz"},
    )
    assert ok.status_code == 200


def test_ldap_settings_crud_and_test_mocked(client: TestClient):
    _login(client)

    page = client.get("/settings/ldap")
    assert page.status_code == 200
    assert "LDAP settings" in page.text

    save = client.post(
        "/settings/ldap",
        data={
            "enabled": "1",
            "host": "ldap.example.com",
            "port": "389",
            "bind_dn": "cn=svc,dc=example,dc=com",
            "bind_password": "s3cret-bind",
            "user_search_base": "ou=people,dc=example,dc=com",
            "user_filter_template": "(uid={username})",
            "display_name_attr": "cn",
            "default_role": "operator",
        },
    )
    assert save.status_code == 200
    assert "LDAP settings saved" in save.text
    assert "unchanged" in save.text
    assert "s3cret-bind" not in save.text

    # Update without password keeps previous secret
    save2 = client.post(
        "/settings/ldap",
        data={
            "enabled": "1",
            "host": "ldap.example.com",
            "port": "636",
            "use_ssl": "1",
            "bind_dn": "cn=svc,dc=example,dc=com",
            "bind_password": "",
            "user_search_base": "ou=people,dc=example,dc=com",
            "user_filter_template": "(sAMAccountName={username})",
            "display_name_attr": "displayName",
            "default_role": "operator",
        },
    )
    assert save2.status_code == 200
    assert 'value="636"' in save2.text
    assert "sAMAccountName" in save2.text

    with patch("bad_server.web.test_connection", return_value=(True, "Connection and bind succeeded")):
        test = client.post(
            "/settings/ldap/test",
            data={
                "enabled": "1",
                "host": "ldap.example.com",
                "port": "636",
                "use_ssl": "1",
                "bind_dn": "cn=svc,dc=example,dc=com",
                "bind_password": "",
                "user_search_base": "ou=people,dc=example,dc=com",
                "user_filter_template": "(sAMAccountName={username})",
                "display_name_attr": "displayName",
                "default_role": "operator",
            },
        )
    assert test.status_code == 200
    assert "OK: Connection and bind succeeded" in test.text


def test_ldap_settings_requires_admin_session(client: TestClient):
    r = client.get("/settings/ldap", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_change_password_clears_must_change(client: TestClient):
    login = _login(client)
    assert login.headers["location"] == "/account/password"

    bad = client.post(
        "/account/password",
        data={
            "current_password": "admin",
            "new_password": "admin",
            "new_password_confirm": "admin",
        },
    )
    assert bad.status_code == 400

    ok = client.post(
        "/account/password",
        data={
            "current_password": "admin",
            "new_password": "correct-horse-battery",
            "new_password_confirm": "correct-horse-battery",
        },
        follow_redirects=False,
    )
    assert ok.status_code == 303
    assert ok.headers["location"] == "/devices"

    fail_old = _login(client, password="admin")
    assert fail_old.status_code == 401

    ok2 = _login(client, password="correct-horse-battery")
    assert ok2.status_code == 303
    assert ok2.headers["location"] == "/devices"
