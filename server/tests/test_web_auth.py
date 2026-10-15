from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from helpers import ADMIN_TOKEN


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
    assert "Неверное имя пользователя или пароль" in r.text
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
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert ok.status_code == 200


def test_ldap_settings_crud_and_test_mocked(client: TestClient):
    _login(client)

    page = client.get("/settings/ldap")
    assert page.status_code == 200
    assert "Настройки LDAP" in page.text

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
    assert "Настройки LDAP сохранены" in save.text
    assert "без изменений" in save.text
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

    with patch("bad_server.web.test_connection", return_value=(True, "Соединение и bind успешны")):
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
    assert "ОК: Соединение и bind успешны" in test.text


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
