"""Дифф соседних inventory-снимков в осмысленные события устройства."""

from __future__ import annotations

from typing import Any, Optional

# Абсолютное падение свободного места (байты) или относительное к предыдущему free.
VOLUME_FREE_DROP_ABS = 5 * 1024**3  # 5 ГиБ
VOLUME_FREE_DROP_REL = 0.20


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _norm_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _sorted_str_list(values: Any) -> list[str]:
    items = []
    for v in _as_list(values):
        text = _norm_str(v)
        if text:
            items.append(text)
    return sorted(set(items), key=str.casefold)


def _disk_key(disk: dict[str, Any]) -> str:
    model = _norm_str(disk.get("model")) or "?"
    size = disk.get("size_bytes")
    return f"{model}|{size if size is not None else '?'}"


def _ram_module_key(mod: dict[str, Any]) -> str:
    parts = [
        _norm_str(mod.get("part_number")) or "?",
        _norm_str(mod.get("serial_number")) or "?",
        _norm_str(mod.get("device_locator") or mod.get("locator")) or "?",
        str(mod.get("capacity_bytes") if mod.get("capacity_bytes") is not None else "?"),
        _norm_str(mod.get("bank_label") or mod.get("channel")) or "?",
    ]
    return "|".join(parts)


def _cpu_label(cpu: dict[str, Any]) -> str:
    name = _norm_str(cpu.get("name")) or "?"
    cores = cpu.get("cores")
    logical = cpu.get("logical")
    return f"{name} (cores={cores}, logical={logical})"


def _volume_key(vol: dict[str, Any]) -> str:
    letter = _norm_str(vol.get("letter"))
    if letter:
        return letter.upper()
    return f"vol|{vol.get('size_bytes')}|{_norm_str(vol.get('model'))}"


def _nic_ipv4_set(network: dict[str, Any]) -> frozenset[str]:
    ips: set[str] = set()
    for nic in _as_list(network.get("nics")):
        if not isinstance(nic, dict):
            continue
        for ip in _as_list(nic.get("ipv4")):
            text = _norm_str(ip)
            if text:
                ips.add(text)
    return frozenset(ips)


def _volume_free_dropped(prev: dict[str, Any], new: dict[str, Any]) -> bool:
    try:
        prev_free = int(prev.get("free_bytes"))
        new_free = int(new.get("free_bytes"))
    except (TypeError, ValueError):
        return False
    if new_free >= prev_free:
        return False
    drop = prev_free - new_free
    if drop >= VOLUME_FREE_DROP_ABS:
        return True
    if prev_free > 0 and (drop / prev_free) >= VOLUME_FREE_DROP_REL:
        return True
    return False


def diff_inventory_snapshots(
    previous: Optional[dict[str, Any]],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    """Вернуть dict событий: type, summary, detail (JSON-сериализуемые).

    Первый снимок (без previous) не даёт событий.
    """
    if not previous or not isinstance(previous, dict):
        return []
    if not isinstance(current, dict):
        return []

    events: list[dict[str, Any]] = []

    prev_host = _as_dict(previous.get("host"))
    cur_host = _as_dict(current.get("host"))
    prev_hn = _norm_str(prev_host.get("hostname"))
    cur_hn = _norm_str(cur_host.get("hostname"))
    if prev_hn and cur_hn and prev_hn.casefold() != cur_hn.casefold():
        events.append(
            {
                "type": "hostname_change",
                "summary": f"Hostname: {prev_hn} → {cur_hn}",
                "detail": {"from": prev_hn, "to": cur_hn},
            }
        )

    prev_domain = _norm_str(prev_host.get("domain"))
    cur_domain = _norm_str(cur_host.get("domain"))
    if prev_domain != cur_domain and (prev_domain or cur_domain):
        events.append(
            {
                "type": "domain_change",
                "summary": f"Domain: {prev_domain or '(none)'} → {cur_domain or '(none)'}",
                "detail": {"from": prev_domain, "to": cur_domain},
            }
        )

    prev_users = _as_dict(previous.get("users"))
    cur_users = _as_dict(current.get("users"))
    prev_logged = _sorted_str_list(prev_users.get("logged_on"))
    cur_logged = _sorted_str_list(cur_users.get("logged_on"))
    if prev_logged != cur_logged:
        events.append(
            {
                "type": "logged_on_change",
                "summary": (
                    "Logged-on users: "
                    f"{', '.join(prev_logged) or '(none)'} → "
                    f"{', '.join(cur_logged) or '(none)'}"
                ),
                "detail": {"from": prev_logged, "to": cur_logged},
            }
        )

    prev_li = _norm_str(prev_users.get("last_interactive"))
    cur_li = _norm_str(cur_users.get("last_interactive"))
    if prev_li != cur_li and (prev_li or cur_li):
        events.append(
            {
                "type": "last_interactive_change",
                "summary": (
                    f"Last interactive user: {prev_li or '(none)'} → {cur_li or '(none)'}"
                ),
                "detail": {"from": prev_li, "to": cur_li},
            }
        )

    prev_hw = _as_dict(previous.get("hardware"))
    cur_hw = _as_dict(current.get("hardware"))

    prev_serial = _norm_str(prev_hw.get("serial_number"))
    cur_serial = _norm_str(cur_hw.get("serial_number"))
    if prev_serial != cur_serial and (prev_serial or cur_serial):
        events.append(
            {
                "type": "serial_change",
                "summary": (
                    f"Serial: {prev_serial or '(none)'} → {cur_serial or '(none)'}"
                ),
                "detail": {"from": prev_serial, "to": cur_serial},
            }
        )

    prev_model = _norm_str(prev_hw.get("model"))
    cur_model = _norm_str(cur_hw.get("model"))
    if prev_model != cur_model and (prev_model or cur_model):
        events.append(
            {
                "type": "model_change",
                "summary": (
                    f"Model: {prev_model or '(none)'} → {cur_model or '(none)'}"
                ),
                "detail": {"from": prev_model, "to": cur_model},
            }
        )

    prev_mfr = _norm_str(prev_hw.get("manufacturer"))
    cur_mfr = _norm_str(cur_hw.get("manufacturer"))
    if prev_mfr != cur_mfr and (prev_mfr or cur_mfr):
        events.append(
            {
                "type": "manufacturer_change",
                "summary": (
                    f"Manufacturer: {prev_mfr or '(none)'} → {cur_mfr or '(none)'}"
                ),
                "detail": {"from": prev_mfr, "to": cur_mfr},
            }
        )

    prev_cpu = _as_dict(prev_hw.get("cpu"))
    cur_cpu = _as_dict(cur_hw.get("cpu"))
    if prev_cpu or cur_cpu:
        prev_cpu_key = (
            _norm_str(prev_cpu.get("name")),
            prev_cpu.get("cores"),
            prev_cpu.get("logical"),
        )
        cur_cpu_key = (
            _norm_str(cur_cpu.get("name")),
            cur_cpu.get("cores"),
            cur_cpu.get("logical"),
        )
        if prev_cpu_key != cur_cpu_key and (prev_cpu or cur_cpu):
            events.append(
                {
                    "type": "cpu_change",
                    "summary": (
                        f"CPU: {_cpu_label(prev_cpu)} → {_cpu_label(cur_cpu)}"
                    ),
                    "detail": {"from": prev_cpu, "to": cur_cpu},
                }
            )

    prev_ram = prev_hw.get("ram_bytes")
    cur_ram = cur_hw.get("ram_bytes")
    if prev_ram != cur_ram and (prev_ram is not None or cur_ram is not None):
        events.append(
            {
                "type": "ram_bytes_change",
                "summary": f"RAM bytes: {prev_ram} → {cur_ram}",
                "detail": {"from": prev_ram, "to": cur_ram},
            }
        )

    prev_modules = {
        _ram_module_key(m): m
        for m in _as_list(prev_hw.get("ram_modules"))
        if isinstance(m, dict)
    }
    cur_modules = {
        _ram_module_key(m): m
        for m in _as_list(cur_hw.get("ram_modules"))
        if isinstance(m, dict)
    }
    for key in sorted(cur_modules.keys() - prev_modules.keys()):
        m = cur_modules[key]
        label = (
            _norm_str(m.get("part_number"))
            or _norm_str(m.get("device_locator") or m.get("locator"))
            or key
        )
        events.append(
            {
                "type": "ram_module_added",
                "summary": f"RAM module added: {label}",
                "detail": {"module": m},
            }
        )
    for key in sorted(prev_modules.keys() - cur_modules.keys()):
        m = prev_modules[key]
        label = (
            _norm_str(m.get("part_number"))
            or _norm_str(m.get("device_locator") or m.get("locator"))
            or key
        )
        events.append(
            {
                "type": "ram_module_removed",
                "summary": f"RAM module removed: {label}",
                "detail": {"module": m},
            }
        )

    prev_disks = {
        _disk_key(d): d
        for d in _as_list(prev_hw.get("disks"))
        if isinstance(d, dict)
    }
    cur_disks = {
        _disk_key(d): d
        for d in _as_list(cur_hw.get("disks"))
        if isinstance(d, dict)
    }
    for key in sorted(cur_disks.keys() - prev_disks.keys()):
        d = cur_disks[key]
        label = _norm_str(d.get("model")) or key
        events.append(
            {
                "type": "disk_added",
                "summary": f"Disk added: {label}",
                "detail": {"disk": d},
            }
        )
    for key in sorted(prev_disks.keys() - cur_disks.keys()):
        d = prev_disks[key]
        label = _norm_str(d.get("model")) or key
        events.append(
            {
                "type": "disk_removed",
                "summary": f"Disk removed: {label}",
                "detail": {"disk": d},
            }
        )

    prev_vols = {
        _volume_key(v): v
        for v in _as_list(prev_hw.get("volumes"))
        if isinstance(v, dict)
    }
    cur_vols = {
        _volume_key(v): v
        for v in _as_list(cur_hw.get("volumes"))
        if isinstance(v, dict)
    }
    for key in sorted(set(prev_vols) & set(cur_vols)):
        if _volume_free_dropped(prev_vols[key], cur_vols[key]):
            events.append(
                {
                    "type": "volume_free_drop",
                    "summary": (
                        f"Volume {key} free space dropped: "
                        f"{prev_vols[key].get('free_bytes')} → "
                        f"{cur_vols[key].get('free_bytes')} bytes"
                    ),
                    "detail": {
                        "volume": key,
                        "from_free_bytes": prev_vols[key].get("free_bytes"),
                        "to_free_bytes": cur_vols[key].get("free_bytes"),
                    },
                }
            )

    prev_ips = _nic_ipv4_set(_as_dict(previous.get("network")))
    cur_ips = _nic_ipv4_set(_as_dict(current.get("network")))
    if prev_ips != cur_ips:
        added = sorted(cur_ips - prev_ips)
        removed = sorted(prev_ips - cur_ips)
        parts: list[str] = []
        if added:
            parts.append("+" + ", ".join(added))
        if removed:
            parts.append("-" + ", ".join(removed))
        events.append(
            {
                "type": "nic_ipv4_change",
                "summary": "NIC IPv4: " + ("; ".join(parts) if parts else "set changed"),
                "detail": {
                    "from": sorted(prev_ips),
                    "to": sorted(cur_ips),
                    "added": added,
                    "removed": removed,
                },
            }
        )

    return events
