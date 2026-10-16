"""Тема B: bootstrap-чеклист, очередь «требует действия», фильтры волны, победитель конфига.

Только сборка контекста для web UI из уже существующих полей (tls / enrollment / ops /
meta.config_local / sources). Без новых таблиц БД.
"""

from __future__ import annotations

from typing import Any, Optional

from .agent_config import ALLOWED_SETTING_KEYS, compute_setting_sources
from .device_health import device_silence_status
from .enrollment_ops import enrollment_status
from .tls_ops import tls_panel_mode

WAVE_FILTERS = frozenset({"drift", "revoked", "agent_local", "stale"})

_SOURCE_LABEL_RU = {
    "default": "по умолчанию",
    "policy": "политика",
    "device_override": "override сервера",
    "agent_local": "задано на агенте",
}

_FOCUS_KEYS = (
    "inventory_interval_hours",
    "heartbeat_interval_minutes",
    "update_check_interval_hours",
    "collect_hardware",
    "collect_users",
    "collect_software",
)

_FOCUS_LABELS_RU = {
    "inventory_interval_hours": "Inventory",
    "heartbeat_interval_minutes": "Heartbeat",
    "update_check_interval_hours": "Проверка обновлений",
    "collect_hardware": "Сбор железа",
    "collect_users": "Сбор пользователей",
    "collect_software": "Сбор ПО",
}


def source_label_ru(source: Optional[str]) -> str:
    if not source:
        return "—"
    return _SOURCE_LABEL_RU.get(str(source), str(source))


def build_bootstrap_checklist(
    *,
    user: Any,
    db: Any,
    settings: Any,
    ops: dict[str, Any],
    active_devices: int,
    security: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Компактный прогресс первого запуска. Скрывается после HTTPS + смена пароля."""
    security = security or {}
    https = security.get("https_first") or {}
    enroll_block = security.get("enrollment") or {}
    tls_mode = str(
        ops.get("tls_mode") or https.get("tls_mode") or tls_panel_mode() or "http"
    ).lower()
    enroll = enroll_block or enrollment_status(db, settings)
    password_done = not bool(user.must_change_password)
    https_done = tls_mode == "https"
    enroll_done = bool(enroll.get("configured"))
    mirror_done = not bool(ops.get("mirror_empty"))
    fleet_done = active_devices > 0
    secrets_ok = not bool(ops.get("legacy_keys_in_sqlite"))

    steps = [
        {
            "id": "password",
            "label": "Сменить пароль admin",
            "done": password_done,
            "href": "/account/password",
        },
        {
            "id": "tls",
            "label": "Загрузить сертификат (HTTPS)",
            "done": https_done,
            "href": "/settings/tls",
        },
        {
            "id": "enrollment",
            "label": "Enrollment token готов",
            "done": enroll_done,
            "href": "/settings/updates",
        },
        {
            "id": "mirror",
            "label": "Зеркало MSI не пусто",
            "done": mirror_done,
            "href": "/settings/updates",
        },
        {
            "id": "fleet",
            "label": "Есть хотя бы одно устройство",
            "done": fleet_done,
            "href": "/devices",
        },
        {
            "id": "secrets",
            "label": "Ключи вне SQLite (SEC-005)",
            "done": secrets_ok,
            "href": "/settings/backups",
        },
    ]
    done_n = sum(1 for s in steps if s["done"])
    # По brainstorm: чеклист исчезает после HTTPS + не-default admin.
    visible = not (password_done and https_done)
    return {
        "visible": visible,
        "steps": steps,
        "done": done_n,
        "total": len(steps),
        "tls_mode": tls_mode,
    }


def build_attention_queue(
    *,
    user: Any,
    ops: dict[str, Any],
    stats: dict[str, Any],
    tls_mode: str,
    security: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Одна приоритизированная лента «требует действия» для Обзора.

    Хуки Server A: ``ops.enrollment_rotation_due``, ``ops.legacy_keys_in_sqlite``,
    ``security.https_first`` / ``security.secrets`` / ``security.enrollment_rotation``.
    """
    items: list[dict[str, Any]] = []
    security = security or (ops.get("security") or {})
    er = security.get("enrollment_rotation") or {}
    secrets = security.get("secrets") or {}
    https = security.get("https_first") or {}
    mode = str(tls_mode or ops.get("tls_mode") or https.get("tls_mode") or "http").lower()

    if user.must_change_password:
        items.append(
            {
                "id": "password",
                "severity": "high",
                "title": "Пароль по умолчанию",
                "detail": "Смените admin/admin до работы в проде.",
                "href": "/account/password",
                "cta": "Сменить пароль",
            }
        )
    if mode == "http":
        items.append(
            {
                "id": "tls",
                "severity": "high",
                "title": "HTTP bootstrap",
                "detail": ops.get("https_first_hint")
                or https.get("hint_ru")
                or "Только доверенная сеть — загрузите сертификат.",
                "href": "/settings/tls",
                "cta": "Сертификат",
            }
        )
    if ops.get("legacy_keys_in_sqlite") or secrets.get("legacy_keys_in_sqlite"):
        items.append(
            {
                "id": "secrets",
                "severity": "high",
                "title": "Ключи ещё в SQLite (SEC-005)",
                "detail": ops.get("secrets_hint")
                or secrets.get("hint_ru")
                or "Вынесите data_key / session_secret в /etc/bad.",
                "href": "/settings/backups",
                "cta": "Резервные копии",
            }
        )
    if ops.get("enrollment_rotation_due") or er.get("rotation_due"):
        n = int(
            ops.get("enrolled_since_rotation")
            or er.get("enrolled_since_rotation")
            or 0
        )
        items.append(
            {
                "id": "enrollment_rotate",
                "severity": "high",
                "title": "Ротация enrollment после волны",
                "detail": ops.get("enrollment_rotation_hint")
                or er.get("hint_ru")
                or f"Новых enroll с прошлой ротации: {n}.",
                "href": ops.get("enrollment_rotate_path")
                or er.get("ui_path")
                or "/settings/updates",
                "cta": "Сменить token",
            }
        )
    if ops.get("mirror_empty"):
        items.append(
            {
                "id": "mirror",
                "severity": "high",
                "title": "Зеркало MSI пусто",
                "detail": "Агенты не получат обновления.",
                "href": "/settings/updates",
                "cta": "Обновления агента",
            }
        )
    pin_n = int(ops.get("pinned_missing_count") or 0)
    if pin_n:
        items.append(
            {
                "id": "pin",
                "severity": "high",
                "title": f"Закреплённая версия отсутствует ({pin_n})",
                "detail": "Pin политики не резолвится в зеркале.",
                "href": "/settings/updates",
                "cta": "Зеркало MSI",
            }
        )
    drift_n = int(ops.get("version_drift_count") or 0)
    if drift_n:
        items.append(
            {
                "id": "drift",
                "severity": "medium",
                "title": f"Отстают от целевой версии ({drift_n})",
                "detail": "Волна обновлений не закрыта.",
                "href": "/devices?wave=drift",
                "cta": "Фильтр drift",
            }
        )
    revoked_n = int(ops.get("revoked_active") or 0)
    if revoked_n:
        items.append(
            {
                "id": "revoked",
                "severity": "medium",
                "title": f"Отозванные активные ({revoked_n})",
                "detail": "Нужен rotate-key или архив.",
                "href": "/devices?wave=revoked",
                "cta": "Фильтр revoked",
            }
        )
    stale_n = int(stats.get("stale") or 0)
    if stale_n:
        items.append(
            {
                "id": "stale",
                "severity": "low",
                "title": f"Давно не виделись ({stale_n})",
                "detail": "Нет контакта дольше порога silence.",
                "href": "/devices?wave=stale",
                "cta": "Фильтр stale",
            }
        )
    return items


def normalize_wave_filter(raw: Optional[str]) -> Optional[str]:
    text = (raw or "").strip().casefold()
    return text if text in WAVE_FILTERS else None


def device_has_agent_local(device: dict[str, Any]) -> bool:
    meta = device.get("meta")
    if not isinstance(meta, dict):
        return False
    block = meta.get("config_local")
    if not isinstance(block, dict):
        return False
    keys = block.get("keys")
    return isinstance(keys, list) and bool(keys)


def filter_devices_by_wave(
    devices: list[dict[str, Any]],
    wave: Optional[str],
    *,
    drift_ids: set[str],
    stale_after_seconds: int,
) -> list[dict[str, Any]]:
    if not wave:
        return devices

    def _match(d: dict[str, Any]) -> bool:
        if wave == "drift":
            return d.get("device_id") in drift_ids
        if wave == "revoked":
            return bool(d.get("revoked"))
        if wave == "agent_local":
            return device_has_agent_local(d)
        if wave == "stale":
            silence = d.get("silence") or device_silence_status(
                d.get("last_seen_at"), stale_after_seconds=stale_after_seconds
            )
            return (silence or {}).get("status") == "stale"
        return False

    return [d for d in devices if _match(d)]


def build_config_winner(
    *,
    effective: dict[str, Any],
    sources: dict[str, Any],
    agent_local_keys: list[str],
    settings_values: dict[str, Any],
    policy_keys: Optional[list[str]] = None,
    override_keys: Optional[list[str]] = None,
    allowed_setting_keys: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Кто победил: remote merge vs метка панели (agent_local).

    Server C отдаёт ``policy_keys`` / ``override_keys`` / ``allowed_setting_keys``.
    """
    pk = set(policy_keys if policy_keys is not None else (effective.get("policy_keys") or []))
    ok = set(
        override_keys
        if override_keys is not None
        else (effective.get("override_keys") or [])
    )
    allow = set(allowed_setting_keys or ALLOWED_SETTING_KEYS)
    remote_sources = compute_setting_sources(
        policy_keys=pk,
        override_keys=ok,
        agent_local_keys=None,
    )
    local_set = set(agent_local_keys or [])
    rows: list[dict[str, Any]] = []
    conflicts = 0
    focus = [k for k in _FOCUS_KEYS if k in allow]
    for key in focus:
        remote = remote_sources.get(key) or "default"
        panel = (sources or {}).get(key) or remote
        if key in local_set:
            panel = "agent_local"
        conflict = panel == "agent_local" and remote in {"policy", "device_override"}
        if conflict:
            conflicts += 1
        # Показываем строку, если не «всё default без local».
        if remote == "default" and panel == "default":
            continue
        rows.append(
            {
                "key": key,
                "label": _FOCUS_LABELS_RU.get(key, key),
                "value": settings_values.get(key),
                "remote": remote,
                "remote_label": source_label_ru(remote),
                "panel": panel,
                "panel_label": source_label_ru(panel),
                "conflict": conflict,
            }
        )
    return {
        "rows": rows,
        "conflicts": conflicts,
        "has_rows": bool(rows),
        "remote_sources": remote_sources,
        "policy_keys": sorted(pk),
        "override_keys": sorted(ok),
    }
