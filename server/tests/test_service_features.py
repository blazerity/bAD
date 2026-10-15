"""Service basics 0.8.0: revoke/archive/delete, retention, mail, backup, search."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from bad_server.backup import backup_filename, run_daily_backup, utc_today
from bad_server.inventory_events import diff_inventory_snapshots
from bad_server.smtp_mail import (
    DEFAULT_NOTIFY,
    filter_events_for_mail,
    parse_notify_flags,
)
from helpers import ADMIN_TOKEN, enroll_device


def _login(client: TestClient):
    return client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )


def test_hardware_diff_events_extended():
    prev = {
        "hardware": {
            "cpu": {"name": "A", "cores": 4, "logical": 8},
            "ram_bytes": 8,
            "serial_number": "S1",
            "model": "M1",
            "disks": [{"model": "SSD", "size_bytes": 100}],
            "ram_modules": [
                {"part_number": "P1", "capacity_bytes": 4, "device_locator": "DIMM1"}
            ],
        }
    }
    cur = {
        "hardware": {
            "cpu": {"name": "B", "cores": 8, "logical": 16},
            "ram_bytes": 16,
            "serial_number": "S2",
            "model": "M2",
            "disks": [{"model": "NVME", "size_bytes": 200}],
            "ram_modules": [
                {"part_number": "P2", "capacity_bytes": 8, "device_locator": "DIMM1"}
            ],
        }
    }
    types = {e["type"] for e in diff_inventory_snapshots(prev, cur)}
    assert "cpu_change" in types
    assert "ram_bytes_change" in types
    assert "serial_change" in types
    assert "model_change" in types
    assert "disk_added" in types
    assert "disk_removed" in types
    assert "ram_module_added" in types
    assert "ram_module_removed" in types


def test_notify_flags_defaults_and_filter():
    flags = parse_notify_flags(None)
    assert flags == DEFAULT_NOTIFY
    events = [
        {"type": "cpu_change", "summary": "cpu"},
        {"type": "hostname_change", "summary": "hn"},
        {"type": "domain_change", "summary": "dom"},
    ]
    selected = filter_events_for_mail(events, flags)
    assert {e["type"] for e in selected} == {"cpu_change"}
    flags["hostname"] = True
    selected2 = filter_events_for_mail(events, flags)
    assert "hostname_change" in {e["type"] for e in selected2}


def test_revoke_blocks_agent_and_rotate_restores(client: TestClient):
    device_id = "rev-1"
    key = enroll_device(client, device_id=device_id, hostname="REV-HOST")
    ok = client.post(
        "/v1/heartbeat",
        headers={"Authorization": f"Bearer {key}"},
        json={"device_id": device_id, "agent_version": "0.8.0"},
    )
    assert ok.status_code == 200

    rev = client.post(
        f"/v1/devices/{device_id}/revoke",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert rev.status_code == 200
    blocked = client.post(
        "/v1/heartbeat",
        headers={"Authorization": f"Bearer {key}"},
        json={"device_id": device_id, "agent_version": "0.8.0"},
    )
    assert blocked.status_code == 403
    assert "revoked" in blocked.json()["detail"].lower()

    rotated = client.post(
        f"/v1/devices/{device_id}/rotate-key",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert rotated.status_code == 200
    new_key = rotated.json()["api_key"]
    again = client.post(
        "/v1/heartbeat",
        headers={"Authorization": f"Bearer {new_key}"},
        json={"device_id": device_id, "agent_version": "0.8.0"},
    )
    assert again.status_code == 200


def test_archive_filter_and_delete(client: TestClient):
    d1 = enroll_device(client, device_id="arch-1", hostname="A1")
    enroll_device(client, device_id="arch-2", hostname="A2")
    assert d1

    client.post(
        "/v1/devices/arch-1/archive",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    active = client.get(
        "/v1/devices",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    ).json()
    assert all(d["device_id"] != "arch-1" for d in active["devices"])

    archived = client.get(
        "/v1/devices",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        params={"archived": "true"},
    ).json()
    assert any(d["device_id"] == "arch-1" for d in archived["devices"])

    deleted = client.delete(
        "/v1/devices/arch-1",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert deleted.status_code == 200
    missing = client.get(
        "/v1/devices/arch-1",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert missing.status_code == 404


def test_devices_search_pagination_and_csv(client: TestClient):
    for i in range(3):
        enroll_device(client, device_id=f"pg-{i}", hostname=f"HOST-{i}")
    _login(client)

    listed = client.get(
        "/v1/devices",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        params={"q": "HOST-1", "page_size": 50},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["devices"][0]["hostname"] == "HOST-1"

    page = client.get("/devices?q=HOST-2")
    assert page.status_code == 200
    assert "HOST-2" in page.text

    csv_resp = client.get("/devices/export.csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "device_id" in csv_resp.text
    assert "HOST-0" in csv_resp.text


def test_overview_and_settings_shell(client: TestClient):
    enroll_device(client, device_id="ov-1", hostname="OV")
    _login(client)
    home = client.get("/")
    assert home.status_code == 200
    assert "Обзор" in home.text
    assert "Активных" in home.text

    settings = client.get("/settings", follow_redirects=False)
    assert settings.status_code == 303
    assert settings.headers["location"] == "/settings/ldap"

    mail = client.get("/settings/mail")
    assert mail.status_code == 200
    assert "Почта и уведомления" in mail.text
    assert "Изменение железа" in mail.text
    assert "Параметры" in mail.text

    ret = client.get("/settings/retention")
    assert ret.status_code == 200
    assert "Хранение и очистка" in ret.text

    backups = client.get("/settings/backups")
    assert backups.status_code == 200
    assert "Резервные копии" in backups.text


def test_retention_settings_and_prune(client: TestClient, tmp_path: Path):
    _login(client)
    save = client.post(
        "/settings/retention",
        data={"events_days": "30", "inventory_days": "60"},
    )
    assert save.status_code == 200
    assert "сохранены" in save.text

    from bad_server.db import Database

    # Use the app's db via a known path from env — prune through API-less direct call.
    db_path = Path(client.app.state.db.path)
    db = Database(db_path)
    cfg = db.get_retention_settings()
    assert cfg["events_days"] == 30
    assert cfg["inventory_days"] == 60
    stats = db.prune_expired_data(events_days=30, inventory_days=60)
    assert "events_deleted" in stats


def test_mail_settings_save_notify_flags(client: TestClient):
    _login(client)
    save = client.post(
        "/settings/mail",
        data={
            "enabled": "1",
            "host": "smtp.example.com",
            "port": "587",
            "use_starttls": "1",
            "from_addr": "bad@example.com",
            "to_addrs": "ops@example.com",
            "notify_hardware": "1",
            "notify_enroll": "1",
            # stale/hostname/domain off
        },
    )
    assert save.status_code == 200
    assert "сохранены" in save.text
    row = client.app.state.db.get_smtp_settings()
    flags = parse_notify_flags(row.get("notify_json"))
    assert flags["hardware"] is True
    assert flags["enroll"] is True
    assert flags["stale"] is False
    assert flags["hostname"] is False


def test_ldap_allowed_group_field(client: TestClient):
    _login(client)
    save = client.post(
        "/settings/ldap",
        data={
            "enabled": "1",
            "host": "ldap.example.com",
            "port": "389",
            "bind_dn": "cn=svc,dc=example,dc=com",
            "bind_password": "x",
            "user_search_base": "ou=people,dc=example,dc=com",
            "user_filter_template": "(sAMAccountName={username})",
            "display_name_attr": "cn",
            "default_role": "operator",
            "allowed_group": "bAD-Operators",
        },
    )
    assert save.status_code == 200
    assert "bAD-Operators" in save.text
    row = client.app.state.db.get_ldap_settings()
    assert row["allowed_group"] == "bAD-Operators"


def test_ldap_group_denied_message(client: TestClient):
    client.post("/logout")
    msg = "Нет доступа: пользователь не входит в группу AD «bAD-Operators»"
    with patch("bad_server.web.authenticate_web_user", return_value=(None, msg)):
        r = client.post(
            "/login",
            data={"username": "alice", "password": "secret"},
        )
    assert r.status_code == 401
    assert "Нет доступа" in r.text
    assert "bAD-Operators" in r.text


def test_sqlite_backup_keeps_two_days(client: TestClient, tmp_path: Path):
    db_path = Path(client.app.state.db.path)
    backup_dir = tmp_path / "bk"
    result = run_daily_backup(db_path, backup_dir)
    assert result["ok"] is True
    today = backup_dir / backup_filename(utc_today())
    assert today.is_file()

    # Pretend yesterday already exists; run again should still keep ≤2 files.
    from datetime import timedelta

    yesterday = utc_today() - timedelta(days=1)
    old = backup_dir / backup_filename(yesterday)
    old.write_bytes(today.read_bytes())
    ancient = backup_dir / backup_filename(utc_today() - timedelta(days=5))
    ancient.write_bytes(b"x")
    result2 = run_daily_backup(db_path, backup_dir)
    assert result2["ok"] is True
    names = sorted(p.name for p in backup_dir.glob("bad-*.db"))
    assert ancient.name not in names
    assert len(names) <= 2

    _login(client)
    page = client.get("/settings/backups")
    assert page.status_code == 200
    run = client.post("/settings/backups/run")
    assert run.status_code == 200
    assert "Бэкап записан" in run.text


def test_duplicates_hint_on_detail(client: TestClient):
    enroll_device(client, device_id="dup-a", hostname="SAME-HOST")
    enroll_device(client, device_id="dup-b", hostname="same-host")
    detail = client.get(
        "/v1/devices/dup-a",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert detail.status_code == 200
    dups = detail.json()["duplicates"]["hostname"]
    assert any(x["device_id"] == "dup-b" for x in dups)

    _login(client)
    page = client.get("/devices/dup-a")
    assert page.status_code == 200
    assert "дубликат" in page.text.lower() or "дубли" in page.text.lower()
