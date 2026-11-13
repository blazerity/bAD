"""Вторая карточка, если SMBIOS UUID снимка чужой. На машине Alex не запускать."""

from __future__ import annotations

import base64
import json
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

_ADMIN = {"Authorization": "Bearer test-admin-token-change-me-please-32b"}
_UUID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_UUID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _device_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _grant(client: TestClient, device_id: str) -> str:
    grant = client.post(
        "/v1/enrollment-grants",
        headers=_ADMIN,
        json={"device_id": device_id},
    )
    assert grant.status_code == 200, grant.text
    return grant.json()["code"]


def _enroll(client: TestClient, device_id: str, *, current: str | None = None) -> dict:
    code = _grant(client, device_id)
    body: dict = {"device_id": device_id, "hostname": "ENROLL"}
    if current is not None:
        body["current_api_key"] = current
    enrolled = client.post(
        "/v1/enroll",
        headers={"Authorization": f"Bearer {code}"},
        json=body,
    )
    assert enrolled.status_code == 200, enrolled.text
    return enrolled.json()


def _inventory(client: TestClient, api_key: str, body: dict):
    return client.post(
        "/v1/inventory",
        headers={"Authorization": f"Bearer {api_key}"},
        json=body,
    )


def _snap(device_id: str, smbios: str | None, hostname: str) -> dict:
    hardware = {} if smbios is None else {"smbios_uuid": smbios}
    return {
        "schema_version": 2,
        "device_id": device_id,
        "host": {"hostname": hostname},
        "hardware": hardware,
    }


def _row(client: TestClient, device_id: str) -> dict:
    db = client.app.state.db
    with db.connection() as conn:
        row = conn.execute(
            """
            SELECT hostname, last_seen_at, meta_json, signing_pubkey, signing_key_fingerprint
            FROM devices WHERE device_id = ?
            """,
            (device_id,),
        ).fetchone()
    assert row is not None
    return dict(row)


def _snap_count(client: TestClient, device_id: str) -> int:
    db = client.app.state.db
    with db.connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM inventory_snapshots WHERE device_id = ?",
            (device_id,),
        ).fetchone()
    return int(row["n"])


def _event_count(client: TestClient, device_id: str) -> int:
    db = client.app.state.db
    with db.connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM device_events WHERE device_id = ?",
            (device_id,),
        ).fetchone()
    return int(row["n"])


def _children(client: TestClient, parent_id: str) -> list[str]:
    db = client.app.state.db
    with db.connection() as conn:
        rows = conn.execute("SELECT device_id, meta_json FROM devices").fetchall()
    found = []
    for row in rows:
        try:
            meta = json.loads(row["meta_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(meta, dict) and meta.get("split_from") == parent_id:
            found.append(row["device_id"])
    return found


def test_foreign_uuid_opens_second_card() -> None:
    device_id = _device_id("clone")
    with TestClient(create_app()) as client:
        enrolled = _enroll(client, device_id)
        api_key = enrolled["api_key"]
        first = _inventory(client, api_key, _snap(device_id, _UUID_A, "ALPHA"))
        assert first.status_code == 200, first.text
        assert "api_key" not in first.json()
        assert "device_id" not in first.json()
        before = _row(client, device_id)
        events_before = _event_count(client, device_id)

        second = _inventory(client, api_key, _snap(device_id, _UUID_B, "BETA"))
        assert second.status_code == 200, second.text
        body = second.json()
        assert body["status"] == "ok"
        child_id = body["device_id"]
        child_key = body["api_key"]
        assert child_id != device_id
        assert child_key and child_key != api_key
        assert "signing_key" not in body

        after = _row(client, device_id)
        assert after["hostname"] == before["hostname"] == "ALPHA"
        assert after["last_seen_at"] == before["last_seen_at"]
        assert after["meta_json"] == before["meta_json"]
        assert _event_count(client, device_id) == events_before
        assert _snap_count(client, device_id) == 1
        assert _snap_count(client, child_id) == 1
        assert _event_count(client, child_id) == 0
        child = _row(client, child_id)
        assert child["hostname"] == "BETA"
        assert json.loads(child["meta_json"])["split_from"] == device_id
        assert child["signing_pubkey"] == after["signing_pubkey"]
        assert child["signing_key_fingerprint"] == after["signing_key_fingerprint"]
        assert _children(client, device_id) == [child_id]


def test_empty_or_same_uuid_stays_on_old_card() -> None:
    device_id = _device_id("same")
    with TestClient(create_app()) as client:
        api_key = _enroll(client, device_id)["api_key"]
        same = _inventory(client, api_key, _snap(device_id, _UUID_A, "ALPHA"))
        assert same.status_code == 200, same.text
        again = _inventory(client, api_key, _snap(device_id, _UUID_A, "ALPHA-2"))
        assert again.status_code == 200, again.text
        assert "api_key" not in again.json()
        assert _snap_count(client, device_id) == 2
        assert _children(client, device_id) == []

        blank = _inventory(client, api_key, _snap(device_id, "", "ALPHA-3"))
        assert blank.status_code == 200, blank.text
        assert "api_key" not in blank.json()
        assert _snap_count(client, device_id) == 3

        zeros = _inventory(
            client,
            api_key,
            _snap(device_id, "00000000-0000-0000-0000-000000000000", "ALPHA-4"),
        )
        assert zeros.status_code == 200, zeros.text
        assert "api_key" not in zeros.json()
        assert _children(client, device_id) == []

    fresh = _device_id("empty-first")
    with TestClient(create_app()) as client:
        api_key = _enroll(client, fresh)["api_key"]
        first = _inventory(client, api_key, _snap(fresh, None, "PLAIN"))
        assert first.status_code == 200, first.text
        second = _inventory(client, api_key, _snap(fresh, _UUID_B, "PLAIN-2"))
        assert second.status_code == 200, second.text
        assert "api_key" not in second.json()
        assert _snap_count(client, fresh) == 2
        assert _children(client, fresh) == []


def test_repeat_foreign_uuid_reuses_the_same_card() -> None:
    device_id = _device_id("repeat")
    with TestClient(create_app()) as client:
        api_key = _enroll(client, device_id)["api_key"]
        assert _inventory(client, api_key, _snap(device_id, _UUID_A, "ALPHA")).status_code == 200
        first = _inventory(client, api_key, _snap(device_id, _UUID_B, "BETA"))
        assert first.status_code == 200, first.text
        child_id = first.json()["device_id"]
        child_key = first.json()["api_key"]
        second = _inventory(client, api_key, _snap(device_id, _UUID_B, "BETA-2"))
        assert second.status_code == 200, second.text
        assert second.json()["device_id"] == child_id
        assert second.json()["api_key"] == child_key
        assert _children(client, device_id) == [child_id]
        assert _snap_count(client, device_id) == 1
        assert _snap_count(client, child_id) == 2
        assert _row(client, device_id)["hostname"] == "ALPHA"


def test_reenroll_same_device_does_not_split() -> None:
    device_id = _device_id("reenroll")
    with TestClient(create_app()) as client:
        first = _enroll(client, device_id)
        api_key = first["api_key"]
        denied = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {_grant(client, device_id)}"},
            json={"device_id": device_id, "hostname": "ENROLL"},
        )
        assert denied.status_code == 409, denied.text
        assert _children(client, device_id) == []

        again = _enroll(client, device_id, current=api_key)
        assert again["device_id"] == device_id
        assert again["api_key"] != api_key
        assert _children(client, device_id) == []
        stale = _inventory(client, api_key, _snap(device_id, _UUID_A, "OLD-KEY"))
        assert stale.status_code == 401, stale.text
        fresh = _inventory(client, again["api_key"], _snap(device_id, _UUID_A, "NEW-KEY"))
        assert fresh.status_code == 200, fresh.text
        assert "api_key" not in fresh.json()
        assert _snap_count(client, device_id) == 1
        assert _children(client, device_id) == []


def test_signature_still_gates_the_split() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    device_id = _device_id("signed-clone")
    with TestClient(create_app()) as client:
        enrolled = _enroll(client, device_id)
        secret = enrolled["signing_key"]
        private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(secret))
        api_key = enrolled["api_key"]
        assert _inventory(client, api_key, _snap(device_id, _UUID_A, "ALPHA")).status_code == 200

        payload = _snap(device_id, _UUID_B, "BETA")
        canon = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        signature = base64.b64encode(private.sign(canon)).decode("ascii")
        spaced = json.dumps(payload, sort_keys=True).encode("utf-8")
        bad = base64.b64encode(private.sign(spaced)).decode("ascii")
        denied = _inventory(client, api_key, {**payload, "signature": bad})
        assert denied.status_code == 401, denied.text
        assert _children(client, device_id) == []
        assert _snap_count(client, device_id) == 1

        accepted = _inventory(client, api_key, {**payload, "signature": signature})
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["device_id"] != device_id
