#!/usr/bin/env python3
"""Демо-парк для скриншотов beta: enroll + inventory + heartbeat через /v1.

Требует запущенный API (обычно с BAD_QA_UI=1 на стенде QA) и тот же
BAD_ENROLLMENT_TOKEN, что в окружении сервера.

  cd server
  python scripts/seed-beta-demo.py --base http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

GB = 1024**3

CPUS = {
    "intel": {"name": "Intel Core i7-12700", "vendor": "GenuineIntel"},
    "amd": {"name": "AMD Ryzen 7 5800X", "vendor": "AuthenticAMD"},
}


def post(base: str, path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def _cpu_for(device_id: str) -> dict:
    key = "amd" if "dev" in device_id or "lab" in device_id else "intel"
    return dict(CPUS[key])


DEVICES = [
    {
        "device_id": "ws-finance-01",
        "hostname": "WS-FINANCE-01",
        "agent_version": "1.3.1",
        "os": "Windows 11 Pro",
        "domain": "corp.local",
        "manufacturer": "Dell",
        "model": "OptiPlex 7090",
        "serial": "SN-FIN-001",
        "ram_bytes": 32 * GB,
        "disk_gb": 512,
        "user": "o.ivanova",
        "ip": "10.42.1.11",
    },
    {
        "device_id": "ws-ops-02",
        "hostname": "WS-OPS-02",
        "agent_version": "1.3.1",
        "os": "Windows 11 Pro",
        "domain": "corp.local",
        "manufacturer": "HP",
        "model": "EliteDesk 800",
        "serial": "SN-OPS-002",
        "ram_bytes": 16 * GB,
        "disk_gb": 256,
        "user": "a.petrov",
        "ip": "10.42.1.22",
    },
    {
        "device_id": "ws-dev-03",
        "hostname": "WS-DEV-03",
        "agent_version": "1.2.2",
        "os": "Windows 10 Pro",
        "domain": "corp.local",
        "manufacturer": "Lenovo",
        "model": "ThinkCentre M90",
        "serial": "SN-DEV-003",
        "ram_bytes": 64 * GB,
        "disk_gb": 1024,
        "user": "m.sidorov",
        "ip": "10.42.3.33",
    },
    {
        "device_id": "lt-sales-04",
        "hostname": "LT-SALES-04",
        "agent_version": "1.3.1",
        "os": "Windows 11 Pro",
        "domain": "corp.local",
        "manufacturer": "Dell",
        "model": "Latitude 5540",
        "serial": "SN-SAL-004",
        "ram_bytes": 16 * GB,
        "disk_gb": 512,
        "user": "e.kozlov",
        "ip": "10.42.2.44",
    },
    {
        "device_id": "ws-lab-05",
        "hostname": "WS-LAB-05",
        "agent_version": "1.3.0",
        "os": "Windows 10 Pro",
        "domain": "lab.local",
        "manufacturer": "ASUS",
        "model": "ExpertCenter D5",
        "serial": "SN-LAB-005",
        "ram_bytes": 8 * GB,
        "disk_gb": 256,
        "user": "lab.user",
        "ip": "10.99.0.55",
    },
    {
        "device_id": "ws-qa-06",
        "hostname": "WS-QA-06",
        "agent_version": "1.3.1",
        "os": "Windows 11 Pro",
        "domain": "corp.local",
        "manufacturer": "HP",
        "model": "ProDesk 400",
        "serial": "SN-QA-006",
        "ram_bytes": 32 * GB,
        "disk_gb": 512,
        "user": "qa.lead",
        "ip": "10.42.3.66",
    },
]


def seed_one(base: str, enroll_token: str, d: dict, collected_at: str) -> None:
    enroll = post(
        base,
        "/v1/enroll",
        {
            "device_id": d["device_id"],
            "hostname": d["hostname"],
            "agent_version": d["agent_version"],
        },
        token=enroll_token,
    )
    key = enroll["api_key"]
    disk_bytes = int(d["disk_gb"]) * GB
    inv = {
        "schema_version": 2,
        "device_id": d["device_id"],
        "agent_version": d["agent_version"],
        "collected_at": collected_at,
        "host": {
            "hostname": d["hostname"],
            "domain": d["domain"],
            "os": {"caption": d["os"], "version": "10.0.22631"},
        },
        "hardware": {
            "manufacturer": d["manufacturer"],
            "model": d["model"],
            "chassis_type": "laptop" if d["hostname"].startswith("LT-") else "desktop",
            "serial_number": d["serial"],
            "ram_bytes": d["ram_bytes"],
            "cpu": _cpu_for(d["device_id"]),
            "disks": [
                {
                    "model": "NVMe Demo",
                    "serial_number": f"{d['serial']}-DISK",
                    "size_bytes": disk_bytes,
                    "interface_type": "NVMe",
                }
            ],
            "volumes": [
                {
                    "letter": "C:",
                    "size_bytes": disk_bytes,
                    "free_bytes": disk_bytes // 3,
                }
            ],
        },
        "network": {
            "nics": [
                {
                    "name": "Ethernet",
                    "mac": "00:11:22:33:44:55",
                    "ipv4": [d["ip"]],
                }
            ]
        },
        "users": {"logged_on": [f"{d['domain'].split('.')[0]}\\{d['user']}"]},
    }
    post(base, "/v1/inventory", inv, token=key)
    if d["device_id"] in {"ws-finance-01", "ws-dev-03"}:
        inv2 = json.loads(json.dumps(inv))
        inv2["collected_at"] = collected_at.replace("T12:", "T13:")
        inv2["hardware"]["ram_bytes"] = d["ram_bytes"] + 8 * GB
        post(base, "/v1/inventory", inv2, token=key)
    post(
        base,
        "/v1/heartbeat",
        {
            "device_id": d["device_id"],
            "agent_version": d["agent_version"],
            "last_inventory_ok": True,
        },
        token=key,
    )
    print("OK", d["device_id"], d["hostname"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8000")
    p.add_argument("--token", default="dev-enrollment-token-change-me-please-32b")
    args = p.parse_args()
    try:
        with urllib.request.urlopen(args.base.rstrip("/") + "/v1/health", timeout=8) as r:
            health = json.loads(r.read().decode())
        print("health", health)
    except Exception as e:
        print("BLOCKER: server not healthy:", e, file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for d in DEVICES:
        try:
            seed_one(args.base, args.token, d, now)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print("FAIL", d["device_id"], e.code, body, file=sys.stderr)
            return 1
    print(f"DONE seeded={len(DEVICES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
