"""Пустые пункты меню карточки. На машине Alex не запускать."""

from __future__ import annotations

import os
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
from bad_server.sessions import WebUser  # noqa: E402
from bad_server.web import (  # noqa: E402
    _device_config_context,
    _device_inventory_nav,
    render_device_report,
    templates,
)

_ADMIN = {"Authorization": "Bearer test-admin-token-change-me-please-32b"}
_EMPTY_TITLES = [
    "Операционная система",
    "Процессор",
    "Материнская плата",
    "Память",
    "Видео",
    "Корпус",
    "Накопители",
    "Мониторы",
    "Батарея",
    "Сеть",
    "ПО",
    "Безопасность",
    "Минидампы BSOD",
]


def _bad_id() -> str:
    return "BAD-" + uuid.uuid4().hex[:8].upper()


def _enroll(client: TestClient, bad_id: str) -> None:
    grant = client.post(
        "/v1/enrollment-grants",
        headers=_ADMIN,
        json={"bad_id": bad_id},
    )
    assert grant.status_code == 200, grant.text
    enrolled = client.post(
        "/v1/enroll",
        headers={"Authorization": f"Bearer {grant.json()['code']}"},
        json={"bad_id": bad_id, "hostname": "CARD"},
    )
    assert enrolled.status_code == 200, enrolled.text


def _user() -> WebUser:
    return WebUser(username="admin", role="admin", source="local")


def _html(ctx: dict) -> str:
    return templates.get_template("device_detail.html").render(
        {**ctx, "csrf_token": "t", "request": None}
    )


def _panel(html: str, panel_id: str) -> str:
    marker = f'data-device-panel="{panel_id}"'
    start = html.find(marker)
    assert start >= 0, panel_id
    nxt = html.find('data-device-panel="', start + len(marker))
    return html[start : nxt if nxt >= 0 else None]


def test_card_without_snapshot_keeps_empty_sections() -> None:
    bad_id = _bad_id()
    with TestClient(create_app()) as client:
        _enroll(client, bad_id)
        ctx = _device_config_context(
            client.app.state.db,
            bad_id,
            user=_user(),
            settings=get_settings(),
            active_view="cpu",
            keep_empty_sections=True,
        )
    assert ctx is not None
    titles = [item["title"] for item in ctx["inventory_nav"]]
    for title in _EMPTY_TITLES:
        assert title in titles
    assert "Ошибки сбора" not in titles
    cpu = next(item for item in ctx["inventory_nav"] if item["id"] == "cpu")
    assert cpu["lines"] == []
    assert ctx["active_view"] == "cpu"
    html = _html(ctx)
    assert "Снимка inventory пока нет." in html
    assert "данных не получено" in _panel(html, "cpu")
    assert "Ошибки сбора" not in html


def test_gpu_panel_unchanged_when_present() -> None:
    bad_id = _bad_id()
    payload = {
        "schema_version": 2,
        "bad_id": bad_id,
        "hardware": {"gpus": [{"name": "Intel UHD"}]},
    }
    with TestClient(create_app()) as client:
        _enroll(client, bad_id)
        ctx = _device_config_context(
            client.app.state.db,
            bad_id,
            user=_user(),
            settings=get_settings(),
            active_view="gpu",
            inventory_payload=payload,
            keep_empty_sections=True,
        )
    assert ctx is not None
    gpu = next(item for item in ctx["inventory_nav"] if item["id"] == "gpu")
    assert gpu["lines"] == ["Intel UHD"]
    assert "данных не получено" not in _panel(_html(ctx), "gpu")
    assert "Intel UHD" in _panel(_html(ctx), "gpu")


def test_report_does_not_keep_empty_sections() -> None:
    bad_id = _bad_id()
    payload = {
        "schema_version": 2,
        "bad_id": bad_id,
        "hardware": {"gpus": [{"name": "Intel UHD"}]},
    }
    with TestClient(create_app()) as client:
        _enroll(client, bad_id)
        report = render_device_report(
            client.app.state.db, get_settings(), bad_id, payload
        )
    text = report.body.decode("utf-8")
    assert "данных не получено" not in text
    assert "Операционная система" not in text
    assert "Процессор" not in text
    assert "Intel UHD" in text


def test_empty_objects_keep_their_own_lines() -> None:
    items = _device_inventory_nav(
        host_info={},
        hardware_summary={"cpu": {}, "battery": {}},
        network_info=None,
        users_info=None,
        software_info={"programs": None},
        minidumps_info={},
        collector_errors=[],
        security_info={},
        keep_empty=True,
    )
    by_id = {item["id"]: item for item in items}
    assert by_id["os"]["lines"] == ["—"]
    assert by_id["cpu"]["lines"] == ["CPU"]
    assert by_id["battery"]["lines"] == ["батарея"]
    assert by_id["software"]["lines"] == ["недоступно"]
    assert by_id["security"]["lines"] == []
    assert by_id["minidumps"]["lines"] == ["нет дампов"]
    assert "errors" not in by_id
    stored = _device_inventory_nav(
        host_info=None,
        hardware_summary={"disks": [{"model": "SSD"}], "chassis_type": "laptop"},
        network_info=None,
        users_info=None,
        software_info=None,
        minidumps_info=None,
        collector_errors=None,
        keep_empty=True,
    )
    ids = [item["id"] for item in stored]
    assert "storage" in ids
    assert "chassis" not in ids
