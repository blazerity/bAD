from __future__ import annotations

from fastapi.testclient import TestClient

from helpers import ADMIN_TOKEN, enroll_device


def test_health(client: TestClient):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.7.0"


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


def test_schema_version_2_with_software_accepted(client: TestClient):
    device_id = "device-schema-v2"
    api_key = enroll_device(
        client,
        device_id=device_id,
        hostname="SW-HOST",
        agent_version="0.7.0",
    )
    r = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "schema_version": 2,
            "device_id": device_id,
            "agent_version": "0.7.0",
            "collected_at": "2026-10-15T16:00:00Z",
            "host": {"hostname": "SW-HOST"},
            "software": {
                "programs": [
                    {"name": "Example App", "version": "1.2.3", "publisher": "Acme"},
                ]
            },
            "collector_errors": [],
        },
    )
    assert r.status_code == 200
    detail = client.get(
        f"/v1/devices/{device_id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail.status_code == 200
    payload = detail.json()["latest_inventory"]["payload"]
    assert payload["schema_version"] == 2
    assert payload["software"]["programs"][0]["name"] == "Example App"


def test_schema_version_2_extended_hardware_accepted(client: TestClient):
    device_id = "device-hw-ext"
    api_key = enroll_device(
        client,
        device_id=device_id,
        hostname="DELL-HOST",
        agent_version="0.7.0",
    )
    hardware = {
        "cpu": {"name": "Intel Core i7", "cores": 8, "logical": 16},
        "ram_bytes": 17179869184,
        "ram_memory_type": "DDR4",
        "serial_number": "SRVTAG01",
        "model": "Latitude 5440",
        "manufacturer": "Dell Inc.",
        "gpus": [
            {"name": "Intel UHD Graphics", "vendor": "Intel Corporation"},
            {"name": "NVIDIA RTX", "vendor": "NVIDIA", "adapter_ram_bytes": 6442450944},
        ],
        "ram_modules": [
            {
                "capacity_bytes": 8589934592,
                "speed_mhz": 3200,
                "part_number": "M471A1K43EB1-CWE",
                "channel": "Channel A",
                "device_locator": "ChannelA-DIMM0",
                "form_factor": "SODIMM",
                "memory_type": "DDR4",
            }
        ],
        "disks": [],
        "volumes": [],
    }
    r = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "schema_version": 2,
            "device_id": device_id,
            "agent_version": "0.7.0",
            "collected_at": "2026-10-15T16:30:00Z",
            "host": {"hostname": "DELL-HOST"},
            "hardware": hardware,
            "collector_errors": [],
        },
    )
    assert r.status_code == 200
    detail = client.get(
        f"/v1/devices/{device_id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail.status_code == 200
    payload = detail.json()["latest_inventory"]["payload"]
    hw = payload["hardware"]
    assert hw["serial_number"] == "SRVTAG01"
    assert hw["model"] == "Latitude 5440"
    assert hw["ram_memory_type"] == "DDR4"
    assert len(hw["gpus"]) == 2
    assert hw["ram_modules"][0]["speed_mhz"] == 3200
    assert hw["ram_modules"][0]["memory_type"] == "DDR4"

    # Web device page renders structured hardware summary when logged in.
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303)
    page = client.get(f"/devices/{device_id}")
    assert page.status_code == 200
    assert "SRVTAG01" in page.text
    assert "Latitude 5440" in page.text
    assert "Intel UHD Graphics" in page.text
    assert "M471A1K43EB1-CWE" in page.text
    assert "DDR4" in page.text


def test_web_login_and_devices(client: TestClient):
    enroll_device(
        client,
        device_id="web-device",
        hostname="WEB-HOST",
        agent_version="0.7.0",
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
