"""Inventory change events, device tags filter, silence helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bad_server.agent_config import compute_effective_config
from bad_server.device_health import device_silence_status, normalize_tags
from bad_server.inventory_events import diff_inventory_snapshots
from helpers import ADMIN_TOKEN, enroll_device


def _base_inventory(device_id: str) -> dict:
    return {
        "schema_version": 1,
        "device_id": device_id,
        "collected_at": "2026-10-15T14:55:00Z",
        "agent_version": "0.3.0",
        "host": {
            "hostname": "WS-A",
            "domain": "CORP",
            "os": {"caption": "Microsoft Windows 11 Pro"},
        },
        "hardware": {
            "cpu": {"name": "CPU", "cores": 4, "logical": 8},
            "ram_bytes": 8_000_000_000,
            "disks": [{"model": "SSD-A", "size_bytes": 512_000_000_000}],
            "volumes": [
                {"letter": "C:", "size_bytes": 500_000_000_000, "free_bytes": 200_000_000_000}
            ],
        },
        "network": {
            "nics": [
                {
                    "name": "Ethernet",
                    "mac": "00:11:22:33:44:55",
                    "ipv4": ["10.0.0.10"],
                    "dhcp": True,
                }
            ]
        },
        "users": {"logged_on": ["CORP\\alice"], "last_interactive": "CORP\\alice"},
        "collector_errors": [],
    }


def test_diff_detects_hostname_user_disk_nic_and_free_drop():
    prev = _base_inventory("d1")
    cur = _base_inventory("d1")
    cur["host"]["hostname"] = "WS-B"
    cur["host"]["domain"] = "ACME"
    cur["users"]["logged_on"] = ["CORP\\bob"]
    cur["users"]["last_interactive"] = "CORP\\bob"
    cur["hardware"]["disks"] = [
        {"model": "SSD-A", "size_bytes": 512_000_000_000},
        {"model": "SSD-B", "size_bytes": 256_000_000_000},
    ]
    cur["hardware"]["volumes"][0]["free_bytes"] = 50_000_000_000  # large drop
    cur["network"]["nics"][0]["ipv4"] = ["10.0.0.11"]

    events = diff_inventory_snapshots(prev, cur)
    types = {e["type"] for e in events}
    assert "hostname_change" in types
    assert "domain_change" in types
    assert "logged_on_change" in types
    assert "last_interactive_change" in types
    assert "disk_added" in types
    assert "volume_free_drop" in types
    assert "nic_ipv4_change" in types


def test_diff_first_snapshot_no_events():
    assert diff_inventory_snapshots(None, _base_inventory("d1")) == []


def test_normalize_tags_dedupes():
    assert normalize_tags("Prod, prod, finance") == ["Prod", "finance"]
    assert normalize_tags(["a", "A", "b"]) == ["a", "b"]


def test_silence_ok_and_stale():
    now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    ok = device_silence_status(
        "2026-10-15T11:30:00Z",
        stale_after_seconds=3600,
        now=now,
    )
    assert ok["status"] == "ok"
    stale = device_silence_status(
        (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        stale_after_seconds=3600,
        now=now,
    )
    assert stale["status"] == "stale"


def test_inventory_upsert_persists_events(client):
    device_id = "evt-device-1"
    api_key = enroll_device(client, device_id=device_id, hostname="WS-A")
    inv1 = _base_inventory(device_id)
    r1 = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json=inv1,
    )
    assert r1.status_code == 200

    events0 = client.get(
        "/v1/events",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert events0.status_code == 200
    assert events0.json()["events"] == []

    inv2 = _base_inventory(device_id)
    inv2["collected_at"] = "2026-10-15T15:00:00Z"
    inv2["host"]["hostname"] = "WS-RENAMED"
    inv2["users"]["last_interactive"] = "CORP\\carol"
    r2 = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json=inv2,
    )
    assert r2.status_code == 200

    events = client.get(
        "/v1/events",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        params={"device_id": device_id},
    )
    assert events.status_code == 200
    body = events.json()["events"]
    types = {e["type"] for e in body}
    assert "hostname_change" in types
    assert "last_interactive_change" in types
    assert all(e["device_id"] == device_id for e in body)


def test_tag_filter_list_devices_and_policy_match(client):
    d1 = "tag-dev-1"
    d2 = "tag-dev-2"
    enroll_device(client, device_id=d1, hostname="HOST-1")
    enroll_device(client, device_id=d2, hostname="HOST-2")

    put1 = client.put(
        f"/v1/devices/{d1}/tags",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"tags": ["prod", "finance"]},
    )
    assert put1.status_code == 200
    assert put1.json()["tags"] == ["prod", "finance"]

    put2 = client.put(
        f"/v1/devices/{d2}/tags",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"tags": ["lab"]},
    )
    assert put2.status_code == 200

    filtered = client.get(
        "/v1/devices",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        params={"tag": "prod"},
    )
    assert filtered.status_code == 200
    ids = {d["device_id"] for d in filtered.json()["devices"]}
    assert ids == {d1}

    # Policy condition tag equals
    result = compute_effective_config(
        hostname="HOST-1",
        tags=["prod", "finance"],
        policies=[
            {
                "id": 1,
                "name": "prod-hb",
                "enabled": True,
                "priority": 10,
                "conditions": [{"field": "tag", "op": "equals", "value": "prod"}],
                "settings": {"heartbeat_interval_minutes": 3},
            }
        ],
        override=None,
    )
    assert result["settings"]["heartbeat_interval_minutes"] == 3
    assert result["matched_policies"][0]["name"] == "prod-hb"

    miss = compute_effective_config(
        hostname="HOST-2",
        tags=["lab"],
        policies=[
            {
                "id": 1,
                "name": "prod-hb",
                "enabled": True,
                "priority": 10,
                "conditions": [{"field": "tag", "op": "equals", "value": "prod"}],
                "settings": {"heartbeat_interval_minutes": 3},
            }
        ],
        override=None,
    )
    assert miss["matched_policies"] == []
