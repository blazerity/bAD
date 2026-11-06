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
        "serial": _device_id("sn"),
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
                "SELECT id FROM enrollment_requests WHERE serial = ?",
                (body["serial"],),
            ).fetchone()
        device_id = "req-" + generate_token("")[:12]
        api_key = generate_token("bad_ak_")
        private, public, fingerprint = new_device_signing_key()
        data_key = client.app.state.data_key
        db.upsert_device_on_enroll(
            device_id=device_id,
            hostname=body["hostname"],
            api_key_hash=hash_secret(api_key),
            agent_version=None,
            signing_pubkey=public,
            signing_key_fingerprint=fingerprint,
        )
        assert db.mark_enrollment_request_approved(
            row["id"],
            device_id,
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

    serial = _device_id("shared-sn")
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
                "SELECT hostname FROM enrollment_requests WHERE id = ?",
                (owner["fingerprint"],),
            ).fetchone()
        assert owner_row["hostname"] == "OWNER-PC"
        device_id = "req-" + generate_token("")[:12]
        api_key = generate_token("bad_ak_")
        private, public, fingerprint = new_device_signing_key()
        data_key = client.app.state.data_key
        db.upsert_device_on_enroll(
            device_id=device_id,
            hostname=owner["hostname"],
            api_key_hash=hash_secret(api_key),
            agent_version=None,
            signing_pubkey=public,
            signing_key_fingerprint=fingerprint,
        )
        assert db.mark_enrollment_request_approved(
            owner["fingerprint"],
            device_id,
            encrypt_secret(data_key, api_key),
            encrypt_secret(data_key, private),
        )
        stolen = client.post("/v1/enrollment-requests", json=stranger)
        assert stolen.status_code == 200, stolen.text
        assert "api_key" not in stolen.json()
        assert "signing_key" not in stolen.json()
        with db.connection() as conn:
            card = conn.execute(
                "SELECT hostname FROM devices WHERE device_id = ?",
                (device_id,),
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
                ) VALUES (?, 'OLD', '', '', '2000-01-01T00:00:00Z', 'pending')
                """,
                ("a" * 64,),
            )
            for i in range(PENDING_ENROLLMENT_CAP - 1):
                conn.execute(
                    """
                    INSERT INTO enrollment_requests(
                      id, hostname, ip, serial, created_at, status
                    ) VALUES (?, 'Q', '', '', ?, 'pending')
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
                "SELECT id FROM enrollment_requests WHERE id = ?",
                ("a" * 64,),
            ).fetchone()
            stored = conn.execute(
                "SELECT serial FROM enrollment_requests WHERE id = ?",
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
                "SELECT id FROM enrollment_requests WHERE id = ?",
                (_fingerprint("overflow"),),
            ).fetchone()
        assert extra is None


def test_unbound_install_code_once() -> None:
    from bad_server.security import enrollment_code_hash, generate_token

    device_id = _device_id("install")
    code = generate_token("bad_ot_")
    with TestClient(create_app()) as client:
        client.app.state.db.create_enrollment_grant("", enrollment_code_hash(code))
        first = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"device_id": device_id, "hostname": "INSTALL"},
        )
        assert first.status_code == 200, first.text
        assert first.json()["api_key"]
        second = client.post(
            "/v1/enroll",
            headers={"Authorization": f"Bearer {code}"},
            json={"device_id": _device_id("install2")},
        )
        assert second.status_code == 401, second.text


def test_panel_flags_override_defaults() -> None:
    device_id = _device_id("flagged")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        db = client.app.state.db
        db.set_site_secret("require_inventory_signature", "1")
        try:
            denied = client.post(
                "/v1/inventory",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"schema_version": 2, "device_id": device_id},
            )
            assert denied.status_code == 401, denied.text
        finally:
            db.set_site_secret("require_inventory_signature", "0")
        ok = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"schema_version": 2, "device_id": device_id},
        )
        assert ok.status_code == 200, ok.text
        db.set_site_secret("allow_shared_enrollment", "0")
        try:
            blocked = client.post(
                "/v1/enroll",
                headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
                json={"device_id": _device_id("shared-off")},
            )
            assert blocked.status_code == 401, blocked.text
        finally:
            db.set_site_secret("allow_shared_enrollment", "1")


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


def test_agent_report_html_is_enrolled_card_without_admin() -> None:
    device_id = _device_id("report-pc")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id, "hostname": "STORED-NAME"},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        bare = client.post(
            "/v1/agent/report.html",
            json={"schema_version": 2, "device_id": device_id},
        )
        assert bare.status_code == 401, bare.text
        report = client.post(
            "/v1/agent/report.html",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "device_id": device_id,
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
        assert _snap_count(client, device_id) == 0


def _tiny_minidump() -> bytes:
    import struct

    name = "C:\\Windows\\System32\\drivers\\nvlddmkm.sys".encode("utf-16-le")
    exc_size = 168
    mod_size = 112
    exc_rva = 56
    mod_rva = exc_rva + exc_size
    str_rva = mod_rva + mod_size
    blob = bytearray(b"MDMP")
    blob += struct.pack("<HHIIIIII", 42899, 0, 2, 32, 0, 0, 0, 0)
    blob += struct.pack("<III", 6, exc_size, exc_rva)
    blob += struct.pack("<III", 4, mod_size, mod_rva)
    blob += struct.pack("<II", 1, 0)
    blob += struct.pack("<IIQQII", 0xD1, 0, 0, 0x10001000, 0, 0)
    blob += b"\x00" * (15 * 8)
    blob += struct.pack("<II", 0, 0)
    blob += struct.pack("<I", 1)
    blob += struct.pack("<QIIII", 0x10000000, 0x200000, 0, 0, str_rva)
    blob += b"\x00" * (52 + 8 + 8 + 8 + 8)
    blob += struct.pack("<I", len(name)) + name
    return bytes(blob)


def test_minidump_request_upload_writes_cause_on_card() -> None:
    import re
    import tempfile
    from pathlib import Path

    import bad_server.api as api_mod
    from bad_server.minidump_read import MAX_BYTES, cause_label, dump_name_ok

    assert MAX_BYTES == 8 * 1024 * 1024
    assert cause_label(0x1A, "ntoskrnl.exe") == "память"
    assert cause_label(0xC0000005, "notepad.exe") == "программа"
    assert cause_label(0xD1, "nvlddmkm.sys") == "драйвер"
    assert dump_name_ok("MEMORY.DMP") is False
    dump_name = "012345-67890-01.dmp"
    device_id = _device_id("minidump")
    with TestClient(create_app()) as client:
        enrolled = client.post(
            "/v1/enroll",
            headers={"Authorization": "Bearer test-enrollment-token-change-me-please"},
            json={"device_id": device_id, "hostname": "DUMP-PC"},
        )
        assert enrolled.status_code == 200, enrolled.text
        api_key = enrolled.json()["api_key"]
        inv = client.post(
            "/v1/inventory",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "schema_version": 2,
                "device_id": device_id,
                "minidumps": {"count": 1, "files": [{"name": dump_name}]},
            },
        )
        assert inv.status_code == 200, inv.text
        db = client.app.state.db
        with db.connection() as conn:
            conn.execute("UPDATE local_users SET must_change_password = 0")
        login_page = client.get("/login")
        assert login_page.status_code == 200, login_page.text
        token = re.search(r'name="csrf_token" value="([^"]+)"', login_page.text)
        assert token is not None
        logged = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "admin",
                "csrf_token": token.group(1),
            },
            follow_redirects=False,
        )
        assert logged.status_code == 303, logged.text
        page = client.get(f"/devices/{device_id}")
        assert page.status_code == 200, page.text
        assert "Разобрать" in page.text
        form_token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
        assert form_token is not None
        asked = client.post(
            f"/devices/{device_id}/minidump-request",
            data={"csrf_token": form_token.group(1), "name": dump_name},
            follow_redirects=False,
        )
        assert asked.status_code == 303, asked.text
        beat = client.post(
            "/v1/heartbeat",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"device_id": device_id},
        )
        assert beat.status_code == 200, beat.text
        assert beat.json()["actions"]["upload_minidump"] == dump_name
        rejected = client.post(
            "/v1/agent/minidump",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("MEMORY.DMP", b"MDMP" + b"\x00" * 32, "application/octet-stream")},
        )
        assert rejected.status_code == 400, rejected.text
        old_limit = api_mod.MAX_BYTES
        api_mod.MAX_BYTES = 32
        try:
            oversized = client.post(
                "/v1/agent/minidump",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (dump_name, b"x" * 33, "application/octet-stream")},
            )
        finally:
            api_mod.MAX_BYTES = old_limit
        assert oversized.status_code == 413, oversized.text
        accepted = client.post(
            "/v1/agent/minidump",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (dump_name, _tiny_minidump(), "application/octet-stream")},
        )
        assert accepted.status_code == 200, accepted.text
        assert list(Path(tempfile.gettempdir()).glob("bad-minidump-*")) == []
        again = client.post(
            "/v1/heartbeat",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"device_id": device_id},
        )
        assert again.status_code == 200, again.text
        assert "upload_minidump" not in (again.json().get("actions") or {})
        card = client.get(f"/devices/{device_id}")
        assert card.status_code == 200, card.text
        assert "драйвер · 0x000000D1 · nvlddmkm.sys" in card.text
