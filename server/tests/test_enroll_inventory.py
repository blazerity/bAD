from __future__ import annotations

import os
from pathlib import Path

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

    monkeypatch.setenv("BAD_AGENT_UPDATES_DIR", str(tmp_path / "agent-updates"))
    monkeypatch.setenv("BAD_AGENT_UPDATE_SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("BAD_GITHUB_REPO", "blazerity/bAD")

    from bad_server.config import get_settings

    get_settings.cache_clear()

    from bad_server.app import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()


def test_health(client: TestClient):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.2.0"


def test_enroll_inventory_get_flow(client: TestClient):
    enroll = client.post(
        "/v1/enroll",
        headers={"Authorization": "Bearer test-enrollment-token-abcdefghijklmnopqrstuvwxyz"},
        json={
            "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "hostname": "WS-TEST-01",
            "agent_version": "1.0.0",
        },
    )
    assert enroll.status_code == 200, enroll.text
    api_key = enroll.json()["api_key"]
    assert api_key.startswith("bad_ak_")

    inventory = {
        "schema_version": 1,
        "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "collected_at": "2026-10-15T14:55:00Z",
        "agent_version": "1.0.0",
        "host": {
            "hostname": "WS-TEST-01",
            "domain": "CORP",
            "os": {
                "caption": "Microsoft Windows 11 Pro",
                "version": "10.0.22631",
                "build": "22631",
                "arch": "x64",
            },
        },
        "hardware": {
            "cpu": {"name": "Intel Core i7", "cores": 8, "logical": 16},
            "ram_bytes": 17179869184,
            "disks": [{"model": "SSD", "size_bytes": 512110190592}],
            "volumes": [{"letter": "C:", "size_bytes": 511862308864, "free_bytes": 120259084288}],
        },
        "network": {
            "nics": [
                {
                    "name": "Ethernet",
                    "mac": "00:11:22:33:44:55",
                    "ipv4": ["10.20.30.40"],
                    "dhcp": True,
                }
            ]
        },
        "users": {"logged_on": ["CORP\\jdoe"], "last_interactive": "CORP\\jdoe"},
        "collector_errors": [],
    }

    inv = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json=inventory,
    )
    assert inv.status_code == 200, inv.text

    hb = client.post(
        "/v1/heartbeat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "agent_version": "1.0.0",
            "last_inventory_at": "2026-10-15T14:55:00Z",
        },
    )
    assert hb.status_code == 200

    devices = client.get(
        "/v1/devices",
        headers={"Authorization": "Bearer test-admin-token-abcdefghijklmnopqrstuvwxyz"},
    )
    assert devices.status_code == 200
    assert len(devices.json()["devices"]) == 1
    assert devices.json()["devices"][0]["hostname"] == "WS-TEST-01"

    detail = client.get(
        "/v1/devices/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        headers={"Authorization": "Bearer test-admin-token-abcdefghijklmnopqrstuvwxyz"},
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["latest_inventory"]["payload"]["schema_version"] == 1
    assert body["latest_inventory"]["payload"]["hardware"]["cpu"]["cores"] == 8

    # upsert second inventory
    inventory["collected_at"] = "2026-10-15T15:00:00Z"
    inventory["hardware"]["ram_bytes"] = 34359738368
    inv2 = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json=inventory,
    )
    assert inv2.status_code == 200
    detail2 = client.get(
        "/v1/devices/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        headers={"Authorization": "Bearer test-admin-token-abcdefghijklmnopqrstuvwxyz"},
    )
    assert detail2.json()["latest_inventory"]["payload"]["hardware"]["ram_bytes"] == 34359738368


def test_unknown_schema_rejected(client: TestClient):
    enroll = client.post(
        "/v1/enroll",
        headers={"Authorization": "Bearer test-enrollment-token-abcdefghijklmnopqrstuvwxyz"},
        json={"device_id": "device-schema-test", "hostname": "X", "agent_version": "1.0.0"},
    )
    api_key = enroll.json()["api_key"]
    r = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "schema_version": 99,
            "device_id": "device-schema-test",
            "collector_errors": [],
        },
    )
    assert r.status_code == 400


def test_web_login_and_devices(client: TestClient):
    # seed a device
    enroll = client.post(
        "/v1/enroll",
        headers={"Authorization": "Bearer test-enrollment-token-abcdefghijklmnopqrstuvwxyz"},
        json={"device_id": "web-device", "hostname": "WEB-HOST", "agent_version": "0.2.0"},
    )
    assert enroll.status_code == 200

    denied = client.get("/devices", follow_redirects=False)
    assert denied.status_code == 303
    assert denied.headers["location"] == "/login"

    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    assert "bad_session" in login.cookies
    # Default password forces change
    assert login.headers["location"] == "/account/password"

    # Still allowed to reach devices after session is set (banner nudges change)
    page = client.get("/devices")
    assert page.status_code == 200
    assert "WEB-HOST" in page.text
