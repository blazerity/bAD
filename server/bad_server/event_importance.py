"""Важность событий inventory для UI и фильтров (не отдельная колонка в БД)."""

from __future__ import annotations

_EVENT_IMPORTANCE: dict[str, str] = {
    "minidump_bugcheck": "high",
    "disk_removed": "critical",
    "cpu_change": "critical",
    "ram_module_removed": "critical",
    "serial_change": "high",
    "model_change": "high",
    "manufacturer_change": "high",
    "device_stale": "medium",
    "device_back_online": "medium",
    "secure_boot_change": "medium",
    "tpm_change": "medium",
    "antivirus_change": "medium",
    "disk_added": "medium",
    "ram_module_added": "medium",
    "volume_free_drop": "medium",
    "volume_free_critical": "critical",
    "device_enrolled": "medium",
    "device_merged": "medium",
    "ad_ou_change": "medium",
    "gpu_added": "medium",
    "gpu_removed": "medium",
    "domain_change": "medium",
    "ram_bytes_change": "low",
    "nic_ipv4_change": "low",
    "pending_reboot_change": "low",
    "chassis_type_change": "low",
    "hostname_change": "medium",
    "agent_version_change": "low",
    "os_build_change": "low",
    "bios_update": "low",
    "monitor_set_change": "low",
    "nic_mac_change": "low",
    "last_boot_change": "low",
    "timezone_change": "low",
    "logged_on_change": "low",
    "last_interactive_change": "low",
    "usb_added": "low",
    "usb_removed": "low",
    "smbios_uuid_change": "high",
    "baseboard_serial_change": "high",
    "bios_serial_change": "high",
}

_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}

IMPORTANCE_LABELS_RU = {
    "critical": "Критично",
    "high": "Высокая",
    "medium": "Средняя",
    "low": "Низкая",
}

FILTER_PRESET_LABELS_RU = {
    "": "Средняя и выше (без шума)",
    "all": "Все события",
    "high": "Высокая и выше",
    "critical": "Только критичные",
}


def event_importance(event_type: str) -> str:
    return _EVENT_IMPORTANCE.get(str(event_type or "").strip(), "medium")


def importance_rank(level: str) -> int:
    return _RANK.get(level, 2)


def types_at_least(min_level: str) -> frozenset[str]:
    need = importance_rank(min_level)
    return frozenset(
        t for t, lvl in _EVENT_IMPORTANCE.items() if importance_rank(lvl) >= need
    )


def types_exact_importance(level: str) -> frozenset[str]:
    want = str(level or "").strip().casefold()
    return frozenset(t for t, lvl in _EVENT_IMPORTANCE.items() if lvl == want)
