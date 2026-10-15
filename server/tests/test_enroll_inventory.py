from __future__ import annotations

from fastapi.testclient import TestClient

from helpers import ADMIN_TOKEN, enroll_device


def test_health(client: TestClient):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.2.0"


def test_enroll_inventory_get_flow(client: TestClient):
    device_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    api_key = enroll_device(
        client,
        device_id=device_id,
        hostname="WS-TEST-01",
        agent_version="1.0.0",
    )
    assert api_key.startswith("bad_ak_")

    inventory = {
        "schema_version": 1,
        "device_id": device_id,
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
            "device_id": device_id,
            "agent_version": "1.0.0",
            "last_inventory_at": "2026-10-15T14:55:00Z",
        },
    )
    assert hb.status_code == 200

    devices = client.get(
        "/v1/devices",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert devices.status_code == 200
    assert len(devices.json()["devices"]) == 1
    assert devices.json()["devices"][0]["hostname"] == "WS-TEST-01"
    # Heartbeat must merge last_inventory_at without wiping inventory meta (e.g. os).
    assert devices.json()["devices"][0]["meta"]["os"] == "Microsoft Windows 11 Pro"
    assert devices.json()["devices"][0]["meta"]["last_inventory_at"] == "2026-10-15T14:55:00Z"

    detail = client.get(
        f"/v1/devices/{device_id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["latest_inventory"]["payload"]["schema_version"] == 1
    assert body["latest_inventory"]["payload"]["hardware"]["cpu"]["cores"] == 8
    assert body["meta"]["os"] == "Microsoft Windows 11 Pro"

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
        f"/v1/devices/{device_id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail2.json()["latest_inventory"]["payload"]["hardware"]["ram_bytes"] == 34359738368


def test_unknown_schema_rejected(client: TestClient):
    api_key = enroll_device(
        client,
        device_id="device-schema-test",
        hostname="X",
        agent_version="1.0.0",
    )
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
    enroll_device(
        client,
        device_id="web-device",
        hostname="WEB-HOST",
        agent_version="0.2.0",
    )

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
