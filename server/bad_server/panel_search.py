"""Поиск по парку и событиям (Обзор / live UI)."""

from __future__ import annotations

import html
import re
from typing import Any, Optional

from .device_meta import (
    collect_hardware_serials,
    meta_search_haystack,
    normalize_logged_on_list,
    normalize_search_serial,
)


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
    ("IdentifyingNumber", "identifying_number"),
    ("serial платы", "baseboard_serial"),
    ("процессор", "cpu_name"),
    ("модель", "hardware_model"),
    ("производитель", "hardware_manufacturer"),
    ("пользователь", "logged_on"),
    ("IPv4", "ipv4_addresses"),
    ("MAC", "mac_addresses"),
    ("тег", "tags"),
)

_SERIAL_LIST_FIELDS: tuple[tuple[str, str], ...] = (
    ("serial диска", "disk_serials"),
    ("serial монитора", "monitor_serials"),
    ("serial ОЗУ", "ram_serials"),
    ("серийный номер", "search_serials"),
)


def _serial_match_in_lists(meta: dict[str, Any], q: str) -> Optional[str]:
    for label, key in _SERIAL_LIST_FIELDS:
        for val in meta.get(key) or []:
            if q in str(val).casefold():
                return label
    return None


def _serial_match_in_hardware(hardware: Optional[dict[str, Any]], q: str) -> Optional[str]:
    if not isinstance(hardware, dict):
        return None
    serials = collect_hardware_serials(hardware)
    for label, key in (
        ("серийный номер", "chassis"),
        ("serial диска", "disk_serials"),
        ("serial монитора", "monitor_serials"),
        ("serial ОЗУ", "ram_serials"),
    ):
        for val in serials.get(key) or []:
            if q in str(val).casefold():
                return label
    return None


def device_match_label(
    device: dict[str, Any],
    query: str,
    *,
    hardware: Optional[dict[str, Any]] = None,
) -> str:
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
    serial_hit = _serial_match_in_lists(meta, q)
    if serial_hit:
        return serial_hit
    hw_hit = _serial_match_in_hardware(hardware, q)
    if hw_hit:
        return hw_hit
    tags = device.get("tags") or []
    for t in tags:
        if q in str(t).casefold():
            return "тег"
    if q in meta_search_haystack(meta):
        return "совпадение"
    # сырой query в любом серийнике из hardware (на случай частичного ILIKE по payload)
    if isinstance(hardware, dict):
        blob = str(hardware).casefold()
        if q in blob and "serial" in blob:
            return "серийный номер"
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


def matched_serial_subtitle(
    device: dict[str, Any],
    query: str,
    *,
    hardware: Optional[dict[str, Any]] = None,
) -> str:
    """Подпись в выдаче: какой именно серийник совпал."""
    q = (query or "").strip().casefold()
    if not q:
        return device_search_meta_line(device)
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    candidates: list[tuple[str, str]] = []
    for label, key in (
        ("ПК", "serial_number"),
        ("BIOS", "bios_serial"),
        ("плата", "baseboard_serial"),
        ("UUID", "smbios_uuid"),
    ):
        val = normalize_search_serial(meta.get(key))
        if val and q in val.casefold():
            candidates.append((label, val))
    for label, key in (
        ("диск", "disk_serials"),
        ("монитор", "monitor_serials"),
        ("ОЗУ", "ram_serials"),
    ):
        for raw in meta.get(key) or []:
            val = normalize_search_serial(raw)
            if val and q in val.casefold():
                candidates.append((label, val))
    if not candidates and isinstance(hardware, dict):
        serials = collect_hardware_serials(hardware)
        for label, key in (
            ("ПК", "chassis"),
            ("диск", "disk_serials"),
            ("монитор", "monitor_serials"),
            ("ОЗУ", "ram_serials"),
        ):
            for val in serials.get(key) or []:
                if q in str(val).casefold():
                    candidates.append((label, str(val)))
    if candidates:
        kind, value = candidates[0]
        return f"{kind}: {value}"
    return device_search_meta_line(device) or device_match_label(
        device, query, hardware=hardware
    )
