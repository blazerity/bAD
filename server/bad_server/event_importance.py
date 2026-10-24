"""Важность событий inventory для UI и фильтров (не отдельная колонка в БД)."""

from __future__ import annotations

from typing import Optional

_EVENT_IMPORTANCE: dict[str, str] = {
    "minidump_bugcheck": "critical",
    "disk_removed": "critical",
    "cpu_change": "critical",
    "ram_module_removed": "critical",
    "serial_change": "high",
    "model_change": "high",
    "manufacturer_change": "high",
    "device_stale": "high",
    "secure_boot_change": "high",
    "tpm_change": "high",
    "antivirus_change": "high",
    "disk_added": "medium",
    "ram_module_added": "medium",
    "volume_free_drop": "medium",
    "device_enrolled": "medium",
    "domain_change": "medium",
    "ram_bytes_change": "low",
    "nic_ipv4_change": "low",
    "pending_reboot_change": "low",
    "chassis_type_change": "low",
    "hostname_change": "low",
    "last_boot_change": "low",
    "timezone_change": "low",
    "logged_on_change": "low",
    "last_interactive_change": "low",
    "usb_added": "low",
    "usb_removed": "low",
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


def event_passes_importance(event_type: str, min_level: Optional[str]) -> bool:
    if not min_level:
        return importance_rank(event_importance(event_type)) >= _RANK["medium"]
    if min_level == "all":
        return True
    return importance_rank(event_importance(event_type)) >= importance_rank(min_level)
