"""Тема B: bootstrap-чеклист, очередь «требует действия», фильтры волны, победитель конфига.

Только сборка контекста для web UI из уже существующих полей (tls / enrollment / ops /
meta.config_local / sources). Без новых таблиц БД.
Дашборд (/dashboard): конфиги парка (ОС/ОЗУ/диски/treemap). События и дрейф — на Обзоре.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from .agent_config import ALLOWED_SETTING_KEYS, compute_setting_sources
from .device_health import device_silence_status
from .enrollment_ops import enrollment_status
from .fleet_buckets import normalize_os_caption, resolve_cpu_family
from .tls_ops import tls_panel_mode

WAVE_FILTERS = frozenset({"drift", "revoked", "agent_local", "stale", "dup"})

# Дашборд: конфиги парка (ОС / ОЗУ / диски / treemap железа)
OS_DOMAIN_BAR_TOP = 5
INVENTORY_SCAN_CAP = 500

_SOURCE_LABEL_RU = {
    "default": "по умолчанию",
    "policy": "политика",
    "device_override": "ручная настройка в панели",
    "agent_local": "задано на компьютере",
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
    "inventory_interval_hours": "Инвентаризация",
    "heartbeat_interval_minutes": "Связь с сервером",
    "update_check_interval_hours": "Проверка обновлений",
    "collect_hardware": "Сбор железа",
    "collect_users": "Сбор пользователей",
    "collect_software": "Сбор ПО",
}


def source_label_ru(source: Optional[str]) -> str:
    if not source:
        return "—"
    return _SOURCE_LABEL_RU.get(str(source), str(source))


def build_bootstrap_progress(
    *,
    user: Any,
    ops: dict[str, Any],
    active_devices: int,
    security: Optional[dict[str, Any]] = None,
    settings: Any = None,
) -> dict[str, Any]:
    """Мастер первого запуска: явные шаги 1/2/3 без дублирования эвристик в UI.

    1 — пароль сменён; 2 — HTTPS; 3 — есть устройство или каталог установщиков не пуст.
    """
    if settings and getattr(settings, "qa_ui", False):
        return {
            "total": 3,
            "done": 3,
            "current": 4,
            "complete": True,
            "label": "готово",
            "steps": [],
            "tls_mode": "https",
        }
    security = security or {}
    https = security.get("https_first") or {}
    tls_mode = str(
        ops.get("tls_mode") or https.get("tls_mode") or tls_panel_mode() or "http"
    ).lower()
    password_done = not bool(user.must_change_password)
    https_done = tls_mode == "https"
    mirror_done = not bool(ops.get("mirror_empty"))
    fleet_done = int(active_devices or 0) > 0
    step3_done = fleet_done or mirror_done

    steps = [
        {
            "n": 1,
            "id": "password",
            "label": "Сменить пароль admin",
            "done": password_done,
            "href": "/account/password",
        },
        {
            "n": 2,
            "id": "https",
            "label": "Включить защищённое соединение",
            "done": https_done,
            "href": "/settings/tls",
        },
        {
            "n": 3,
            "id": "fleet_or_installer",
            "label": "Устройство в парке или установщик готов",
            "done": step3_done,
            "href": "/devices" if not fleet_done else "/settings/updates",
            "fleet_done": fleet_done,
            "installer_ready": mirror_done,
        },
    ]
    total = len(steps)
    done_n = sum(1 for s in steps if s["done"])
    current = total + 1
    for s in steps:
        if not s["done"]:
            current = int(s["n"])
            break
    complete = done_n >= total
    return {
        "total": total,
        "done": done_n,
        "current": current,
        "complete": complete,
        "label": "готово" if complete else f"шаг {current}/{total}",
        "steps": steps,
        "tls_mode": tls_mode,
    }


def enrich_overview_ops_signals(db: Any, ops: dict[str, Any]) -> dict[str, Any]:
    """Стабильные флаги обзора для UI (S5): LDAP, legacy keys, пустое зеркало."""
    out = dict(ops)
    ldap = db.get_ldap_settings()
    ldap_insecure = bool(ldap.get("enabled") and ldap.get("tls_insecure"))
    out["ldap_tls_insecure"] = ldap_insecure
    out["signal_ldap_tls_insecure"] = ldap_insecure
    legacy = bool(
        out.get("legacy_keys_in_db") or out.get("legacy_keys_in_sqlite")
    )
    out["signal_legacy_keys_in_db"] = legacy
    out["signal_mirror_empty"] = bool(out.get("mirror_empty"))
    return out


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
    if getattr(settings, "qa_ui", False):
        progress = build_bootstrap_progress(
            user=user,
            ops=ops,
            active_devices=active_devices,
            security=security,
            settings=settings,
        )
        return {
            "visible": False,
            "steps": [],
            "done": 0,
            "total": 0,
            "tls_mode": "https",
            "progress": progress,
        }
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
    secrets_ok = not bool(
        ops.get("legacy_keys_in_db") or ops.get("legacy_keys_in_sqlite")
    )

    steps = [
        {
            "id": "password",
            "label": "Сменить пароль admin",
            "done": password_done,
            "href": "/account/password",
        },
        {
            "id": "tls",
            "label": "Включить защищённое соединение (Сертификат)",
            "done": https_done,
            "href": "/settings/tls",
        },
        {
            "id": "enrollment",
            "label": "Токен подключения готов",
            "done": enroll_done,
            "href": "/settings/updates#enrollment",
        },
        {
            "id": "mirror",
            "label": "Каталог установщиков не пуст",
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
            "label": "Ключи вне базы данных",
            "done": secrets_ok,
            "href": "/settings/backups",
        },
    ]
    done_n = sum(1 for s in steps if s["done"])
    # По brainstorm: чеклист исчезает после HTTPS + не-default admin.
    visible = not (password_done and https_done)
    progress = build_bootstrap_progress(
        user=user,
        ops=ops,
        active_devices=active_devices,
        security=security,
    )
    return {
        "visible": visible,
        "steps": steps,
        "done": done_n,
        "total": len(steps),
        "tls_mode": tls_mode,
        "progress": progress,
    }


def build_attention_queue(
    *,
    user: Any,
    ops: dict[str, Any],
    stats: dict[str, Any],
    tls_mode: str,
    security: Optional[dict[str, Any]] = None,
    qa_ui: bool = False,
) -> list[dict[str, Any]]:
    """Одна приоритизированная лента «требует действия» для Обзора.

    Хуки Server A: ``ops.enrollment_rotation_due``, ``ops.legacy_keys_in_db``,
    ``security.https_first`` / ``security.secrets`` / ``security.enrollment_rotation``.
    """
    items: list[dict[str, Any]] = []
    security = security or (ops.get("security") or {})
    er = security.get("enrollment_rotation") or {}
    secrets = security.get("secrets") or {}
    https = security.get("https_first") or {}
    mode = str(tls_mode or ops.get("tls_mode") or https.get("tls_mode") or "http").lower()
    legacy_keys = bool(
        ops.get("legacy_keys_in_db")
        or ops.get("legacy_keys_in_sqlite")
        or secrets.get("legacy_keys_in_db")
        or secrets.get("legacy_keys_in_sqlite")
    )

    if user.must_change_password and not qa_ui:
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
    if mode == "http" and not qa_ui:
        items.append(
            {
                "id": "tls",
                "severity": "high",
                "title": "Нужно защищённое соединение",
                "detail": ops.get("https_first_hint")
                or https.get("hint_ru")
                or "Параметры → Сертификат: загрузите сертификат с боевого ресурса.",
                "href": "/settings/tls",
                "cta": "Параметры → Сертификат",
            }
        )
    if legacy_keys:
        items.append(
            {
                "id": "secrets",
                "severity": "high",
                "title": "Ключи ещё в базе данных",
                "detail": ops.get("secrets_hint")
                or secrets.get("hint_ru")
                or "Перенесите ключи шифрования в файлы на сервере.",
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
                "title": "Смените токен после волны установок",
                "detail": ops.get("enrollment_rotation_hint")
                or er.get("hint_ru")
                or f"Новых подключений с прошлой смены: {n}.",
                "href": "/settings/updates#enrollment",
                "cta": "Сменить токен",
            }
        )
    if ops.get("mirror_empty") or ops.get("signal_mirror_empty"):
        items.append(
            {
                "id": "mirror",
                "severity": "high",
                "title": "Каталог установщиков пуст",
                "detail": "Агенты не получат обновления.",
                "href": "/settings/updates",
                "cta": "Обновления агента",
            }
        )
    if ops.get("ldap_tls_insecure") or ops.get("signal_ldap_tls_insecure"):
        items.append(
            {
                "id": "ldap_insecure",
                "severity": "high",
                "title": "LDAP без проверки TLS",
                "detail": "Включена опасная проверка сертификата LDAP — только для лаборатории.",
                "href": "/settings/ldap",
                "cta": "Параметры LDAP",
            }
        )
    pin_n = int(ops.get("pinned_missing_count") or 0)
    if pin_n:
        items.append(
            {
                "id": "pin",
                "severity": "high",
                "title": f"Закреплённая версия отсутствует ({pin_n})",
                "detail": "Закреплённая в политике версия отсутствует в каталоге установщиков.",
                "href": "/settings/updates",
                "cta": "Обновления агента",
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
                "cta": "Отстающие по версии",
            }
        )
    revoked_n = int(ops.get("revoked_active") or 0)
    if revoked_n:
        items.append(
            {
                "id": "revoked",
                "severity": "medium",
                "title": f"Отозванные активные ({revoked_n})",
                "detail": "Выпустите новый ключ доступа или отправьте в архив.",
                "href": "/devices?wave=revoked",
                "cta": "Отозванные",
            }
        )
    stale_n = int(stats.get("stale") or 0)
    if stale_n:
        items.append(
            {
                "id": "stale",
                "severity": "low",
                "title": f"Давно не виделись ({stale_n})",
                "detail": "Давно не было связи с сервером.",
                "href": "/devices?wave=stale",
                "cta": "Без связи",
            }
        )
    agent_local_n = int(
        ops.get("agent_local_count") or ops.get("wave_counts", {}).get("agent_local") or 0
    )
    if agent_local_n:
        items.append(
            {
                "id": "agent_local",
                "severity": "low",
                "title": f"Настройка на компьютере ({agent_local_n})",
                "detail": "Параметры заданы локально, не из панели или политики.",
                "href": "/devices?wave=agent_local",
                "cta": "Список устройств",
            }
        )
    return items


def normalize_wave_filter(raw: Optional[str]) -> Optional[str]:
    text = (raw or "").strip().casefold()
    return text if text in WAVE_FILTERS else None


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(100.0 * float(part) / float(whole), 1)


def _top_bars(
    counts: dict[str, int],
    *,
    top: int,
    total: int,
    other_label: str = "прочие",
) -> list[dict[str, Any]]:
    """Top-N + «прочие» для horizontal bars."""
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    items: list[dict[str, Any]] = []
    for label, count in ranked[: max(0, top)]:
        items.append(
            {
                "label": label,
                "count": count,
                "pct": _pct(count, total),
                "is_other": False,
            }
        )
    rest = sum(c for _, c in ranked[top:]) if top >= 0 else 0
    if rest > 0:
        items.append(
            {
                "label": other_label,
                "count": rest,
                "pct": _pct(rest, total),
                "is_other": True,
            }
        )
    return items


def build_wave_counts(
    active: list[dict[str, Any]],
    *,
    ops: dict[str, Any],
    stale_n: int,
) -> dict[str, Any]:
    """O8 / D3: counts волны с deeplink (Обзор — числа; Дашборд — chips)."""
    drift_n = int(ops.get("version_drift_count") or 0)
    revoked_n = int(ops.get("revoked_active") or 0)
    agent_local_n = sum(1 for d in active if device_has_agent_local(d))
    chips = [
        {
            "id": "drift",
            "label": "Дрейф версий",
            "count": drift_n,
            "href": "/devices?wave=drift",
        },
        {
            "id": "revoked",
            "label": "Отозваны",
            "count": revoked_n,
            "href": "/devices?wave=revoked",
        },
        {
            "id": "agent_local",
            "label": "Настройка на компьютере",
            "count": agent_local_n,
            "href": "/devices?wave=agent_local",
        },
        {
            "id": "stale",
            "label": "Устарели",
            "count": int(stale_n),
            "href": "/devices?wave=stale",
        },
    ]
    return {
        "drift": drift_n,
        "revoked": revoked_n,
        "agent_local": agent_local_n,
        "stale": int(stale_n),
        "chips": chips,
    }


def _ram_tier_label(ram_bytes: object) -> Optional[str]:
    try:
        n = int(ram_bytes)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    gb = n / (1024**3)
    if gb < 8:
        return "< 8 ГБ"
    if gb < 16:
        return "8–16 ГБ"
    if gb < 32:
        return "16–32 ГБ"
    if gb < 64:
        return "32–64 ГБ"
    return "64+ ГБ"


def _storage_tier_label(total_bytes: int) -> Optional[str]:
    if total_bytes <= 0:
        return None
    gb = total_bytes / (1024**3)
    if gb < 256:
        return "< 256 ГБ"
    if gb < 512:
        return "256–512 ГБ"
    if gb < 1024:
        return "512 ГБ – 1 ТБ"
    return "1 ТБ+"


def cpu_vendor_bucket(cpu_name: object) -> str:
    text = str(cpu_name or "").casefold()
    if "intel" in text or "xeon" in text or "core i" in text:
        return "Intel"
    if "amd" in text or "ryzen" in text or "epyc" in text:
        return "AMD"
    return "other"


def cpu_family_bucket(cpu_name: object) -> str:
    text = str(cpu_name or "")
    low = text.casefold()
    for pat, label in (
        (r"ryzen\s*9", "Ryzen 9"),
        (r"ryzen\s*7", "Ryzen 7"),
        (r"ryzen\s*5", "Ryzen 5"),
        (r"ryzen\s*3", "Ryzen 3"),
        (r"core\s*i9", "Core i9"),
        (r"core\s*i7", "Core i7"),
        (r"core\s*i5", "Core i5"),
        (r"core\s*i3", "Core i3"),
        (r"xeon", "Xeon"),
    ):
        if re.search(pat, low):
            return label
    return "Прочее"


def device_chart_facets(
    device: dict[str, Any],
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, Optional[str]]:
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    os_caption = str(meta.get("os_caption") or meta.get("os") or "").strip() or None
    cpu_name = str(meta.get("cpu_name") or "").strip()
    hw: dict[str, Any] = {}
    if isinstance(payload, dict):
        raw = payload.get("hardware")
        if isinstance(raw, dict):
            hw = raw
        if not os_caption:
            host = payload.get("host")
            if isinstance(host, dict):
                os_raw = host.get("os")
                if isinstance(os_raw, dict):
                    os_caption = str(os_raw.get("caption") or "").strip() or None
        if not cpu_name:
            cpu = hw.get("cpu") if hw else None
            if isinstance(cpu, dict):
                cpu_name = str(cpu.get("name") or "").strip()
    ram_label = _ram_tier_label(hw.get("ram_bytes") if hw else None)
    total_disk = 0
    for disk in (hw.get("disks") or []) if hw else []:
        if isinstance(disk, dict):
            try:
                total_disk += int(disk.get("size_bytes") or 0)
            except (TypeError, ValueError):
                continue
    disk_label = _storage_tier_label(total_disk) if total_disk else None
    family = cpu_family_bucket(cpu_name) if cpu_name else None
    vendor = cpu_vendor_bucket(cpu_name) if cpu_name else None
    return {
        "os": os_caption,
        "ram": ram_label,
        "disk": disk_label,
        "cpu": family,
        "cpu_vendor": vendor if vendor != "other" else None,
    }


def device_matches_chart_filters(
    facets: dict[str, Optional[str]],
    *,
    os_filter: Optional[str],
    ram_filter: Optional[str],
    disk_filter: Optional[str],
    cpu_filter: Optional[str],
    cpu_vendor_filter: Optional[str],
) -> bool:
    checks = (
        (os_filter, facets.get("os")),
        (ram_filter, facets.get("ram")),
        (disk_filter, facets.get("disk")),
        (cpu_filter, facets.get("cpu")),
        (cpu_vendor_filter, facets.get("cpu_vendor")),
    )
    for want, have in checks:
        if not want:
            continue
        if not have or str(have) != str(want):
            return False
    return True


def chart_filter_href(param: str, value: str, **extra: str) -> str:
    from urllib.parse import urlencode

    params: dict[str, str] = {param: value}
    for key, val in extra.items():
        if val:
            params[key] = val
    return "/devices?" + urlencode(params)


def _treemap_vendor(label: str) -> str:
    if label.startswith("Intel"):
        return "intel"
    if label.startswith("AMD"):
        return "amd"
    return "neutral"


def _treemap_items(
    counts: dict[str, int],
    *,
    href_param: Optional[str] = None,
    href_extra: Optional[dict[str, str]] = None,
    vendor_from_label: bool = False,
) -> list[dict[str, Any]]:
    """Кубики treemap: сортировка по убыванию count; голый Intel/AMD скрываем."""
    total = sum(max(0, int(c)) for c in counts.values()) or 1
    items: list[dict[str, Any]] = []
    for label, count in sorted(counts.items(), key=lambda x: (-int(x[1]), str(x[0]))):
        n = int(count)
        if n <= 0:
            continue
        if label in {"Intel", "AMD"}:
            continue
        row: dict[str, Any] = {
            "label": label,
            "count": n,
            "pct": round(100.0 * n / total, 1),
            "share": round(n / total, 6),
        }
        row["vendor"] = (
            _treemap_vendor(label) if vendor_from_label else "neutral"
        )
        if href_param:
            extra = dict(href_extra or {})
            row["href"] = chart_filter_href(href_param, label, **extra)
        items.append(row)
    return items


def _accumulate_hw_bars(hw: dict[str, Any], ram_counts: dict[str, int], storage_counts: dict[str, int]) -> None:
    if not isinstance(hw, dict):
        return
    ram_label = _ram_tier_label(hw.get("ram_bytes"))
    if ram_label:
        ram_counts[ram_label] = ram_counts.get(ram_label, 0) + 1
    total_disk = 0
    for disk in hw.get("disks") or []:
        if not isinstance(disk, dict):
            continue
        try:
            total_disk += int(disk.get("size_bytes") or 0)
        except (TypeError, ValueError):
            continue
    storage_label = _storage_tier_label(total_disk)
    if storage_label:
        storage_counts[storage_label] = storage_counts.get(storage_label, 0) + 1


def _os_caption_from_device_meta(device: dict[str, Any]) -> Optional[str]:
    """Подпись ОС из meta_json (без inventory), если поле есть."""
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    caption = str(meta.get("os") or meta.get("os_caption") or "").strip()
    return caption or None


def build_dashboard_stats(
    db: Any,
    *,
    stale_after_seconds: int,
    stats: dict[str, Any],
    active: Optional[list[dict[str, Any]]] = None,
    ops: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Агрегаты SSR для /dashboard (конфиги парка). Не публичный /v1."""
    del stale_after_seconds  # silence уже в stats; параметр для симметрии home()
    del ops  # события и дрейф версий — только на Обзоре
    if active is None:
        active = db.list_devices(archived=False)
    total_active = int(stats.get("total_active") or len(active))
    online = int(stats.get("online") or 0)
    archived_n = int(stats.get("archived") or 0)
    offline_n = max(0, total_active - online)

    park_bar = {
        "segments": [
            {
                "id": "online",
                "label": "В сети",
                "count": online,
                "pct": _pct(online, total_active),
                "href": "/devices?fresh=ok",
            },
            {
                "id": "stale",
                "label": "Не в сети",
                "count": offline_n,
                "pct": _pct(offline_n, total_active),
                "href": "/devices?wave=stale",
            },
        ],
        "archived": {"count": archived_n, "href": "/devices?archive=1"},
        "total_active": total_active,
    }

    # OS (cap scan) — нормализованные подписи
    os_counts: dict[str, int] = {}
    ram_counts: dict[str, int] = {}
    storage_counts: dict[str, int] = {}
    for d in active:
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        ram_label = meta.get("ram_bucket")
        if ram_label:
            key = str(ram_label)
            ram_counts[key] = ram_counts.get(key, 0) + 1
        disk_label = meta.get("disk_bucket")
        if disk_label:
            key = str(disk_label)
            storage_counts[key] = storage_counts.get(key, 0) + 1
    scan_cap = min(len(active), INVENTORY_SCAN_CAP)
    scan_ids = [d["device_id"] for d in active[:scan_cap]]
    payloads = db.latest_inventory_payloads(scan_ids, cap=INVENTORY_SCAN_CAP) if scan_ids else {}
    need_payload: list[str] = []
    scanned = 0
    for d in active[:scan_cap]:
        caption = _os_caption_from_device_meta(d)
        if caption:
            scanned += 1
            key = normalize_os_caption(caption)
            os_counts[key] = os_counts.get(key, 0) + 1
        else:
            need_payload.append(d["device_id"])
    for device_id, payload in payloads.items():
        if device_id not in need_payload:
            continue
        scanned += 1
        host = payload.get("host") if isinstance(payload, dict) else None
        if not isinstance(host, dict):
            host = {}
        os_raw = host.get("os")
        if isinstance(os_raw, dict):
            caption = str(os_raw.get("caption") or "").strip()
        elif isinstance(os_raw, str) and os_raw.strip():
            caption = os_raw.strip()
        else:
            caption = ""
        key = normalize_os_caption(caption)
        os_counts[key] = os_counts.get(key, 0) + 1
    missing = max(0, len(scan_ids) - scanned)
    if missing:
        os_counts["Не определена"] = os_counts.get("Не определена", 0) + missing
        scanned += missing

    bar_total = max(scanned, 1)
    capped = len(active) > INVENTORY_SCAN_CAP
    os_items = _top_bars(
        os_counts, top=OS_DOMAIN_BAR_TOP, total=bar_total, other_label="Прочие"
    )
    for row in os_items:
        row["bar_pct"] = max(float(row.get("pct") or 0), 4.0)
        if not row.get("is_other"):
            row["href"] = chart_filter_href("os", str(row.get("label") or ""))
    os_bars = {
        "items": os_items,
        "scanned": scanned,
        "capped": capped,
        "href": "/devices",
        "center_total": total_active,
        "center_label": "ПК",
    }

    def _hbar_block(counts: dict[str, int], param: str) -> Optional[dict[str, Any]]:
        if not counts:
            return None
        total = sum(counts.values())
        items = _top_bars(counts, top=OS_DOMAIN_BAR_TOP, total=max(total, 1))
        for row in items:
            row["bar_pct"] = max(float(row.get("pct") or 0), 4.0)
            if int(row.get("count") or 0) > 0 and not row.get("is_other"):
                row["href"] = chart_filter_href(param, str(row.get("label") or ""))
        return {
            "items": items,
            "scanned": total,
            "capped": capped,
            "href": "/devices",
        }

    ram_bars = _hbar_block(ram_counts, "ram")
    storage_bars = _hbar_block(storage_counts, "disk")

    cpu_family_counts: dict[str, int] = {}
    laptop_model_counts: dict[str, int] = {}
    desktop_model_counts: dict[str, int] = {}
    chassis_counts = {"laptop": 0, "desktop": 0, "other": 0}
    for d in active:
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        fam = resolve_cpu_family(meta)
        if fam:
            cpu_family_counts[fam] = cpu_family_counts.get(fam, 0) + 1
        chassis = str(meta.get("chassis_type") or "").strip().casefold()
        if chassis == "laptop":
            chassis_counts["laptop"] += 1
        elif chassis == "desktop":
            chassis_counts["desktop"] += 1
        else:
            chassis_counts["other"] += 1
        model = str(meta.get("hardware_model") or "").strip()
        if model:
            if chassis == "laptop":
                laptop_model_counts[model] = laptop_model_counts.get(model, 0) + 1
            elif chassis == "desktop":
                desktop_model_counts[model] = desktop_model_counts.get(model, 0) + 1

    cpu_family_treemap = {
        "items": _treemap_items(
            cpu_family_counts, href_param="cpu", vendor_from_label=True
        )
    }
    laptop_model_treemap = {
        "items": _treemap_items(
            laptop_model_counts,
            href_param="model",
            href_extra={"chassis": "laptop"},
        )
    }
    desktop_model_treemap = {
        "items": _treemap_items(
            desktop_model_counts,
            href_param="model",
            href_extra={"chassis": "desktop"},
        )
    }

    return {
        "park_bar": park_bar,
        "os_bars": os_bars,
        "ram_bars": ram_bars,
        "storage_bars": storage_bars,
        "cpu_family_treemap": cpu_family_treemap,
        "laptop_model_treemap": laptop_model_treemap,
        "desktop_model_treemap": desktop_model_treemap,
        "chassis_counts": chassis_counts,
        "gauges": {
            "online_pct": _pct(online, total_active) if total_active else 0,
            "stale_pct": _pct(offline_n, total_active) if total_active else 0,
        },
    }


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
        if wave == "dup":
            # hostname / serial / uuid / bios / board / disk — см. duplicate_signal_index
            return bool(d.get("is_duplicate"))
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
