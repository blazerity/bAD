"""Важность событий, новые diff и почта по типам."""

from __future__ import annotations

import json

from bad_server.event_importance import event_importance
from bad_server.inventory_events import diff_inventory_snapshots
from bad_server.smtp_mail import (
    DEFAULT_NOTIFY,
    HARDWARE_ALERT_TYPES,
    build_inventory_digest_email,
    filter_events_for_mail,
    parse_notify_flags,
)
from bad_server.web import _EVENT_TYPE_LABELS_RU

_NEW_TYPES = (
    "agent_version_change",
    "os_build_change",
    "bios_update",
    "monitor_set_change",
    "nic_mac_change",
    "ad_ou_change",
    "gpu_added",
    "gpu_removed",
    "smbios_uuid_change",
    "baseboard_serial_change",
    "bios_serial_change",
)

_MOVED = {
    "antivirus_change": "medium",
    "device_stale": "medium",
    "tpm_change": "medium",
    "secure_boot_change": "medium",
    "hostname_change": "medium",
    "minidump_bugcheck": "high",
}

_NEW_IMPORTANCE = {
    "agent_version_change": "low",
    "os_build_change": "low",
    "bios_update": "low",
    "monitor_set_change": "low",
    "nic_mac_change": "low",
    "ad_ou_change": "medium",
    "gpu_added": "medium",
    "gpu_removed": "medium",
    "smbios_uuid_change": "high",
    "baseboard_serial_change": "high",
    "bios_serial_change": "high",
}


def _types(previous: dict, current: dict) -> list[str]:
    return [event["type"] for event in diff_inventory_snapshots(previous, current)]


def _legacy_wanted(flags: dict[str, bool]) -> set[str]:
    wanted: set[str] = set()
    if flags.get("hardware"):
        wanted |= set(HARDWARE_ALERT_TYPES)
    if flags.get("hostname"):
        wanted.add("hostname_change")
    if flags.get("domain"):
        wanted.add("domain_change")
    if flags.get("pending_reboot"):
        wanted.add("pending_reboot_change")
    if flags.get("enroll"):
        wanted.add("device_enrolled")
    if flags.get("stale"):
        wanted.add("device_stale")
    if flags.get("online"):
        wanted.add("device_back_online")
    if flags.get("disk_space"):
        wanted.add("volume_free_drop")
        wanted.add("volume_free_critical")
    return wanted


def _enabled(raw: object) -> set[str]:
    return {key for key, on in parse_notify_flags(raw).items() if on}


def test_importance_table() -> None:
    for event_type, level in _MOVED.items():
        assert event_importance(event_type) == level
    assert event_importance("cpu_change") == "critical"
    assert event_importance("serial_change") == "high"
    assert event_importance("domain_change") == "medium"
    assert event_importance("usb_added") == "low"
    for event_type, level in _NEW_IMPORTANCE.items():
        assert event_importance(event_type) == level
    assert event_importance("device_merged") == "medium"


def test_first_snapshot_is_empty() -> None:
    current = {
        "agent_version": "3.1.4",
        "host": {
            "os": {"caption": "Windows", "version": "10", "build": "1"},
            "ad_ou": "OU=Workstations,DC=contoso,DC=com",
        },
        "hardware": {
            "bios_version": "1.2",
            "smbios_uuid": "aabbccdd-eeff-0011-2233-445566778899",
            "baseboard_serial": "BOARD1",
            "bios_serial": "BIOS1",
            "gpus": [{"pnp_device_id": "PCI\\GPU", "name": "GPU"}],
            "monitors": [{"serial_number": "MON1", "name": "Dell"}],
        },
        "network": {"nics": [{"mac": "AA-BB-CC-DD-EE-FF", "ipv4": ["10.0.0.2"]}]},
    }
    assert diff_inventory_snapshots(None, current) == []


def test_agent_version_change() -> None:
    assert "agent_version_change" not in _types(
        {"agent_version": "3.1.4"},
        {"agent_version": "3.1.4"},
    )
    assert "agent_version_change" not in _types(
        {"agent_version": ""},
        {"agent_version": "3.1.4"},
    )
    events = diff_inventory_snapshots(
        {"agent_version": "3.1.3"},
        {"agent_version": "3.1.4"},
    )
    matched = [event for event in events if event["type"] == "agent_version_change"]
    assert len(matched) == 1
    assert matched[0]["summary"] == "Версия агента: 3.1.3 → 3.1.4"


def test_os_build_change() -> None:
    base = {"caption": "Windows", "version": "10", "build": "1", "arch": "x64"}
    previous = {"host": {"os": dict(base)}}
    changed = {"host": {"os": {**base, "caption": "Windows 11"}}}
    assert _types(previous, changed).count("os_build_change") == 1
    arch_only = {"host": {"os": {**base, "arch": "arm64"}}}
    assert "os_build_change" not in _types(previous, arch_only)
    empty = {"host": {"os": {"caption": "", "version": "", "build": "", "arch": "x64"}}}
    assert "os_build_change" not in _types(empty, previous)


def test_ad_ou_change() -> None:
    previous = {
        "host": {
            "ad_ou": "OU=Laptops,DC=contoso,DC=com",
            "ad_distinguished_name": "CN=PC1,OU=Laptops,DC=contoso,DC=com",
        }
    }
    changed = {
        "host": {
            "ad_ou": "OU=Servers,DC=contoso,DC=com",
            "ad_distinguished_name": "CN=PC1,OU=Servers,DC=contoso,DC=com",
        }
    }
    assert _types(previous, changed).count("ad_ou_change") == 1
    same_ou = {
        "host": {
            "ad_ou": "OU=Laptops,DC=contoso,DC=com",
            "ad_distinguished_name": "CN=PC2,OU=Laptops,DC=contoso,DC=com",
        }
    }
    assert "ad_ou_change" not in _types(previous, same_ou)
    dn_only_cn = {
        "host": {
            "ad_ou": "",
            "ad_distinguished_name": "CN=PC2,OU=Laptops,DC=contoso,DC=com",
        }
    }
    dn_previous = {
        "host": {
            "ad_ou": "",
            "ad_distinguished_name": "CN=PC1,OU=Laptops,DC=contoso,DC=com",
        }
    }
    assert "ad_ou_change" not in _types(dn_previous, dn_only_cn)
    one_empty = {"host": {"ad_ou": "", "ad_distinguished_name": ""}}
    assert "ad_ou_change" not in _types(previous, one_empty)


def test_bios_update() -> None:
    previous = {
        "hardware": {
            "bios_version": "1.0",
            "bios_release_date": "2020-01-01",
            "bios_manufacturer": "Dell",
        }
    }
    version = {
        "hardware": {
            "bios_version": "1.1",
            "bios_release_date": "2020-01-01",
            "bios_manufacturer": "Dell",
        }
    }
    dates = {
        "hardware": {
            "bios_version": "1.0",
            "bios_release_date": "2024-05-01",
            "bios_manufacturer": "Dell",
        }
    }
    assert _types(previous, version).count("bios_update") == 1
    assert _types(previous, dates).count("bios_update") == 1
    empty_version = {
        "hardware": {
            "bios_version": "",
            "bios_release_date": "2020-01-01",
            "bios_manufacturer": "Dell",
        }
    }
    assert "bios_update" not in _types(previous, empty_version)
    manufacturer = {
        "hardware": {
            "bios_version": "1.0",
            "bios_release_date": "2020-01-01",
            "bios_manufacturer": "Lenovo",
        }
    }
    assert "bios_update" not in _types(previous, manufacturer)


def test_board_identity_is_not_serial_change() -> None:
    previous = {
        "hardware": {
            "serial_number": "SYS1",
            "smbios_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "baseboard_serial": "BOARD1",
            "bios_serial": "BIOS1",
        }
    }
    changed = {
        "hardware": {
            "serial_number": "SYS1",
            "smbios_uuid": "11111111-2222-3333-4444-555555555555",
            "baseboard_serial": "BOARD2",
            "bios_serial": "BIOS2",
        }
    }
    found = set(_types(previous, changed))
    assert found == {
        "smbios_uuid_change",
        "baseboard_serial_change",
        "bios_serial_change",
    }
    serial_only = {
        "hardware": {
            "serial_number": "SYS2",
            "smbios_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "baseboard_serial": "BOARD1",
            "bios_serial": "BIOS1",
        }
    }
    assert _types(previous, serial_only) == ["serial_change"]
    hyphen_uuid = {
        "hardware": {
            "serial_number": "SYS1",
            "smbios_uuid": "AAAAAAAABBBB-CCCC-DDDD-EEEEEEEEEEEE",
            "baseboard_serial": "BOARD-1",
            "bios_serial": "BIOS1",
        }
    }
    assert "smbios_uuid_change" not in _types(previous, hyphen_uuid)
    assert "baseboard_serial_change" not in _types(previous, hyphen_uuid)
    all_zero = {
        "hardware": {
            "smbios_uuid": "00000000-0000-0000-0000-000000000000",
            "baseboard_serial": "To be filled by O.E.M.",
            "bios_serial": "0000",
        }
    }
    quiet = _types({"hardware": {"smbios_uuid": "", "baseboard_serial": "", "bios_serial": ""}}, all_zero)
    assert "smbios_uuid_change" not in quiet
    assert "baseboard_serial_change" not in quiet
    assert "bios_serial_change" not in quiet


def test_gpu_and_monitor_and_mac() -> None:
    previous = {
        "hardware": {
            "gpus": [
                {"pnp_device_id": "PCI\\GPU1", "name": "Arc", "driver_version": "1"}
            ],
            "monitors": [
                {"serial_number": "MON1", "name": "Dell", "width": 1920, "height": 1080}
            ],
        },
        "network": {
            "nics": [{"name": "Ethernet", "mac": "AA-BB-CC-DD-EE-FF", "ipv4": ["10.0.0.5"]}]
        },
    }
    added_gpu = {
        "hardware": {
            "gpus": [
                {"pnp_device_id": "PCI\\GPU1", "name": "Arc", "driver_version": "1"},
                {"pnp_device_id": "PCI\\GPU2", "name": "Iris", "driver_version": "2"},
            ],
            "monitors": previous["hardware"]["monitors"],
        },
        "network": previous["network"],
    }
    assert _types(previous, added_gpu) == ["gpu_added"]
    removed_gpu = {
        "hardware": {"gpus": [], "monitors": previous["hardware"]["monitors"]},
        "network": previous["network"],
    }
    assert _types(previous, removed_gpu) == ["gpu_removed"]
    driver = {
        "hardware": {
            "gpus": [
                {"pnp_device_id": "PCI\\GPU1", "name": "Arc", "driver_version": "9"}
            ],
            "monitors": previous["hardware"]["monitors"],
        },
        "network": previous["network"],
    }
    assert "gpu_added" not in _types(previous, driver)
    assert "gpu_removed" not in _types(previous, driver)
    null_gpus = {
        "hardware": {"gpus": None, "monitors": previous["hardware"]["monitors"]},
        "network": previous["network"],
    }
    assert "gpu_added" not in _types(previous, null_gpus)
    assert "gpu_removed" not in _types(previous, null_gpus)
    monitors = {
        "hardware": {
            "gpus": previous["hardware"]["gpus"],
            "monitors": [{"serial_number": "MON2", "name": "LG"}],
        },
        "network": previous["network"],
    }
    assert _types(previous, monitors).count("monitor_set_change") == 1
    resolution = {
        "hardware": {
            "gpus": previous["hardware"]["gpus"],
            "monitors": [
                {"serial_number": "MON1", "name": "Dell", "width": 1280, "height": 720}
            ],
        },
        "network": previous["network"],
    }
    assert "monitor_set_change" not in _types(previous, resolution)
    new_mac = {
        "hardware": previous["hardware"],
        "network": {
            "nics": [{"name": "Ethernet", "mac": "11-22-33-44-55-66", "ipv4": ["10.0.0.5"]}]
        },
    }
    assert _types(previous, new_mac) == ["nic_mac_change"]
    new_ip = {
        "hardware": previous["hardware"],
        "network": {
            "nics": [{"name": "Ethernet", "mac": "AA:BB:CC:DD:EE:FF", "ipv4": ["10.0.0.9"]}]
        },
    }
    assert _types(previous, new_ip) == ["nic_ipv4_change"]


def test_ignored_snapshot_fields_do_not_emit() -> None:
    previous = {
        "hardware": {
            "disks": [{"serial_number": "DISK1", "model": "NVMe", "size_bytes": 100}],
            "volumes": [{"letter": "C", "free_bytes": 50, "size_bytes": 100}],
        },
        "security": {"antivirus": [{"name": "Defender", "product_state": "on"}]},
        "minidumps": {
            "memory_dmp_present": False,
            "files": [{"name": "old.dmp"}],
        },
        "collector_errors": [],
    }
    current = {
        "hardware": {
            "disks": [{"serial_number": "DISK1", "model": "NVMe", "size_bytes": 200}],
            "volumes": [
                {"letter": "C", "free_bytes": 50, "size_bytes": 100},
                {"letter": "D", "free_bytes": 10, "size_bytes": 20},
            ],
        },
        "security": {"antivirus": [{"name": "Defender", "product_state": "off"}]},
        "minidumps": {
            "memory_dmp_present": True,
            "files": [{"name": "old.dmp"}, {"name": "quiet.dmp"}],
        },
        "collector_errors": [{"scope": "gpu", "message": "fail"}],
    }
    assert _types(previous, current) == []


def test_legacy_notify_json_keeps_the_old_set() -> None:
    forbidden = {
        "agent_version_change",
        "os_build_change",
        "bios_update",
        "ad_ou_change",
        "gpu_added",
        "gpu_removed",
        "monitor_set_change",
        "nic_mac_change",
        "smbios_uuid_change",
        "baseboard_serial_change",
        "bios_serial_change",
    }
    expected = _legacy_wanted(dict(DEFAULT_NOTIFY))
    for raw in ("", "{}", json.dumps(DEFAULT_NOTIFY), None):
        enabled = _enabled(raw)
        assert enabled == expected
        assert "minidump_bugcheck" in enabled
        assert forbidden.isdisjoint(enabled)
    saved = dict(DEFAULT_NOTIFY)
    saved["hardware"] = False
    saved["hostname"] = True
    enabled = _enabled(json.dumps(saved))
    assert enabled == _legacy_wanted(saved)
    assert forbidden.isdisjoint(enabled)


def test_new_notify_json_is_explicit() -> None:
    raw = json.dumps({"agent_version_change": True})
    mailed = filter_events_for_mail(
        [
            {"type": "agent_version_change"},
            {"type": "cpu_change"},
            {"type": "minidump_bugcheck"},
            {"type": "disk_added"},
        ],
        parse_notify_flags(raw),
    )
    assert [event["type"] for event in mailed] == ["agent_version_change"]


def test_new_event_labels() -> None:
    expected = {
        "agent_version_change": "Версия агента",
        "os_build_change": "Сборка Windows",
        "ad_ou_change": "OU",
        "bios_update": "BIOS",
        "smbios_uuid_change": "SMBIOS UUID",
        "baseboard_serial_change": "Серийник платы",
        "bios_serial_change": "Серийник BIOS",
        "gpu_added": "Видеокарта подключена",
        "gpu_removed": "Видеокарта отключена",
        "monitor_set_change": "Мониторы",
        "nic_mac_change": "Сетевой интерфейс",
    }
    for event_type, label in expected.items():
        assert _EVENT_TYPE_LABELS_RU[event_type] == label


def test_digest_card_and_compact_line() -> None:
    message = build_inventory_digest_email(
        devices_groups=[
            {
                "hostname": "QUIET",
                "bad_id": "BAD-QUIET",
                "hardware_model": "Hidden",
                "user_display_name": "nobody",
                "events": [{"type": "hostname_change", "summary": "тихо"}],
            },
            {
                "hostname": "LOUD",
                "bad_id": "BAD-9",
                "hardware_model": "OptiPlex",
                "user_display_name": "ivan",
                "chassis_type": "desktop",
                "events": [{"type": "cpu_change", "summary": "процессор сменился"}],
            },
        ],
        from_addr="bad@example.com",
        to_addrs=["ops@example.com"],
        window_label="тест",
    )
    plain = message.get_body(preferencelist=("plain",)).get_content()
    html_body = message.get_body(preferencelist=("html",)).get_content()
    assert "QUIET: тихо" in plain
    assert "QUIET: тихо" in html_body
    assert "Hidden" not in plain
    assert "BAD-QUIET" not in plain
    assert "Модель" not in plain.split("LOUD")[0]
    assert "LOUD" in plain
    assert "BAD-9" in plain
    assert "Модель: OptiPlex · Пользователь: ivan" in plain
    assert "процессор сменился" in plain
    assert "Модель: OptiPlex · Пользователь: ivan" in html_body
    assert "процессор сменился" in html_body
