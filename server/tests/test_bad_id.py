"""Номер BAD- из платы или случайный. На машине Alex не запускать."""

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

from fastapi.testclient import TestClient

from bad_server.config import get_settings

get_settings.cache_clear()

from bad_server.app import create_app  # noqa: E402

_GUID = "6f0bc3d6-87c4-4608-9c01-e6e7c7d2e6c5"
_UUID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_UUID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
_BAD = re.compile(r"^BAD-[0-9A-F]{8}$")


def _fp() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def _request(client: TestClient, fingerprint: str, **extra: str) -> None:
    body = {
        "hostname": "PC",
        "ip": "10.0.0.8",
        "serial": extra.pop("serial", "SN"),
        "fingerprint": fingerprint,
    }
    body.update(extra)
    response = client.post("/v1/enrollment-requests", json=body)
    assert response.status_code == 200, response.text


def _login(client: TestClient) -> None:
    db = client.app.state.db
    with db.connection() as conn:
        conn.execute(
            "UPDATE local_users SET must_change_password = 0 WHERE username = %s",
            ("admin",),
        )
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert token is not None
    logged = client.post(
        "/login",
        data={"username": "admin", "password": "admin", "csrf_token": token.group(1)},
        follow_redirects=False,
    )
    assert logged.status_code == 303, logged.text


def _allow(client: TestClient, fingerprint: str) -> str:
    page = client.get("/devices/enrollment-requests")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert token is not None
    allowed = client.post(
        f"/devices/enrollment-requests/{fingerprint.lower()}/allow",
        data={"csrf_token": token.group(1)},
        follow_redirects=False,
    )
    assert allowed.status_code == 303, allowed.text
    row = client.app.state.db.get_enrollment_request(fingerprint.lower())
    assert row["status"] == "approved"
    assert _BAD.match(row["bad_id"])
    return row["bad_id"]


def _claim(client: TestClient, fingerprint: str) -> dict:
    response = client.post(
        "/v1/enrollment-requests",
        json={
            "hostname": "PC",
            "ip": "10.0.0.8",
            "serial": "SN",
            "fingerprint": fingerprint,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("api_key")
    return body


def _snaps(client: TestClient, bad_id: str) -> int:
    with client.app.state.db.connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM inventory_snapshots WHERE bad_id = %s",
            (bad_id,),
        ).fetchone()
    return int(row["n"])


def _device_count(client: TestClient) -> int:
    with client.app.state.db.connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM devices").fetchone()
    return int(row["n"])


def test_same_board_same_bad_id() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        first = _fp()
        second = _fp()
        _request(client, first, machine_guid=_GUID, smbios_uuid=_UUID_A)
        first_id = _allow(client, first)
        _request(client, second, machine_guid=_GUID, smbios_uuid=_UUID_A)
        second_id = _allow(client, second)
        assert first_id == second_id
        assert _device_count(client) == 1


def test_other_board_new_bad_id() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        first = _fp()
        _request(client, first, machine_guid=_GUID, smbios_uuid=_UUID_A)
        first_id = _allow(client, first)
        claimed = _claim(client, first)
        posted = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {claimed['api_key']}"},
            json={
                "schema_version": 2,
                "bad_id": first_id,
                "host": {"hostname": "OLD"},
                "hardware": {"smbios_uuid": _UUID_A},
            },
        )
        assert posted.status_code == 200, posted.text
        other = _fp()
        _request(client, other, machine_guid=_GUID, smbios_uuid=_UUID_B)
        other_id = _allow(client, other)
        assert other_id != first_id
        assert _snaps(client, first_id) == 1


def test_disk_serial_ignored() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        first = _fp()
        second = _fp()
        _request(client, first, machine_guid=_GUID, smbios_uuid=_UUID_A, serial="DISK-1")
        first_id = _allow(client, first)
        _request(client, second, machine_guid=_GUID, smbios_uuid=_UUID_A, serial="DISK-2")
        second_id = _allow(client, second)
        assert first_id == second_id


def test_random_without_uuid() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        first = _fp()
        _request(client, first, machine_guid="", smbios_uuid="")
        first_id = _allow(client, first)
        claimed = _claim(client, first)
        posted = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {claimed['api_key']}"},
            json={
                "schema_version": 2,
                "bad_id": first_id,
                "host": {"hostname": "RAND"},
                "hardware": {"smbios_uuid": _UUID_A},
            },
        )
        assert posted.status_code == 200, posted.text
        assert _snaps(client, first_id) == 1
        assert client.app.state.db.get_device_auth_row(first_id)["bad_id"] == first_id
        second = _fp()
        _request(client, second, machine_guid="", smbios_uuid="")
        second_id = _allow(client, second)
        assert second_id != first_id
        assert _BAD.match(second_id)


def test_board_changed() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        fingerprint = _fp()
        _request(client, fingerprint, machine_guid=_GUID, smbios_uuid=_UUID_A)
        bad_id = _allow(client, fingerprint)
        claimed = _claim(client, fingerprint)
        headers = {"Authorization": f"Bearer {claimed['api_key']}"}
        first = client.post(
            "/v1/inventory",
            headers=headers,
            json={
                "schema_version": 2,
                "bad_id": bad_id,
                "hardware": {"smbios_uuid": _UUID_A},
            },
        )
        assert first.status_code == 200, first.text
        second = client.post(
            "/v1/inventory",
            headers=headers,
            json={
                "schema_version": 2,
                "bad_id": bad_id,
                "hardware": {"smbios_uuid": _UUID_B},
            },
        )
        assert second.status_code == 409, second.text
        assert second.json()["detail"] == "board changed"
        assert "api_key" not in second.json()
        assert _device_count(client) == 1
        assert _snaps(client, bad_id) == 1


def test_bad_id_required() -> None:
    with TestClient(create_app()) as client:
        _login(client)
        fingerprint = _fp()
        _request(client, fingerprint, machine_guid=_GUID, smbios_uuid=_UUID_A)
        bad_id = _allow(client, fingerprint)
        claimed = _claim(client, fingerprint)
        headers = {"Authorization": f"Bearer {claimed['api_key']}"}
        missing = client.post(
            "/v1/heartbeat",
            headers=headers,
            json={"agent_version": "test"},
        )
        assert missing.status_code != 200
        foreign = client.post(
            "/v1/heartbeat",
            headers=headers,
            json={"bad_id": "BAD-FFFFFFFF", "agent_version": "test"},
        )
        assert foreign.status_code == 403, foreign.text
        assert foreign.json()["detail"] == "bad_id mismatch"
        assert bad_id != "BAD-FFFFFFFF"
