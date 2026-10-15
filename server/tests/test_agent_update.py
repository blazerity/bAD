from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bad_server.github_release import sha256_hex

from helpers import ADMIN_TOKEN, enroll_device


def _seed_mirror(client: TestClient, updates: Path, version: str, payload: bytes) -> str:
    updates.mkdir(parents=True, exist_ok=True)
    msi_name = f"bad-agent-{version}.msi"
    path = updates / msi_name
    path.write_bytes(payload)
    digest = sha256_hex(payload)
    from bad_server.config import get_settings
    from bad_server.db import Database

    db = Database(get_settings().db_path)
    db.set_agent_update(
        version=version,
        msi_name=msi_name,
        sha256=digest,
        file_path=str(path),
        source_tag=f"v{version}",
        release_url="https://github.com/blazerity/bAD/releases/tag/v" + version,
    )
    return digest


def test_check_no_mirror(client: TestClient):
    api_key = enroll_device(client)
    r = client.get(
        "/v1/agent/update/check",
        params={"current": "0.1.0"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["update_available"] is False
    assert body["version"] is None


def test_check_and_download_msi(client: TestClient, updates_dir: Path):
    api_key = enroll_device(client)
    payload = b"fake-msi-bytes-for-test"
    digest = _seed_mirror(client, updates_dir, "0.2.0", payload)

    r = client.get(
        "/v1/agent/update/check",
        params={"current": "0.1.0"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["update_available"] is True
    assert body["version"] == "0.2.0"
    assert body["sha256"] == digest
    assert body["url"] == "/v1/agent/update/msi"

    # same version → no update
    same = client.get(
        "/v1/agent/update/check",
        params={"current": "0.2.0"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert same.json()["update_available"] is False

    dl = client.get(
        "/v1/agent/update/msi",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert dl.status_code == 200
    assert dl.content == payload


def test_update_requires_api_key(client: TestClient):
    assert client.get("/v1/agent/update/check", params={"current": "0.1.0"}).status_code == 401
    assert client.get("/v1/agent/update/msi").status_code == 401


def test_admin_status_and_sync_fixture(
    client: TestClient, updates_dir: Path, monkeypatch: pytest.MonkeyPatch
):
    admin = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

    status = client.get("/v1/admin/agent-update", headers=admin)
    assert status.status_code == 200
    assert status.json()["mirrored"] is None
    assert status.json()["github_repo"] == "blazerity/bAD"

    # Fixture GitHub sync without network
    from bad_server import github_release
    from bad_server.github_release import ReleaseAssets

    payload = b"mirrored-from-fixture"
    digest = sha256_hex(payload)

    def fake_fetch(repo: str, token: str = "", api_base: str = "https://api.github.com"):
        assert repo == "blazerity/bAD"
        return ReleaseAssets(
            tag="v0.1.1",
            version="0.1.1",
            msi_name="bad-agent-0.1.1.msi",
            sha256=digest,
            msi_download_url="https://example.invalid/msi",
            manifest_download_url="https://example.invalid/manifest",
            release_url="https://github.com/blazerity/bAD/releases/tag/v0.1.1",
        )

    def fake_download(url: str, token: str = "") -> bytes:
        return payload

    monkeypatch.setattr(github_release, "fetch_latest_release_assets", fake_fetch)
    monkeypatch.setattr(
        "bad_server.agent_update.fetch_latest_release_assets", fake_fetch
    )
    monkeypatch.setattr(github_release, "_download_bytes", fake_download)

    sync = client.post("/v1/admin/agent-update/sync", headers=admin)
    assert sync.status_code == 200, sync.text
    mirrored = sync.json()["mirrored"]
    assert mirrored["version"] == "0.1.1"
    assert mirrored["sha256"] == digest
    assert Path(mirrored["file_path"]).is_file()
    assert (updates_dir / "bad-agent-0.1.1.msi").read_bytes() == payload
    assert (updates_dir / "agent-release.json").is_file()

    # Web UI shows mirrored version (session login, not admin API token)
    login = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    assert "bad_session" in login.cookies
    page = client.get("/devices")
    assert page.status_code == 200
    assert "0.1.1" in page.text


def test_is_newer_helpers():
    from bad_server.agent_update import is_newer, parse_semver

    assert parse_semver("0.1.0") == (0, 1, 0)
    assert parse_semver("v1.2.3-beta") == (1, 2, 3)
    assert is_newer("0.2.0", "0.1.0")
    assert not is_newer("0.1.0", "0.1.0")
    assert not is_newer("0.1.0", "0.2.0")
    assert is_newer("0.1.0", "bogus")
