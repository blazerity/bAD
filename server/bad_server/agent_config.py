"""Remote agent settings: defaults, policy match, effective config merge."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

# Safe knobs that may be pushed to an enrolled agent (never secrets / URLs / ids).
DEFAULT_AGENT_SETTINGS: dict[str, Any] = {
    "inventory_interval_hours": 6,
    "heartbeat_interval_minutes": 15,
    "update_check_interval_hours": 24,
    "update_enabled": True,
    # Hardware/users stay on by default (preserve prior behavior); software is opt-in.
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

CONDITION_FIELDS = frozenset({"hostname", "domain", "os_caption"})
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
    """Keep only known keys with validated types/ranges."""
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
    return out


def sanitize_conditions(raw: Any) -> list[dict[str, str]]:
    """Normalize policy conditions; drop invalid entries."""
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
) -> dict[str, str]:
    """Build lowercase match fields from device row + latest inventory."""
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

    return {
        "hostname": hn,
        "domain": domain,
        "os_caption": os_caption,
    }


def condition_matches(condition: dict[str, str], context: dict[str, str]) -> bool:
    field = condition["field"]
    op = condition["op"]
    expected = condition["value"]
    actual = context.get(field, "") or ""
    if op == "equals":
        return actual.casefold() == expected.casefold()
    if op == "contains":
        return expected.casefold() in actual.casefold()
    return False


def policy_matches(conditions: list[dict[str, str]], context: dict[str, str]) -> bool:
    """All conditions must match (AND). Empty conditions never match."""
    if not conditions:
        return False
    return all(condition_matches(c, context) for c in conditions)


def config_version(settings: dict[str, Any]) -> str:
    payload = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_effective_config(
    *,
    hostname: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    inventory_payload: Optional[dict[str, Any]] = None,
    policies: list[dict[str, Any]],
    override: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """defaults < matching policies (ascending priority) < per-device override.

    Each policy dict: {enabled, priority, conditions (list|json), settings (dict|json)}.
    Lower priority number wins earlier; later matching policies override earlier ones.
    """
    effective = dict(DEFAULT_AGENT_SETTINGS)
    context = device_match_context(
        hostname=hostname, meta=meta, inventory_payload=inventory_payload
    )

    ordered = sorted(
        policies,
        key=lambda p: (
            int(p.get("priority") if p.get("priority") is not None else 100),
            int(p.get("id") or 0),
        ),
    )
    matched: list[dict[str, Any]] = []
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

    return {
        "settings": effective,
        "version": config_version(effective),
        "matched_policies": matched,
        "has_override": bool(override_clean),
        "context": context,
    }
