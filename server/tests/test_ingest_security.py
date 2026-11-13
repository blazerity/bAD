"""Приём снимка: одноразовый код и толстый снимок."""

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


def _snap_count(client: TestClient, bad_id: str) -> int:
    db = client.app.state.db
    with db.connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM inventory_snapshots WHERE bad_id = %s",
            (bad_id,),
        ).fetchone()
    return int(row["n"])


def _bad_id(prefix: str) -> str:
    return "BAD-" + uuid.uuid5(uuid.NAMESPACE_URL, f"{prefix}-{uuid.uuid4()}").hex[:8].upper()


def test_one_time_code_burns() -> None:
    bad_id = _bad_id("granted-pc")
    with TestClient(create_app()) as client:
        grant = client.post(
            "/v1/enrollment-grants",
            headers={"Authorization": "Bearer test-admin-token-change-me-please-32b"},
            json={"bad_id": bad_id},
        )
        assert grant.status_code == 200, grant.text
        code = grant.json()["code"]
        first = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"bad_id": bad_id},
        )
        assert first.status_code == 200, first.text
        second = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"bad_id": bad_id},
        )
        assert second.status_code == 401, second.text


def test_unsigned_snapshot_and_signing_key_once() -> None:
    bad_id = _bad_id("old-sign")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"bad_id": bad_id, "hostname": "OLD"},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        db = client.app.state.db
        with db.connection() as conn:
            conn.execute(
                """
                UPDATE devices
                SET signing_pubkey = NULL, signing_key_fingerprint = NULL
                WHERE bad_id = %s
                """,
                (bad_id,),
            )
        inv = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "bad_id": bad_id,
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

    bad_id = _bad_id("signed")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"bad_id": bad_id, "hostname": "SIGNED"},
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
                "SELECT signing_key_fingerprint FROM devices WHERE bad_id = %s",
                (bad_id,),
            ).fetchone()
        assert row["signing_key_fingerprint"] == fingerprint
        payload = {
            "schema_version": 2,
            "bad_id": bad_id,
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


def _fingerprint(label: str) -> str:
    import hashlib

    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_enrollment_request_waits_for_admin() -> None:
    import base64

    from bad_server.crypto_util import encrypt_secret
    from bad_server.security import generate_token, hash_secret, new_device_signing_key

    body = {
        "hostname": "NEW-PC",
        "ip": "10.1.1.5",
        "serial": _bad_id("sn"),
        "fingerprint": _fingerprint("owner"),
    }
    with TestClient(create_app()) as client:
        first = client.post("/v1/enrollment-requests", json=body)
        assert first.status_code == 200, first.text
        assert first.json() == {"status": "pending"}
        assert "api_key" not in first.json()
        again = client.post("/v1/enrollment-requests", json=body)
        assert again.json() == {"status": "pending"}
        db = client.app.state.db
        with db.connection() as conn:
            row = conn.execute(
                "SELECT id FROM enrollment_requests WHERE serial = %s",
                (body["serial"],),
            ).fetchone()
        bad_id = "req-" + generate_token("")[:12]
        api_key = generate_token("bad_ak_")
        private, public, fingerprint = new_device_signing_key()
        data_key = client.app.state.data_key
        db.upsert_device_on_enroll(
            bad_id=bad_id,
            hostname=body["hostname"],
            api_key_hash=hash_secret(api_key),
            agent_version=None,
            signing_pubkey=public,
            signing_key_fingerprint=fingerprint,
        )
        assert db.mark_enrollment_request_approved(
            row["id"],
            bad_id,
            encrypt_secret(data_key, api_key),
            encrypt_secret(data_key, private),
        )
        claimed = client.post("/v1/enrollment-requests", json=body)
        assert claimed.status_code == 200, claimed.text
        assert claimed.json()["api_key"] == api_key
        assert len(base64.b64decode(claimed.json()["signing_key"])) == 32
        repeat = client.post("/v1/enrollment-requests", json=body)
        assert "api_key" not in repeat.json()
        assert "signing_key" not in repeat.json()


def test_stranger_same_serial_gets_no_key() -> None:
    from bad_server.crypto_util import encrypt_secret
    from bad_server.security import generate_token, hash_secret, new_device_signing_key

    serial = _bad_id("shared-sn")
    owner = {
        "hostname": "OWNER-PC",
        "ip": "10.1.1.5",
        "serial": serial,
        "fingerprint": _fingerprint("owner-" + serial),
    }
    stranger = {
        "hostname": "STRANGER-PC",
        "ip": "10.9.9.9",
        "serial": serial,
        "fingerprint": _fingerprint("stranger-" + serial),
    }
    with TestClient(create_app()) as client:
        assert client.post("/v1/enrollment-requests", json=owner).json()["status"] == "pending"
        assert client.post("/v1/enrollment-requests", json=stranger).json()["status"] == "pending"
        db = client.app.state.db
        with db.connection() as conn:
            owner_row = conn.execute(
                "SELECT hostname FROM enrollment_requests WHERE id = %s",
                (owner["fingerprint"],),
            ).fetchone()
        assert owner_row["hostname"] == "OWNER-PC"
        bad_id = "req-" + generate_token("")[:12]
        api_key = generate_token("bad_ak_")
        private, public, fingerprint = new_device_signing_key()
        data_key = client.app.state.data_key
        db.upsert_device_on_enroll(
            bad_id=bad_id,
            hostname=owner["hostname"],
            api_key_hash=hash_secret(api_key),
            agent_version=None,
            signing_pubkey=public,
            signing_key_fingerprint=fingerprint,
        )
        assert db.mark_enrollment_request_approved(
            owner["fingerprint"],
            bad_id,
            encrypt_secret(data_key, api_key),
            encrypt_secret(data_key, private),
        )
        stolen = client.post("/v1/enrollment-requests", json=stranger)
        assert stolen.status_code == 200, stolen.text
        assert "api_key" not in stolen.json()
        assert "signing_key" not in stolen.json()
        with db.connection() as conn:
            card = conn.execute(
                "SELECT hostname FROM devices WHERE bad_id = %s",
                (bad_id,),
            ).fetchone()
        assert card["hostname"] == "OWNER-PC"
        claimed = client.post("/v1/enrollment-requests", json=owner)
        assert claimed.json()["api_key"] == api_key


def test_pending_queue_expires_and_caps() -> None:
    from bad_server.db import PENDING_ENROLLMENT_CAP, utc_now

    fresh = _fingerprint("queue-fresh")
    with TestClient(create_app()) as client:
        db = client.app.state.db
        now = utc_now()
        with db.connection() as conn:
            conn.execute("DELETE FROM enrollment_requests WHERE status = 'pending'")
            conn.execute(
                """
                INSERT INTO enrollment_requests(
                  id, hostname, ip, serial, created_at, status
                ) VALUES (%s, 'OLD', '', '', '2000-01-01T00:00:00Z', 'pending')
                """,
                ("a" * 64,),
            )
            for i in range(PENDING_ENROLLMENT_CAP - 1):
                conn.execute(
                    """
                    INSERT INTO enrollment_requests(
                      id, hostname, ip, serial, created_at, status
                    ) VALUES (%s, 'Q', '', '', %s, 'pending')
                    """,
                    (f"{i:064x}", now),
                )
        opened = client.post(
            "/v1/enrollment-requests",
            json={
                "hostname": "NEW",
                "ip": "",
                "serial": "To Be Filled By O.E.M.",
                "fingerprint": fresh,
            },
        )
        assert opened.json()["status"] == "pending"
        with db.connection() as conn:
            gone = conn.execute(
                "SELECT id FROM enrollment_requests WHERE id = %s",
                ("a" * 64,),
            ).fetchone()
            stored = conn.execute(
                "SELECT serial FROM enrollment_requests WHERE id = %s",
                (fresh,),
            ).fetchone()
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM enrollment_requests WHERE status = 'pending'"
            ).fetchone()
        assert gone is None
        assert stored["serial"] == ""
        assert int(pending["n"]) == PENDING_ENROLLMENT_CAP
        blocked = client.post(
            "/v1/enrollment-requests",
            json={
                "hostname": "OVERFLOW",
                "ip": "",
                "serial": "SN-OVERFLOW",
                "fingerprint": _fingerprint("overflow"),
            },
        )
        assert blocked.json() == {"status": "busy"}
        with db.connection() as conn:
            extra = conn.execute(
                "SELECT id FROM enrollment_requests WHERE id = %s",
                (_fingerprint("overflow"),),
            ).fetchone()
        assert extra is None


def test_unbound_install_code_once() -> None:
    from bad_server.security import enrollment_code_hash, generate_token

    bad_id = _bad_id("install")
    code = generate_token("bad_ot_")
    with TestClient(create_app()) as client:
        client.app.state.db.create_enrollment_grant("", enrollment_code_hash(code))
        first = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"bad_id": bad_id, "hostname": "INSTALL"},
        )
        assert first.status_code == 200, first.text
        assert first.json()["api_key"]
        second = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"bad_id": _bad_id("install2")},
        )
        assert second.status_code == 401, second.text


def test_panel_flags_override_defaults() -> None:
    bad_id = _bad_id("flagged")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"bad_id": bad_id},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        db = client.app.state.db
        db.set_site_secret("require_inventory_signature", "1")
        try:
            denied = client.post(
                "/v1/inventory",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"schema_version": 2, "bad_id": bad_id},
            )
            assert denied.status_code == 401, denied.text
        finally:
            db.set_site_secret("require_inventory_signature", "0")
        ok = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"schema_version": 2, "bad_id": bad_id},
        )
        assert ok.status_code == 200, ok.text
        db.set_site_secret("allow_shared_enrollment", "0")
        try:
            blocked = client.post(
                "/v1/enroll",
                headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
                json={"bad_id": _bad_id("shared-off")},
            )
            assert blocked.status_code == 401, blocked.text
        finally:
            db.set_site_secret("allow_shared_enrollment", "1")


def test_fat_inventory_does_not_write() -> None:
    bad_id = _bad_id("fat-pc")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"bad_id": bad_id},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        programs = [{"name": f"pkg-{i}"} for i in range(601)]
        inv = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "bad_id": bad_id,
                "software": {"programs": programs},
            },
        )
        assert inv.status_code == 400, inv.text
        assert _snap_count(client, bad_id) == 0


def test_agent_report_html_is_enrolled_card_without_admin() -> None:
    bad_id = _bad_id("report-pc")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"bad_id": bad_id, "hostname": "STORED-NAME"},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        bare = client.post(
            "/v1/agent/report.html",
            json={"schema_version": 2, "bad_id": bad_id},
        )
        assert bare.status_code == 401, bare.text
        report = client.post(
            "/v1/agent/report.html",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "bad_id": bad_id,
                "agent_version": "9.9.9-report",
                "host": {"hostname": "WS-REPORT-HOST"},
                "hardware": {"model": "Model-XYZ-Report", "chassis_type": "desktop"},
                "software": {"programs": [{"name": "Layout Check", "version": "1"}]},
            },
        )
        assert report.status_code == 200, report.text
        assert "text/html" in report.headers["content-type"]
        body = report.text
        assert "WS-REPORT-HOST" in body
        assert "Model-XYZ-Report" in body
        assert "9.9.9-report" in body
        assert "<style>" in body
        assert ".device-panel" in body
        assert 'href="/static/style.css' not in body
        assert "Снять агент" not in body
        assert "В архив" not in body
        assert "Выпустить новый ключ" not in body
        assert "Создать или изменить политики" not in body
        assert "Недавние события" not in body
        assert "<a " not in body
        assert "<form" not in body
        assert "<button" not in body
        assert ">Версия<" in body
        assert ">Version<" not in body
        assert _snap_count(client, bad_id) == 0
