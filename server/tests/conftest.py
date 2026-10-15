from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from helpers import ADMIN_TOKEN, ENROLLMENT_TOKEN

# Import-time defaults so Settings can construct before fixtures run.
os.environ.setdefault("BAD_ENROLLMENT_TOKEN", ENROLLMENT_TOKEN)
os.environ.setdefault("BAD_ADMIN_TOKEN", ADMIN_TOKEN)


@pytest.fixture()
def updates_dir(tmp_path: Path) -> Path:
    return tmp_path / "agent-updates"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, updates_dir: Path):
    monkeypatch.setenv("BAD_DB_PATH", str(tmp_path / "bad.db"))
    monkeypatch.setenv("BAD_ENROLLMENT_TOKEN", ENROLLMENT_TOKEN)
    monkeypatch.setenv("BAD_ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv(
        "BAD_SESSION_SECRET",
        "test-session-secret-abcdefghijklmnopqrstuvwxyz",
    )
    monkeypatch.setenv("BAD_AGENT_UPDATES_DIR", str(updates_dir))
    monkeypatch.setenv("BAD_AGENT_UPDATE_SYNC_ON_STARTUP", "false")
    monkeypatch.setenv("BAD_AGENT_UPDATE_SYNC_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("BAD_GITHUB_REPO", "blazerity/bAD")

    from bad_server.config import get_settings

    get_settings.cache_clear()
    from bad_server.app import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
