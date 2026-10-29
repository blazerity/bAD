"""Кэш полей inventory в devices.meta (списки без полного snapshot)."""

from __future__ import annotations

from typing import Any, Optional

from .fleet_buckets import (
    cpu_family_label,
    cpu_vendor_label,
    disk_bucket_from_fixed_bytes,
    format_ram_gib,
    ram_bucket,
    sort_ipv4_addresses,
    sum_fixed_disk_bytes,
)

CHASSIS_TYPES = frozenset({"laptop", "desktop", "server", "vm", "other"})

# Placeholder / мусор WMI — не индексируем в поиск
_SERIAL_PLACEHOLDERS = frozenset(
    {
        "",
        "none",
        "n/a",
        "na",
        "null",
        "unknown",
        "to be filled by o.e.m.",
        "to be filled by oem",
        "default string",
        "system serial number",
        "chassis serial number",
        "base board serial number",
        "0",
        "00000000",
        "0000000000000000",
    }
)


def normalize_search_serial(raw: object) -> Optional[str]:
    """Очистить серийник для индекса поиска (мониторы/диски/ОЗУ/плата)."""
    text = str(raw or "").strip()
    if not text:
        return None
    if text.casefold() in _SERIAL_PLACEHOLDERS:
        return None
    return text


def collect_hardware_serials(hardware: Optional[dict[str, Any]]) -> dict[str, list[str]]:
    """Все серийники из снимка hardware: ПК, BIOS, плата, диски, мониторы, ОЗУ."""
    out: dict[str, list[str]] = {
        "chassis": [],
        "disk_serials": [],
        "monitor_serials": [],
        "ram_serials": [],
        "all": [],
    }
    if not isinstance(hardware, dict):
        return out
    seen_all: set[str] = set()
    seen_bucket: dict[str, set[str]] = {
        "chassis": set(),
        "disk_serials": set(),
        "monitor_serials": set(),
        "ram_serials": set(),
    }

    def _add(bucket: str, raw: object) -> None:
        serial = normalize_search_serial(raw)
        if not serial:
            return
        key = serial.casefold()
        bucket_seen = seen_bucket[bucket]
        if key not in bucket_seen:
            bucket_seen.add(key)
            out[bucket].append(serial)
        if key not in seen_all:
            seen_all.add(key)
            out["all"].append(serial)

    for key in (
        "serial_number",
        "bios_serial",
        "identifying_number",
        "baseboard_serial",
        "smbios_uuid",
    ):
        _add("chassis", hardware.get(key))

    for disk in hardware.get("disks") or []:
        if isinstance(disk, dict):
            _add("disk_serials", disk.get("serial_number"))

    for mon in hardware.get("monitors") or []:
        if isinstance(mon, dict):
            _add("monitor_serials", mon.get("serial_number"))

    for mod in hardware.get("ram_modules") or []:
        if isinstance(mod, dict):
            _add("ram_serials", mod.get("serial_number"))

    return out


def normalize_logged_on_user(entry: object) -> Optional[str]:
    """Строка для UI/поиска: str, либо dict с username/user и опционально domain."""
    if entry is None:
        return None
    if isinstance(entry, dict):
        username = str(entry.get("username") or entry.get("user") or "").strip()
        if not username:
            upn = str(entry.get("upn") or "").strip()
            return upn or None
        domain = str(entry.get("domain") or "").strip()
        if domain and "\\" not in username and "@" not in username:
            return f"{domain}\\{username}"
        return username
    text = str(entry).strip()
    return text or None


def normalize_logged_on_list(entries: object) -> list[str]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        entries = [entries]
    out: list[str] = []
    for item in entries:
        name = normalize_logged_on_user(item)
        if name:
            out.append(name)
    return out


def format_logged_on_display(entries: object, sep: str = ", ") -> str:
    return sep.join(normalize_logged_on_list(entries))


def normalize_chassis_type(value: object) -> Optional[str]:
    if value is None:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    if key in CHASSIS_TYPES:
        return key
    return "other"


def inventory_meta_cache(
    *,
    host: Optional[dict[str, Any]],
    hardware: Optional[dict[str, Any]],
    users: Optional[dict[str, Any]] = None,
    network: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Поля для devices.meta после POST /v1/inventory (фильтры и списки)."""
    out: dict[str, Any] = {}
    if host and isinstance(host, dict):
        dom = host.get("domain")
        if dom is not None and str(dom).strip():
            out["domain"] = str(dom).strip()
        os_info = host.get("os")
        if isinstance(os_info, dict):
            cap = os_info.get("caption")
            if cap is not None and str(cap).strip():
                caption = str(cap).strip()
                out["os_caption"] = caption
                out["os"] = caption
    if hardware and isinstance(hardware, dict):
        mfr = hardware.get("manufacturer")
        mdl = hardware.get("model")
        if mfr is not None and str(mfr).strip():
            out["hardware_manufacturer"] = str(mfr).strip()
        if mdl is not None and str(mdl).strip():
            out["hardware_model"] = str(mdl).strip()
        chassis = normalize_chassis_type(hardware.get("chassis_type"))
        if chassis:
            out["chassis_type"] = chassis
        serial = hardware.get("serial_number")
        if serial is not None and str(serial).strip():
            out["serial_number"] = str(serial).strip()
        cpu = hardware.get("cpu")
        if isinstance(cpu, dict):
            cpu_name = cpu.get("name")
            if cpu_name is not None and str(cpu_name).strip():
                out["cpu_name"] = str(cpu_name).strip()
        serials = collect_hardware_serials(hardware)
        if serials["disk_serials"]:
            out["disk_serials"] = serials["disk_serials"]
        if serials["monitor_serials"]:
            out["monitor_serials"] = serials["monitor_serials"]
        if serials["ram_serials"]:
            out["ram_serials"] = serials["ram_serials"]
        if serials["all"]:
            out["search_serials"] = serials["all"]
    if network and isinstance(network, dict):
        ips: list[str] = []
        macs: list[str] = []
        for nic in network.get("nics") or []:
            if not isinstance(nic, dict):
                continue
            for ip in nic.get("ipv4") or []:
                s = str(ip).strip()
                if s:
                    ips.append(s)
            mac = nic.get("mac")
            if mac is not None and str(mac).strip():
                macs.append(str(mac).strip())
        if ips:
            out["ipv4_addresses"] = sort_ipv4_addresses(ips)
        if macs:
            out["mac_addresses"] = macs
    enrich_hardware_meta(out, hardware=hardware, host=host, network=network)
    return out


def enrich_hardware_meta(
    meta: dict[str, Any],
    *,
    hardware: Optional[dict[str, Any]],
    host: Optional[dict[str, Any]] = None,
    network: Optional[dict[str, Any]] = None,
) -> None:
    if hardware and isinstance(hardware, dict):
        try:
            ram_b = int(hardware.get("ram_bytes") or 0)
        except (TypeError, ValueError):
            ram_b = 0
        if ram_b > 0:
            meta["ram_bytes"] = ram_b
            meta["ram_display"] = format_ram_gib(ram_b)
            bucket = ram_bucket(ram_b)
            if bucket:
                meta["ram_bucket"] = bucket
        cpu = hardware.get("cpu")
        if isinstance(cpu, dict):
            cpu_name = str(cpu.get("name") or "").strip()
            if cpu_name:
                meta["cpu_name"] = cpu_name
                fam = cpu_family_label(cpu_name)
                if fam:
                    meta["cpu_family"] = fam
                vendor = cpu_vendor_label(cpu_name)
                if vendor:
                    meta["cpu_vendor"] = vendor
        fixed = sum_fixed_disk_bytes(hardware.get("disks"))
        d_bucket = disk_bucket_from_fixed_bytes(fixed)
        if d_bucket:
            meta["disk_bucket"] = d_bucket


def apply_user_presence_patch(
    meta: dict[str, Any],
    users: Optional[dict[str, Any]],
    *,
    existing: Optional[dict[str, Any]],
) -> None:
    prev = existing or {}
    logged = normalize_logged_on_list(users.get("logged_on") if users else None)
    meta["logged_on"] = logged
    last_int = None
    if users and isinstance(users, dict) and "last_interactive" in users:
        last_int = normalize_logged_on_user(users.get("last_interactive"))
    if logged:
        meta["last_logged_on"] = logged[0]
        meta["user_presence"] = "online"
        return
    meta["user_presence"] = "last"
    if last_int:
        meta["last_logged_on"] = last_int
    elif prev.get("last_logged_on"):
        meta["last_logged_on"] = prev.get("last_logged_on")
    elif prev.get("logged_on"):
        old = normalize_logged_on_list(prev.get("logged_on"))
        if old:
            meta["last_logged_on"] = old[0]


def meta_search_haystack(meta: dict[str, Any]) -> str:
    """Строка для поиска по meta (list_devices / web fleet filter)."""
    bits = [
        str(meta.get("serial_number") or ""),
        str(meta.get("smbios_uuid") or ""),
        str(meta.get("bios_serial") or ""),
        str(meta.get("identifying_number") or ""),
        str(meta.get("baseboard_serial") or ""),
        str(meta.get("domain") or ""),
        str(meta.get("os_caption") or meta.get("os") or ""),
        str(meta.get("hardware_manufacturer") or ""),
        str(meta.get("hardware_model") or ""),
        str(meta.get("chassis_type") or ""),
        str(meta.get("cpu_name") or ""),
        str(meta.get("bad_id") or ""),
        str(meta.get("last_logged_on") or ""),
        str(meta.get("ram_bucket") or ""),
        str(meta.get("disk_bucket") or ""),
        str(meta.get("cpu_family") or ""),
    ]
    for user in normalize_logged_on_list(meta.get("logged_on")):
        bits.append(user)
    last = meta.get("last_logged_on")
    if last:
        bits.append(str(last))
    for ip in meta.get("ipv4_addresses") or []:
        bits.append(str(ip or ""))
    for mac in meta.get("mac_addresses") or []:
        bits.append(str(mac or ""))
    for disk in meta.get("disk_serials") or []:
        bits.append(str(disk or ""))
    for mon in meta.get("monitor_serials") or []:
        bits.append(str(mon or ""))
    for ram in meta.get("ram_serials") or []:
        bits.append(str(ram or ""))
    for serial in meta.get("search_serials") or []:
        bits.append(str(serial or ""))
    return " ".join(bits).casefold()
