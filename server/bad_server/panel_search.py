"""Поиск по парку и событиям (Обзор / live UI)."""

from __future__ import annotations

import html
import re
from typing import Any, Optional

from .device_meta import meta_search_haystack, normalize_logged_on_list


def device_search_meta_line(device: dict[str, Any]) -> str:
    """Краткая meta-строка для выдачи поиска (пользователь, CPU, serial)."""
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    parts: list[str] = []
    logged = normalize_logged_on_list(meta.get("logged_on"))
    if logged:
        parts.append(logged[0])
    cpu = str(meta.get("cpu_name") or "").strip()
    if cpu:
        parts.append(cpu)
    serial = str(meta.get("serial_number") or "").strip()
    if serial:
        parts.append(serial)
    return " · ".join(parts)

_MATCH_FIELDS: tuple[tuple[str, str], ...] = (
    ("имя", "hostname"),
    ("идентификатор", "device_id"),
    ("серийный номер", "serial_number"),
    ("UUID", "smbios_uuid"),
    ("BIOS", "bios_serial"),
    ("процессор", "cpu_name"),
    ("модель", "hardware_model"),
    ("производитель", "hardware_manufacturer"),
    ("пользователь", "logged_on"),
    ("IPv4", "ipv4_addresses"),
    ("MAC", "mac_addresses"),
    ("тег", "tags"),
)


def device_match_label(device: dict[str, Any], query: str) -> str:
    q = (query or "").strip().casefold()
    if not q:
        return ""
    host = (device.get("hostname") or "").casefold()
    did = str(device.get("device_id") or "").casefold()
    if q in host:
        return "имя"
    if q in did:
        return "идентификатор"
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    for label, key in _MATCH_FIELDS[2:]:
        if key == "logged_on":
            for user in normalize_logged_on_list(meta.get("logged_on")):
                if q in user.casefold():
                    return label
            continue
        if key in {"ipv4_addresses", "mac_addresses"}:
            for val in meta.get(key) or []:
                if q in str(val).casefold():
                    return label
            continue
        val = str(meta.get(key) or "").casefold()
        if val and q in val:
            return label
    tags = device.get("tags") or []
    for t in tags:
        if q in str(t).casefold():
            return "тег"
    if q in meta_search_haystack(meta):
        return "совпадение"
    return "совпадение"


def highlight_match(text: str, query: str) -> str:
    """Экранированный фрагмент с <mark> вокруг первого вхождения query."""
    raw = str(text or "")
    q = (query or "").strip()
    if not raw or not q:
        return html.escape(raw)
    try:
        m = re.search(re.escape(q), raw, flags=re.IGNORECASE)
    except re.error:
        return html.escape(raw)
    if not m:
        return html.escape(raw)
    start, end = m.span()
    return (
        html.escape(raw[:start])
        + "<mark>"
        + html.escape(raw[start:end])
        + "</mark>"
        + html.escape(raw[end:])
    )


def event_match_label(event: dict[str, Any], query: str) -> str:
    q = (query or "").strip().casefold()
    if not q:
        return ""
    for key in ("summary", "type", "hostname", "device_id"):
        val = str(event.get(key) or "").casefold()
        if q in val:
            if key == "summary":
                return "описание"
            if key == "type":
                return "тип"
            if key == "hostname":
                return "имя"
            return "идентификатор"
    return "совпадение"
