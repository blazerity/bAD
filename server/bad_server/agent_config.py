"""Удалённые настройки агента: defaults, сопоставление политик, merge эффективного конфига."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

# Безопасные knobs, которые можно пушить enrolled-агенту (никогда secrets / URLs / ids).
# update_target: "latest" | конкретный semver из зеркала MSI на сервере (epic 0.10).
# Сервер резолвит цель в /v1/agent/update/check; агент применяет target (в т.ч. downgrade).
UPDATE_TARGET_LATEST = "latest"
_SEMVER_TARGET_RE = re.compile(r"^v?(?P<ver>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)$")

DEFAULT_AGENT_SETTINGS: dict[str, Any] = {
    "inventory_interval_hours": 6,
    "heartbeat_interval_minutes": 15,
    "update_check_interval_hours": 24,
    "update_enabled": True,
    "update_target": UPDATE_TARGET_LATEST,
    # Hardware/users по умолчанию включены (прежнее поведение); software — opt-in.
    "collect_hardware": True,
    "collect_users": True,
    "collect_software": False,
}

ALLOWED_SETTING_KEYS = frozenset(DEFAULT_AGENT_SETTINGS.keys())

BOOL_SETTING_KEYS = frozenset(
    {
        "update_enabled",
        "collect_hardware",
        "collect_users",
        "collect_software",
    }
)

INT_SETTING_KEYS = frozenset(
    {
        "inventory_interval_hours",
        "heartbeat_interval_minutes",
        "update_check_interval_hours",
    }
)

STRING_SETTING_KEYS = frozenset({"update_target"})

# Provenance enum for UI (docs/architecture — config source); remote merge unchanged.
CONFIG_SOURCES = frozenset(
    {"default", "policy", "device_override", "agent_local"}
)
# Secrets never accepted inside config_local (strip / ignore).
CONFIG_LOCAL_FORBIDDEN_KEYS = frozenset({"api_key", "enrollment_token"})
MAX_CONFIG_LOCAL_SERVER_URL_LEN = 2048


def sanitize_update_target(value: Any) -> Optional[str]:
    """Нормализовать цель обновления: latest или semver."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.casefold() in {UPDATE_TARGET_LATEST, "newest", "*"}:
        return UPDATE_TARGET_LATEST
    m = _SEMVER_TARGET_RE.match(text)
    if not m:
        return None
    return m.group("ver")


CONDITION_FIELDS = frozenset({"hostname", "domain", "os_caption", "tag"})
CONDITION_OPS = frozenset({"equals", "contains"})

_TRUE_STRINGS = frozenset({"1", "true", "yes"})
_FALSE_STRINGS = frozenset({"0", "false", "no"})


def _parse_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE_STRINGS:
            return True
        if text in _FALSE_STRINGS:
            return False
    return None


def sanitize_settings(raw: Any) -> dict[str, Any]:
    """Оставить только известные ключи с проверенными типами/диапазонами."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in ALLOWED_SETTING_KEYS:
            continue
        if key in BOOL_SETTING_KEYS:
            parsed = _parse_bool(value)
            if parsed is not None:
                out[key] = parsed
            continue
        if key in INT_SETTING_KEYS:
            try:
                n = int(value)
            except (TypeError, ValueError):
                continue
            if n >= 1:
                out[key] = n
            continue
        if key in STRING_SETTING_KEYS:
            if key == "update_target":
                parsed = sanitize_update_target(value)
                if parsed is not None:
                    out[key] = parsed
    return out


def sanitize_conditions(raw: Any) -> list[dict[str, str]]:
    """Нормализовать условия политики; отбросить невалидные."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field", "")).strip().lower()
        op = str(item.get("op", "")).strip().lower()
        value = item.get("value")
        if field not in CONDITION_FIELDS or op not in CONDITION_OPS:
            continue
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        out.append({"field": field, "op": op, "value": text})
    return out


def device_match_context(
    *,
    hostname: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    inventory_payload: Optional[dict[str, Any]] = None,
    tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Собрать поля сопоставления из строки device + последнего inventory + tags."""
    from .device_health import normalize_tags

    meta = meta or {}
    host: dict[str, Any] = {}
    if inventory_payload and isinstance(inventory_payload.get("host"), dict):
        host = inventory_payload["host"]

    os_caption = ""
    os_info = host.get("os")
    if isinstance(os_info, dict):
        os_caption = str(os_info.get("caption") or "")
    if not os_caption and meta.get("os"):
        os_caption = str(meta.get("os") or "")

    domain = ""
    if host.get("domain") is not None:
        domain = str(host.get("domain") or "")

    hn = hostname or (str(host.get("hostname") or "") if host else "") or ""
    # ad_ou — в inventory (display/context). Match-поле OU в CONDITION_FIELDS
    # не входит: контракт C = tag|hostname|domain|os_caption (OU — отдельный kickoff).
    ad_ou = ""
    if host.get("ad_ou") is not None:
        ad_ou = str(host.get("ad_ou") or "").strip()
    if not ad_ou and host.get("ad_distinguished_name") is not None:
        ad_ou = str(host.get("ad_distinguished_name") or "").strip()
    # tag — список; equals = членство, contains = подстрока любого тега.
    return {
        "hostname": hn,
        "domain": domain,
        "os_caption": os_caption,
        "tag": normalize_tags(tags),
        "ad_ou": ad_ou,
    }


def condition_matches(condition: dict[str, str], context: dict[str, Any]) -> bool:
    field = condition["field"]
    op = condition["op"]
    expected = condition["value"]
    if field == "tag":
        raw = context.get("tag") or []
        tags = raw if isinstance(raw, list) else [str(raw)]
        if op == "equals":
            return any(str(t).casefold() == expected.casefold() for t in tags)
        if op == "contains":
            return any(expected.casefold() in str(t).casefold() for t in tags)
        return False
    actual = str(context.get(field, "") or "")
    if op == "equals":
        return actual.casefold() == expected.casefold()
    if op == "contains":
        return expected.casefold() in actual.casefold()
    return False


def policy_matches(conditions: list[dict[str, str]], context: dict[str, Any]) -> bool:
    """Все условия должны совпасть (AND). Пустые условия не совпадают."""
    if not conditions:
        return False
    return all(condition_matches(c, context) for c in conditions)


def config_version(settings: dict[str, Any]) -> str:
    payload = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def sanitize_config_local(raw: Any) -> dict[str, Any]:
    """Sanitize inbound heartbeat ``config_local`` for meta storage (no reported_at).

    ``keys`` is the source of truth for agent_local; unknown / forbidden dropped.
    Empty ``keys`` means clear agent_local on store.
    """
    if not isinstance(raw, dict):
        return {"keys": [], "settings": {}}

    keys: list[str] = []
    seen: set[str] = set()
    raw_keys = raw.get("keys")
    if isinstance(raw_keys, list):
        for item in raw_keys:
            name = str(item).strip()
            if not name or name in CONFIG_LOCAL_FORBIDDEN_KEYS:
                continue
            if name not in ALLOWED_SETTING_KEYS or name in seen:
                continue
            seen.add(name)
            keys.append(name)
            if len(keys) >= len(ALLOWED_SETTING_KEYS):
                break

    settings: dict[str, Any] = {}
    raw_settings = raw.get("settings")
    if isinstance(raw_settings, dict) and keys:
        filtered = {
            k: v
            for k, v in raw_settings.items()
            if k in seen and k not in CONFIG_LOCAL_FORBIDDEN_KEYS
        }
        settings = sanitize_settings(filtered)

    out: dict[str, Any] = {"keys": keys, "settings": settings}
    url = raw.get("server_url")
    if isinstance(url, str):
        text = url.strip()
        if (
            text
            and len(text) <= MAX_CONFIG_LOCAL_SERVER_URL_LEN
            and "\n" not in text
            and "\r" not in text
        ):
            out["server_url"] = text[:MAX_CONFIG_LOCAL_SERVER_URL_LEN]
    return out


def config_local_from_meta(meta: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Return stored config_local if it has keys and/or display-only server_url."""
    if not meta or not isinstance(meta, dict):
        return None
    raw = meta.get("config_local")
    if not isinstance(raw, dict):
        return None
    keys = [
        str(k)
        for k in (raw.get("keys") or [])
        if str(k) in ALLOWED_SETTING_KEYS
    ]
    key_set = set(keys)
    settings = {
        k: v
        for k, v in sanitize_settings(raw.get("settings") or {}).items()
        if k in key_set
    }
    out: dict[str, Any] = {"keys": keys, "settings": settings}
    url = raw.get("server_url")
    if isinstance(url, str) and url.strip():
        out["server_url"] = url.strip()[:MAX_CONFIG_LOCAL_SERVER_URL_LEN]
    reported = raw.get("reported_at")
    if isinstance(reported, str) and reported.strip():
        out["reported_at"] = reported.strip()
    # Empty keys alone is not agent_local knobs; keep block if server_url present.
    if not keys and "server_url" not in out:
        return None
    return out


def compute_setting_sources(
    *,
    policy_keys: set[str],
    override_keys: set[str],
    agent_local_keys: Optional[list[str]] = None,
) -> dict[str, str]:
    """UI provenance map for every ALLOWED_SETTING_KEYS entry.

    Precedence for label only: agent_local > device_override > policy > default.
    Does not change remote effective merge.
    """
    sources = {key: "default" for key in ALLOWED_SETTING_KEYS}
    for key in policy_keys:
        if key in sources:
            sources[key] = "policy"
    for key in override_keys:
        if key in sources:
            sources[key] = "device_override"
    for key in agent_local_keys or []:
        if key in sources:
            sources[key] = "agent_local"
    return sources


def provenance_from_effective(
    effective: dict[str, Any],
    *,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Attach sources / agent_local_* / config_local for admin + web device context."""
    stored = config_local_from_meta(meta)
    agent_local_keys = list((stored or {}).get("keys") or [])
    sources = compute_setting_sources(
        policy_keys=set(effective.get("policy_keys") or []),
        override_keys=set(effective.get("override_keys") or []),
        agent_local_keys=agent_local_keys,
    )
    return {
        "sources": sources,
        "agent_local_keys": agent_local_keys,
        "has_agent_local": bool(agent_local_keys),
        "config_local": stored,
    }


def compute_effective_config(
    *,
    hostname: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    inventory_payload: Optional[dict[str, Any]] = None,
    tags: Optional[list[str]] = None,
    policies: list[dict[str, Any]],
    override: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """defaults < совпавшие политики (по возрастанию priority) < per-device override.

    Каждый dict политики: {enabled, priority, conditions (list|json), settings (dict|json)}.
    Меньший priority применяется раньше; более поздние совпавшие политики перекрывают ранние.
    """
    effective = dict(DEFAULT_AGENT_SETTINGS)
    context = device_match_context(
        hostname=hostname,
        meta=meta,
        inventory_payload=inventory_payload,
        tags=tags,
    )

    ordered = sorted(
        policies,
        key=lambda p: (
            int(p.get("priority") if p.get("priority") is not None else 100),
            int(p.get("id") or 0),
        ),
    )
    matched: list[dict[str, Any]] = []
    policy_keys: set[str] = set()
    for policy in ordered:
        if not policy.get("enabled", True):
            continue
        conditions = policy.get("conditions")
        if isinstance(conditions, str):
            try:
                conditions = json.loads(conditions)
            except json.JSONDecodeError:
                conditions = []
        conditions = sanitize_conditions(conditions)
        if not policy_matches(conditions, context):
            continue
        settings = policy.get("settings")
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except json.JSONDecodeError:
                settings = {}
        patch = sanitize_settings(settings)
        if patch:
            effective.update(patch)
            policy_keys.update(patch.keys())
            matched.append(
                {
                    "id": policy.get("id"),
                    "name": policy.get("name"),
                    "priority": policy.get("priority"),
                }
            )

    override_clean = sanitize_settings(override or {})
    if override_clean:
        effective.update(override_clean)

    sources = compute_setting_sources(
        policy_keys=policy_keys,
        override_keys=set(override_clean.keys()),
        agent_local_keys=None,
    )

    return {
        "settings": effective,
        "version": config_version(effective),
        "matched_policies": matched,
        "has_override": bool(override_clean),
        "context": context,
        "policy_keys": sorted(policy_keys),
        "override_keys": sorted(override_clean.keys()),
        "sources": sources,
    }
