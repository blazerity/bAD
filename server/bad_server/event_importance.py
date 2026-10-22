"""Важность событий inventory для UI и фильтров (не отдельная колонка в БД)."""

from __future__ import annotations

from typing import Optional

# critical — безопасность / отказ железа / BSOD
# high — заметные изменения железа или диска
# medium — сеть, reboot, security knobs
# low — шум (сессии, timezone, hostname в AD-среде)

_EVENT_IMPORTANCE: dict[str, str] = {
    "minidump_bugcheck": "critical",
    "disk_removed": "critical",
    "serial_change": "critical",
    "cpu_change": "high",
    "ram_module_removed": "high",
    "disk_added": "high",
    "volume_free_drop": "high",
    "model_change": "high",
    "manufacturer_change": "high",
    "ram_bytes_change": "medium",
    "ram_module_added": "medium",
    "nic_ipv4_change": "medium",
    "pending_reboot_change": "medium",
    "secure_boot_change": "medium",
    "tpm_change": "medium",
    "antivirus_change": "medium",
    "chassis_type_change": "medium",
    "hostname_change": "low",
    "domain_change": "low",
    "last_boot_change": "low",
    "timezone_change": "low",
    "logged_on_change": "low",
    "last_interactive_change": "low",
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
    """Типы с важностью >= min_level (для SQL IN)."""
    need = importance_rank(min_level)
    return frozenset(
        t for t, lvl in _EVENT_IMPORTANCE.items() if importance_rank(lvl) >= need
    )


def event_passes_importance(event_type: str, min_level: Optional[str]) -> bool:
    if not min_level:
        # default UI: скрыть low
        return importance_rank(event_importance(event_type)) >= _RANK["medium"]
    if min_level == "all":
        return True
    return importance_rank(event_importance(event_type)) >= importance_rank(min_level)
