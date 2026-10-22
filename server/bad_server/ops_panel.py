"""Тема B: bootstrap-чеклист, очередь «требует действия», фильтры волны, победитель конфига.

Только сборка контекста для web UI из уже существующих полей (tls / enrollment / ops /
meta.config_local / sources). Без новых таблиц БД.
Дашборд (/dashboard): агрегаты park/version/wave/os/model (контракт overview-dashboard).
"""

from __future__ import annotations

from typing import Any, Optional

from .agent_config import ALLOWED_SETTING_KEYS, compute_setting_sources
from .device_health import device_silence_status
from .enrollment_ops import enrollment_status
from .tls_ops import tls_panel_mode

WAVE_FILTERS = frozenset({"drift", "revoked", "agent_local", "stale", "dup"})

# Дашборд D1–D5 (согласовано с UI Lead / контрактом)
VERSION_BAR_TOP = 6
OS_DOMAIN_BAR_TOP = 5
MODEL_BAR_TOP = 5
INVENTORY_SCAN_CAP = 500

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
            "label": "Параметры → Сертификат → HTTPS",
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
                "title": "Нужен HTTPS",
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
                "title": "Ключи ещё в БД (SEC-005)",
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
                "title": "Смените токен после волны установок",
                "detail": ops.get("enrollment_rotation_hint")
                or er.get("hint_ru")
                or f"Новых подключений с прошлой смены: {n}.",
                "href": "/settings/updates#enrollment",
                "cta": "Сменить токен",
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
            "label": "agent_local",
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


def _facet_from_device_meta(device: dict[str, Any]) -> tuple[str, str, str] | None:
    """OS / domain / model из meta_json (без inventory), если поля есть."""
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    os_caption = str(meta.get("os") or meta.get("os_caption") or "").strip()
    domain = str(meta.get("domain") or "").strip()
    mfr = str(meta.get("hardware_manufacturer") or meta.get("manufacturer") or "").strip()
    model = str(meta.get("hardware_model") or meta.get("model") or "").strip()
    if not os_caption and not domain and not (mfr or model):
        return None
    model_label = " · ".join(x for x in (mfr, model) if x) or "—"
    return (
        os_caption or "—",
        domain or "—",
        model_label,
    )


def build_dashboard_stats(
    db: Any,
    *,
    stale_after_seconds: int,
    stats: dict[str, Any],
    ops: dict[str, Any],
    active: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Агрегаты SSR для /dashboard (D1–D5). Не публичный /v1.

    Поля: park_bar, agent_version_bars, wave_chips, os_bars, domain_bars,
    model_bars, hardware_feed, mirror. См. server-lead-overview-dashboard.md.
    """
    del stale_after_seconds  # silence уже в stats; параметр для симметрии home()
    if active is None:
        active = db.list_devices(archived=False)
    total_active = int(stats.get("total_active") or len(active))
    online = int(stats.get("online") or 0)
    stale_n = int(stats.get("stale") or 0)
    archived_n = int(stats.get("archived") or 0)

    # D1 — park bar (архив aside)
    park_bar = {
        "segments": [
            {
                "id": "online",
                "label": "Онлайн",
                "count": online,
                "pct": _pct(online, total_active),
                "href": "/devices",
            },
            {
                "id": "stale",
                "label": "Устарели",
                "count": stale_n,
                "pct": _pct(stale_n, total_active),
                "href": "/devices?wave=stale",
            },
        ],
        "archived": {
            "count": archived_n,
            "href": "/devices?archive=1",
        },
        "total_active": total_active,
    }

    # D2 — version bars
    ver_counts: dict[str, int] = {}
    for row in stats.get("agent_versions") or []:
        ver_counts[str(row.get("version") or "—")] = int(row.get("count") or 0)
    version_items = [
        {
            "version": item["label"],
            "count": item["count"],
            "pct": item["pct"],
            "is_other": item["is_other"],
        }
        for item in _top_bars(ver_counts, top=VERSION_BAR_TOP, total=total_active)
    ]
    agent_version_bars = {
        "items": version_items,
        "latest": ops.get("latest_version"),
        "drift_count": int(ops.get("version_drift_count") or 0),
        "drift_href": "/devices?wave=drift",
        "total": total_active,
        "version_count": len(ver_counts),
    }

    # D3 — wave chips
    wave = build_wave_counts(active, ops=ops, stale_n=stale_n)
    wave_chips = wave["chips"]

    # D4 / D5 — OS / domain / model (cap scan)
    os_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    model_counts: dict[str, int] = {}
    scan_cap = min(len(active), INVENTORY_SCAN_CAP)
    need_payload: list[str] = []
    scanned = 0
    for d in active[:scan_cap]:
        facets = _facet_from_device_meta(d)
        if facets:
            caption, domain, model_label = facets
            scanned += 1
            os_counts[caption] = os_counts.get(caption, 0) + 1
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            model_counts[model_label] = model_counts.get(model_label, 0) + 1
        else:
            need_payload.append(d["device_id"])
    payloads = (
        db.latest_inventory_payloads(need_payload, cap=INVENTORY_SCAN_CAP)
        if need_payload
        else {}
    )
    for device_id, payload in payloads.items():
        scanned += 1
        host = payload.get("host") if isinstance(payload, dict) else None
        if not isinstance(host, dict):
            host = {}
        os_raw = host.get("os")
        if isinstance(os_raw, dict):
            caption = str(os_raw.get("caption") or "").strip() or "—"
        elif isinstance(os_raw, str) and os_raw.strip():
            caption = os_raw.strip()
        else:
            caption = "—"
        domain = str(host.get("domain") or "").strip() or "—"
        hw = payload.get("hardware") if isinstance(payload, dict) else None
        if not isinstance(hw, dict):
            hw = {}
        model_label = " · ".join(
            str(x).strip()
            for x in (hw.get("manufacturer"), hw.get("model"))
            if x and str(x).strip()
        ) or "—"
        os_counts[caption] = os_counts.get(caption, 0) + 1
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        model_counts[model_label] = model_counts.get(model_label, 0) + 1
    scan_ids = [d["device_id"] for d in active[:INVENTORY_SCAN_CAP]]
    missing = max(0, len(scan_ids) - scanned)
    if missing:
        os_counts["—"] = os_counts.get("—", 0) + missing
        domain_counts["—"] = domain_counts.get("—", 0) + missing
        model_counts["—"] = model_counts.get("—", 0) + missing
        scanned += missing

    bar_total = max(scanned, 1)
    capped = len(active) > INVENTORY_SCAN_CAP
    os_bars = {
        "items": _top_bars(os_counts, top=OS_DOMAIN_BAR_TOP, total=bar_total),
        "scanned": scanned,
        "capped": capped,
        "href": "/devices",
    }
    domain_bars = {
        "items": _top_bars(domain_counts, top=OS_DOMAIN_BAR_TOP, total=bar_total),
        "scanned": scanned,
        "capped": capped,
        "href": "/devices",
    }
    model_bars = {
        "items": _top_bars(model_counts, top=MODEL_BAR_TOP, total=bar_total),
        "scanned": scanned,
        "capped": capped,
        "href": "/devices",
    }

    # hardware feed (на Дашборде — опц.; Обзор держит список O7)
    hw_items = list(stats.get("recent_hardware_events") or [])[:8]
    hardware_feed = {
        "items": hw_items,
        "href": "/events",
        "empty": not hw_items,
    }

    mirror = {
        "empty": bool(ops.get("mirror_empty")),
        "latest_version": ops.get("latest_version"),
        "count": int(ops.get("mirror_count") or 0),
        "synced_at": ops.get("latest_synced_at"),
        "href": "/settings/updates",
    }

    return {
        "park_bar": park_bar,
        "agent_version_bars": agent_version_bars,
        "wave_chips": wave_chips,
        "wave_counts": {
            "drift": wave["drift"],
            "revoked": wave["revoked"],
            "agent_local": wave["agent_local"],
            "stale": wave["stale"],
        },
        "os_bars": os_bars,
        "domain_bars": domain_bars,
        "model_bars": model_bars,
        "hardware_feed": hardware_feed,
        "mirror": mirror,
    }


# Совместимое имя для старых ссылок на агрегатор.
build_overview_dashboard = build_dashboard_stats


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
