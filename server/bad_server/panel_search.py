"""Поиск по парку и событиям (Обзор / live UI)."""

from __future__ import annotations

import html
import re
from typing import Any, Optional

from .device_meta import (
    collect_hardware_serials,
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
    ("Имя", "hostname"),
    ("Идентификатор", "bad_id"),
    ("Серийный номер", "serial_number"),
    ("UUID", "smbios_uuid"),
    ("Серийный номер", "bios_serial"),
    ("Серийный номер", "identifying_number"),
    ("Плата", "baseboard_serial"),
    ("Процессор", "cpu_name"),
    ("Модель", "hardware_model"),
    ("Производитель", "hardware_manufacturer"),
    ("Пользователь", "logged_on"),
    ("IPv4", "ipv4_addresses"),
    ("MAC", "mac_addresses"),
    ("Тег", "tags"),
)

_SERIAL_LIST_FIELDS: tuple[tuple[str, str], ...] = (
    ("Диск", "disk_serials"),
    ("Монитор", "monitor_serials"),
    ("Память", "ram_serials"),
    ("Серийный номер", "search_serials"),
)


def _first_folded_hit(values: object, q: str) -> Optional[str]:
    for val in values or []:
        text = str(val)
        if text and q in text.casefold():
            return text
    return None


def _serial_match_in_lists(meta: dict[str, Any], q: str) -> Optional[tuple[str, str]]:
    for label, key in _SERIAL_LIST_FIELDS:
        hit = _first_folded_hit(meta.get(key), q)
        if hit:
            return label, hit
    return None


def _serial_match_in_hardware(
    hardware: Optional[dict[str, Any]], q: str
) -> Optional[tuple[str, str]]:
    if not isinstance(hardware, dict):
        return None
    serials = collect_hardware_serials(hardware)
    for label, key in (
        ("Серийный номер", "chassis"),
        ("Диск", "disk_serials"),
        ("Монитор", "monitor_serials"),
        ("Память", "ram_serials"),
    ):
        hit = _first_folded_hit(serials.get(key), q)
        if hit:
            return label, hit
    return None


def device_match_parts(
    device: dict[str, Any],
    query: str,
    *,
    hardware: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    """Подпись параметра и совпавшее значение. Нет совпадения — две пустые строки."""
    q = (query or "").strip().casefold()
    if not q:
        return "", ""
    host = str(device.get("hostname") or "")
    did = str(device.get("bad_id") or "")
    if host and q in host.casefold():
        return "Имя", host
    if did and q in did.casefold():
        return "Идентификатор", did
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    for label, key in _MATCH_FIELDS[2:]:
        if key == "logged_on":
            hit = _first_folded_hit(normalize_logged_on_list(meta.get("logged_on")), q)
            if hit:
                return label, hit
            continue
        if key in {"ipv4_addresses", "mac_addresses"}:
            hit = _first_folded_hit(meta.get(key), q)
            if hit:
                return label, hit
            continue
        raw = str(meta.get(key) or "")
        if raw and q in raw.casefold():
            return label, raw
    serial_hit = _serial_match_in_lists(meta, q)
    if serial_hit:
        return serial_hit
    hw_hit = _serial_match_in_hardware(hardware, q)
    if hw_hit:
        return hw_hit
    for tag in device.get("tags") or []:
        text = str(tag)
        if text and q in text.casefold():
            return "Тег", text
    return "", ""


def device_match_label(
    device: dict[str, Any],
    query: str,
    *,
    hardware: Optional[dict[str, Any]] = None,
) -> str:
    return device_match_parts(device, query, hardware=hardware)[0]


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
    for key in ("summary", "type", "hostname", "bad_id"):
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
        ("Серийный номер", "serial_number"),
        ("Серийный номер", "bios_serial"),
        ("Плата", "baseboard_serial"),
        ("UUID", "smbios_uuid"),
    ):
        val = normalize_search_serial(meta.get(key))
        if val and q in val.casefold():
            candidates.append((label, val))
    for label, key in (
        ("Диск", "disk_serials"),
        ("Монитор", "monitor_serials"),
        ("Память", "ram_serials"),
    ):
        for raw in meta.get(key) or []:
            val = normalize_search_serial(raw)
            if val and q in val.casefold():
                candidates.append((label, val))
    if not candidates and isinstance(hardware, dict):
        serials = collect_hardware_serials(hardware)
        for label, key in (
            ("Серийный номер", "chassis"),
            ("Диск", "disk_serials"),
            ("Монитор", "monitor_serials"),
            ("Память", "ram_serials"),
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
