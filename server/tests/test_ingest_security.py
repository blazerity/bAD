"""Три случая приёма: старый агент, одноразовый код, толстый снимок."""

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
os.environ.setdefault("BAD_ALLOW_SHARED_ENROLLMENT", "1")
os.environ.setdefault("BAD_REQUIRE_INVENTORY_SIGNATURE", "0")
os.environ.setdefault("BAD_DATA_DIR", "/tmp/bad-ingest-test-data")
os.environ.setdefault("BAD_BACKUP_DIR", "/tmp/bad-ingest-test-backups")

from fastapi.testclient import TestClient

from bad_server.config import get_settings

get_settings.cache_clear()

from bad_server.app import create_app  # noqa: E402


def _snap_count(client: TestClient, device_id: str) -> int:
    db = client.app.state.db
    with db.connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM inventory_snapshots WHERE device_id = ?",
            (device_id,),
        ).fetchone()
    return int(row["n"])


def _device_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def test_old_agent_shared_token_without_signature() -> None:
    device_id = _device_id("legacy-agent")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id, "hostname": "LEGACY"},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        beat = client.post(
            "/v1/heartbeat",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"device_id": device_id},
        )
        assert beat.status_code == 200, beat.text
        inv = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "device_id": device_id,
                "software": {"programs": [{"name": "notepad"}]},
            },
        )
        assert inv.status_code == 200, inv.text
        assert _snap_count(client, device_id) == 1


def test_one_time_code_burns() -> None:
    device_id = _device_id("granted-pc")
    with TestClient(create_app()) as client:
        grant = client.post(
            "/v1/enrollment-grants",
            headers={"Authorization": "Bearer test-admin-token-change-me-please-32b"},
            json={"device_id": device_id},
        )
        assert grant.status_code == 200, grant.text
        code = grant.json()["code"]
        first = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"device_id": device_id},
        )
        assert first.status_code == 200, first.text
        second = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"device_id": device_id},
        )
        assert second.status_code == 401, second.text


def test_unsigned_snapshot_and_signing_key_once() -> None:
    device_id = _device_id("old-sign")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id, "hostname": "OLD"},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        db = client.app.state.db
        with db.connection() as conn:
            conn.execute(
                """
                UPDATE devices
                SET signing_pubkey = NULL, signing_key_fingerprint = NULL
                WHERE device_id = ?
                """,
                (device_id,),
            )
        inv = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "device_id": device_id,
                "software": {"programs": [{"name": "notepad"}]},
            },
        )
        assert inv.status_code == 200, inv.text
        first = client.post(
            "/v1/agent/signing-key",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert first.status_code == 200, first.text
        assert first.json().get("signing_key")
        second = client.post(
            "/v1/agent/signing-key",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert second.status_code == 200, second.text
        assert not second.json().get("signing_key")


def test_inventory_signature_uses_agent_canon() -> None:
    import base64
    import hashlib
    import json

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    device_id = _device_id("signed")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id, "hostname": "SIGNED"},
        )
        assert enrolled.status_code == 200, enrolled.text
        secret = enrolled.json()["signing_key"]
        raw_private = base64.b64decode(secret)
        assert len(raw_private) == 32
        private = Ed25519PrivateKey.from_private_bytes(raw_private)
        raw_public = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        fingerprint = hashlib.sha256(raw_public).hexdigest()
        assert fingerprint == fingerprint.lower()
        with client.app.state.db.connection() as conn:
            row = conn.execute(
                "SELECT signing_key_fingerprint FROM devices WHERE device_id = ?",
                (device_id,),
            ).fetchone()
        assert row["signing_key_fingerprint"] == fingerprint
        payload = {
            "schema_version": 2,
            "device_id": device_id,
            "software": {"programs": [{"name": "блокнот"}]},
        }
        canon = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        signature = base64.b64encode(private.sign(canon)).decode("ascii")
        ok = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {enrolled.json()['api_key']}"},
            json={**payload, "signature": signature},
        )
        assert ok.status_code == 200, ok.text
        spaced = json.dumps(payload, sort_keys=True).encode("utf-8")
        bad = base64.b64encode(private.sign(spaced)).decode("ascii")
        denied = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {enrolled.json()['api_key']}"},
            json={**payload, "signature": bad},
        )
        assert denied.status_code == 401, denied.text


def test_fat_inventory_does_not_write() -> None:
    device_id = _device_id("fat-pc")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        programs = [{"name": f"pkg-{i}"} for i in range(601)]
        inv = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "device_id": device_id,
                "software": {"programs": programs},
            },
        )
        assert inv.status_code == 400, inv.text
        assert _snap_count(client, device_id) == 0
