from __future__ import annotations

from fastapi.testclient import TestClient

ENROLLMENT_TOKEN = "test-enrollment-token-abcdefghijklmnopqrstuvwxyz"
ADMIN_TOKEN = "test-admin-token-abcdefghijklmnopqrstuvwxyz"


def enroll_device(
    client: TestClient,
    *,
    device_id: str = "upd-device-1",
    hostname: str = "UPD-HOST",
    agent_version: str = "0.1.0",
) -> str:
    r = client.post(
        "/v1/enroll",
        headers={"Authorization": f"Bearer {ENROLLMENT_TOKEN}"},
        json={
            "device_id": device_id,
            "hostname": hostname,
            "agent_version": agent_version,
        },
    )
    assert r.status_code == 200
    return r.json()["api_key"]
