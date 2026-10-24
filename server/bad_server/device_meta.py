"""Кэш полей inventory в devices.meta (списки без полного snapshot)."""

from __future__ import annotations

from typing import Any, Optional

CHASSIS_TYPES = frozenset({"laptop", "desktop", "server", "vm", "other"})


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
    if users and isinstance(users, dict):
        logged = users.get("logged_on") or []
        clean = [str(u).strip() for u in logged if u and str(u).strip()]
        if clean:
            out["logged_on"] = clean
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
            out["ipv4_addresses"] = ips
        if macs:
            out["mac_addresses"] = macs
    return out


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
    ]
    for user in meta.get("logged_on") or []:
        bits.append(str(user or ""))
    for ip in meta.get("ipv4_addresses") or []:
        bits.append(str(ip or ""))
    for mac in meta.get("mac_addresses") or []:
        bits.append(str(mac or ""))
    for disk in meta.get("disk_serials") or []:
        bits.append(str(disk or ""))
    return " ".join(bits).casefold()
