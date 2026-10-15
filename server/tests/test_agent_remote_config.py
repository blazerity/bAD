"""Policy evaluation, override precedence, agent config pull."""

from __future__ import annotations

from bad_server.agent_config import (
    DEFAULT_AGENT_SETTINGS,
    compute_effective_config,
    sanitize_settings,
)
from helpers import ADMIN_TOKEN, enroll_device


def test_sanitize_settings_drops_unsafe_keys():
    cleaned = sanitize_settings(
        {
            "inventory_interval_hours": 3,
            "server_url": "https://evil.example",
            "api_key": "steal-me",
            "update_enabled": "false",
            "collect_software": "true",
            "collect_hardware": 0,
            "heartbeat_interval_minutes": 0,
        }
    )
    assert cleaned == {
        "inventory_interval_hours": 3,
        "update_enabled": False,
        "collect_software": True,
        "collect_hardware": False,
    }


def test_compute_effective_precedence_defaults_policy_override():
    policies = [
        {
            "id": 1,
            "name": "corp-hosts",
            "enabled": True,
            "priority": 10,
            "conditions": [{"field": "hostname", "op": "contains", "value": "CORP"}],
            "settings": {"heartbeat_interval_minutes": 5, "inventory_interval_hours": 2},
        },
        {
            "id": 2,
            "name": "later-wins",
            "enabled": True,
            "priority": 20,
            "conditions": [{"field": "domain", "op": "equals", "value": "ACME"}],
            "settings": {"heartbeat_interval_minutes": 7},
        },
    ]
    result = compute_effective_config(
        hostname="CORP-LAP-01",
        meta={"os": "Windows 11 Pro"},
        inventory_payload={
            "host": {
                "hostname": "CORP-LAP-01",
                "domain": "ACME",
                "os": {"caption": "Microsoft Windows 11 Pro"},
            }
        },
        policies=policies,
        override={"update_enabled": False, "heartbeat_interval_minutes": 1},
    )
    assert result["settings"]["inventory_interval_hours"] == 2
    assert result["settings"]["heartbeat_interval_minutes"] == 1  # override wins
    assert result["settings"]["update_enabled"] is False
    assert result["settings"]["collect_hardware"] is True
    assert result["settings"]["collect_users"] is True
    assert result["settings"]["collect_software"] is False
    assert result["settings"]["update_check_interval_hours"] == (
        DEFAULT_AGENT_SETTINGS["update_check_interval_hours"]
    )
    assert result["has_override"] is True
    assert [p["name"] for p in result["matched_policies"]] == ["corp-hosts", "later-wins"]


def test_compute_effective_collector_toggles_override():
    result = compute_effective_config(
        hostname="X",
        policies=[],
        override={
            "collect_hardware": False,
            "collect_users": False,
            "collect_software": True,
        },
    )
    assert result["settings"]["collect_hardware"] is False
    assert result["settings"]["collect_users"] is False
    assert result["settings"]["collect_software"] is True


def test_compute_effective_disabled_and_nonmatching_ignored():
    policies = [
        {
            "id": 1,
            "name": "off",
            "enabled": False,
            "priority": 1,
            "conditions": [{"field": "hostname", "op": "equals", "value": "X"}],
            "settings": {"inventory_interval_hours": 1},
        },
        {
            "id": 2,
            "name": "miss",
            "enabled": True,
            "priority": 2,
            "conditions": [{"field": "os_caption", "op": "contains", "value": "Linux"}],
            "settings": {"inventory_interval_hours": 2},
        },
    ]
    result = compute_effective_config(
        hostname="X",
        inventory_payload={"host": {"os": {"caption": "Windows 10"}}},
        policies=policies,
        override=None,
    )
    assert result["settings"] == DEFAULT_AGENT_SETTINGS
    assert result["matched_policies"] == []


def test_agent_config_requires_api_key(client):
    r = client.get("/v1/agent/config")
    assert r.status_code == 401


def test_agent_config_and_heartbeat_piggyback(client):
    api_key = enroll_device(client, device_id="cfg-dev-1", hostname="CORP-PC")
    # Seed inventory so domain/os are available for policies
    inv = client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "schema_version": 1,
            "device_id": "cfg-dev-1",
            "agent_version": "0.7.0",
            "collected_at": "2026-10-15T12:00:00Z",
            "host": {
                "hostname": "CORP-PC",
                "domain": "CORP",
                "os": {"caption": "Microsoft Windows 11 Enterprise"},
            },
        },
    )
    assert inv.status_code == 200

    create = client.post(
        "/v1/admin/policies",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={
            "name": "corp-fast-hb",
            "enabled": True,
            "priority": 50,
            "conditions": [{"field": "hostname", "op": "contains", "value": "CORP"}],
            "settings": {"heartbeat_interval_minutes": 3},
        },
    )
    assert create.status_code == 201, create.text
    policy_id = create.json()["policy"]["id"]

    ov = client.put(
        "/v1/admin/devices/cfg-dev-1/config-override",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={"settings": {"update_enabled": False}},
    )
    assert ov.status_code == 200
    assert ov.json()["effective"]["heartbeat_interval_minutes"] == 3
    assert ov.json()["effective"]["update_enabled"] is False

    # Another device must not see this device's override via its own key
    other_key = enroll_device(client, device_id="cfg-dev-2", hostname="OTHER")
    other = client.get(
        "/v1/agent/config",
        headers={"Authorization": f"Bearer {other_key}"},
    )
    assert other.status_code == 200
    assert other.json()["device_id"] == "cfg-dev-2"
    assert other.json()["settings"]["heartbeat_interval_minutes"] == 15
    assert other.json()["settings"]["update_enabled"] is True

    mine = client.get(
        "/v1/agent/config",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert mine.status_code == 200
    body = mine.json()
    assert body["device_id"] == "cfg-dev-1"
    assert body["settings"]["heartbeat_interval_minutes"] == 3
    assert body["settings"]["update_enabled"] is False
    version = body["version"]
    assert version

    hb = client.post(
        "/v1/heartbeat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "device_id": "cfg-dev-1",
            "agent_version": "0.7.0",
            "config_version": "stale",
            "last_inventory_ok": True,
            "agent_uptime_seconds": 120,
            "system_drive_free_bytes": 50_000_000,
        },
    )
    assert hb.status_code == 200
    hb_body = hb.json()
    assert hb_body["config_version"] == version
    assert hb_body["config"]["settings"]["heartbeat_interval_minutes"] == 3

    detail_after_hb = client.get(
        "/v1/devices/cfg-dev-1",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail_after_hb.status_code == 200
    meta = detail_after_hb.json().get("meta") or {}
    assert meta.get("last_inventory_ok") is True
    assert meta.get("agent_uptime_seconds") == 120
    assert meta.get("system_drive_free_bytes") == 50_000_000

    hb2 = client.post(
        "/v1/heartbeat",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "device_id": "cfg-dev-1",
            "agent_version": "0.7.0",
            "config_version": version,
        },
    )
    assert hb2.status_code == 200
    assert "config" not in hb2.json()
    assert hb2.json()["config_version"] == version

    # Admin detail endpoint
    detail = client.get(
        f"/v1/admin/devices/cfg-dev-1/config",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail.status_code == 200
    assert detail.json()["has_override"] is True
    assert any(p["id"] == policy_id for p in detail.json()["matched_policies"])

    # Clear override
    cleared = client.delete(
        "/v1/admin/devices/cfg-dev-1/config-override",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert cleared.status_code == 200
    assert cleared.json()["effective"]["update_enabled"] is True

    deleted = client.delete(
        f"/v1/admin/policies/{policy_id}",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert deleted.status_code == 200


def test_admin_policy_rejects_unsafe_settings(client):
    r = client.post(
        "/v1/admin/policies",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json={
            "name": "bad",
            "conditions": [{"field": "hostname", "op": "equals", "value": "x"}],
            "settings": {"server_url": "https://evil"},
        },
    )
    assert r.status_code == 422


def test_web_policies_and_device_override(client):
    api_key = enroll_device(client, device_id="web-cfg-1", hostname="WEBHOST")
    assert api_key
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert login.status_code in (302, 303)

    page = client.get("/settings/policies")
    assert page.status_code == 200
    assert "Agent policies" in page.text

    created = client.post(
        "/settings/policies",
        data={
            "name": "web-policy",
            "enabled": "1",
            "priority": "40",
            "cond_field": "hostname",
            "cond_op": "contains",
            "cond_value": "WEB",
            "heartbeat_interval_minutes": "4",
            "update_enabled": "",
        },
        follow_redirects=False,
    )
    assert created.status_code == 200
    assert "Policy created" in created.text

    detail = client.get("/devices/web-cfg-1")
    assert detail.status_code == 200
    assert "Effective agent config" in detail.text

    saved = client.post(
        "/devices/web-cfg-1/config-override",
        data={
            "inventory_interval_hours": "8",
            "heartbeat_interval_minutes": "",
            "update_check_interval_hours": "",
            "update_enabled": "false",
            "collect_software": "true",
            "collect_hardware": "",
            "collect_users": "",
        },
    )
    assert saved.status_code == 200
    assert "Manual override saved" in saved.text
    assert ">8<" in saved.text or "inventory_interval_hours</dt><dd class=\"mono\">8" in saved.text
    assert "collect_software</dt><dd class=\"mono\">True" in saved.text
