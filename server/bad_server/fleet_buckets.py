"""Бакеты парка (ОЗУ/диск/CPU) — единые правила для meta, фильтров и дашборда."""

from __future__ import annotations

import ipaddress
import re
from typing import Any, Optional

_RAM_NOMINALS_GIB = (4, 8, 16, 32, 64, 128, 256, 512)
_DISK_NOMINALS = (
    (128, "128 ГБ"),
    (256, "256 ГБ"),
    (512, "512 ГБ"),
    (1024, "1 ТБ"),
    (2048, "2 ТБ"),
    (4096, "4 ТБ"),
    (8192, "8 ТБ"),
)


def format_ram_gib(ram_bytes: object) -> str:
    try:
        n = int(ram_bytes or 0)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    gib = n / (1024**3)
    if abs(gib - round(gib)) < 0.05:
        return f"{int(round(gib))} ГБ"
    return f"{gib:.1f} ГБ"


def ram_bucket(ram_bytes: object) -> Optional[str]:
    try:
        n = int(ram_bytes or 0)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    gib = n / (1024**3)
    if gib <= _RAM_NOMINALS_GIB[0]:
        return f"{_RAM_NOMINALS_GIB[0]} ГБ"
    best = _RAM_NOMINALS_GIB[0]
    best_dist = abs(gib - best)
    for nom in _RAM_NOMINALS_GIB[1:]:
        dist = abs(gib - nom)
        if dist < best_dist or (dist == best_dist and nom > best):
            best = nom
            best_dist = dist
    return f"{best} ГБ"


def _within_disk_tolerance(size_bytes: int, nominal_gib: int) -> bool:
    if size_bytes <= 0:
        return False
    dec = nominal_gib * 1_000_000_000
    bin_ = nominal_gib * (2**30)
    for target in (dec, bin_):
        if target <= 0:
            continue
        if abs(size_bytes - target) / target <= 0.12:
            return True
    return False


def disk_bucket_from_fixed_bytes(total_fixed_bytes: int) -> Optional[str]:
    if total_fixed_bytes <= 0:
        return None
    matched: list[tuple[int, str]] = []
    for gib, label in _DISK_NOMINALS:
        if _within_disk_tolerance(total_fixed_bytes, gib):
            matched.append((gib, label))
    if len(matched) == 1:
        return matched[0][1]
    if len(matched) > 1:
        return matched[0][1]
    # между номиналами
    gib = total_fixed_bytes / (1024**3)
    pairs = list(_DISK_NOMINALS)
    for i in range(len(pairs) - 1):
        lo, hi = pairs[i], pairs[i + 1]
        if lo[0] <= gib < hi[0]:
            return f"{lo[1].replace(' ТБ', '').replace(' ГБ', '')}–{hi[1]}"
    if gib < pairs[0][0]:
        return f"< {pairs[0][1]}"
    return f"{pairs[-1][1]}+"


def disk_role(disk: dict[str, Any]) -> str:
    if disk.get("removable") is True:
        return "flash"
    media = str(disk.get("media_type") or "").casefold()
    if "removable" in media:
        return "flash"
    iface = str(disk.get("interface_type") or "").casefold()
    pnp = str(disk.get("pnp_device_id") or "").strip().upper()
    if iface == "usb" or pnp.startswith("USB") or pnp.startswith("USBSTOR"):
        return "usb_disk"
    if "external" in media:
        return "usb_disk"
    return "fixed"


def sum_fixed_disk_bytes(disks: object) -> int:
    total = 0
    if not isinstance(disks, list):
        return 0
    for d in disks:
        if not isinstance(d, dict):
            continue
        if disk_role(d) != "fixed":
            continue
        try:
            total += int(d.get("size_bytes") or 0)
        except (TypeError, ValueError):
            continue
    return total


def cpu_vendor_label(cpu_name: str) -> Optional[str]:
    low = cpu_name.casefold()
    if any(x in low for x in ("intel", "xeon", "core i", "pentium", "celeron", "core ultra")):
        return "Intel"
    if any(x in low for x in ("amd", "ryzen", "epyc")):
        return "AMD"
    return None


def cpu_family_label(cpu_name: str) -> Optional[str]:
    name = (cpu_name or "").strip()
    if not name:
        return None
    low = name.casefold()
    vendor = cpu_vendor_label(name)

    if vendor == "Intel":
        return _intel_family(name, low)
    if vendor == "AMD":
        return _amd_family(name, low)
    if vendor:
        return vendor
    return "Другое"


def _intel_family(name: str, low: str) -> str:
    if "core ultra" in low:
        m = re.search(r"(\d{3})", name)
        if m:
            n = int(m.group(1))
            if 200 <= n < 300 and name.upper().endswith("V"):
                return "Intel · Core Ultra · Lunar Lake"
            if 200 <= n < 300:
                return "Intel · Core Ultra · Arrow Lake"
            if 100 <= n < 200:
                return "Intel · Core Ultra · Meteor Lake"
        return "Intel · Core Ultra"
    m = re.search(r"i([3579])-(\d{2})(\d{3})", low)
    if m:
        gen = int(m.group(2))
        suffix = name.split()[-1].upper() if name.split() else ""
        if gen == 14:
            return "Intel · 14 · Raptor Lake"
        if gen == 13:
            return "Intel · 13 · Raptor Lake"
        if gen == 12:
            return "Intel · 12 · Alder Lake"
        if gen == 11:
            if any(x in suffix for x in ("U", "H", "G")):
                return "Intel · 11 · Tiger Lake"
            return "Intel · 11 · Rocket Lake"
        if gen == 10:
            return "Intel · 10 · Comet Lake"
    if re.search(r"\bn100\b|\bn200\b|\bn95\b", low):
        return "Intel · N · Alder Lake-N"
    m_old = re.search(r"i([3579])-(\d{4})", low)
    if m_old and int(m_old.group(2)[:2]) < 10:
        return f"Intel · Core i{m_old.group(1)}"
    if "xeon" in low:
        if re.search(r"silver\s*43|gold\s*53|platinum\s*83", low):
            return "Intel · Xeon · Ice Lake"
        if re.search(r"gold\s*5[46]|gold\s*6[45]|platinum\s*84|w-24|w-34", low):
            return "Intel · Xeon · Sapphire Rapids"
        if re.search(r"gold\s*55|gold\s*65|platinum\s*85", low):
            return "Intel · Xeon · Granite Rapids"
        if "e-23" in low or "e23" in low:
            return "Intel · Xeon · Rocket Lake"
        for tier in ("bronze", "silver", "gold", "platinum"):
            if tier in low:
                return f"Intel · Xeon · {tier.title()}"
        return "Intel · Xeon"
    if "pentium" in low:
        return "Intel · Pentium"
    if "celeron" in low:
        return "Intel · Celeron"
    return "Intel"


def _amd_family(name: str, low: str) -> str:
    if "ryzen ai" in low:
        return "AMD · Ryzen AI · Strix Point"
    if "ryzen" in low:
        m = re.search(r"(\d)", name)
        if m:
            d = int(m.group(1))
            if d >= 9:
                return "AMD · Ryzen · Zen 5"
            if d >= 7:
                return "AMD · Ryzen · Zen 4"
            if d >= 5:
                return "AMD · Ryzen · Zen 3"
            if d >= 3:
                return "AMD · Ryzen · Zen 2"
        return "AMD · Ryzen"
    if "epyc" in low:
        if "9005" in name:
            return "AMD · EPYC · Turin"
        if "9004" in name:
            return "AMD · EPYC · Genoa"
        if "7003" in name:
            return "AMD · EPYC · Milan"
        return "AMD · EPYC"
    return "AMD"


def sort_ipv4_addresses(ips: list[str]) -> list[str]:
    def key(ip: str) -> tuple[int, str]:
        try:
            addr = ipaddress.ip_address(ip.strip())
            if isinstance(addr, ipaddress.IPv4Address):
                link_local = addr in ipaddress.ip_network("169.254.0.0/16")
                return (1 if link_local else 0, str(addr))
        except ValueError:
            pass
        return (2, ip)

    uniq = []
    seen: set[str] = set()
    for ip in ips:
        s = str(ip or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    return sorted(uniq, key=key)


def meta_facet_matches(
    meta: dict[str, Any],
    device: dict[str, Any],
    *,
    os_filter: Optional[str] = None,
    ram_filter: Optional[str] = None,
    disk_filter: Optional[str] = None,
    cpu_filter: Optional[str] = None,
    cpu_vendor_filter: Optional[str] = None,
    agent_filter: Optional[str] = None,
    fresh_ok: bool = False,
    silence_status: Optional[str] = None,
) -> bool:
    if os_filter and str(meta.get("os_caption") or meta.get("os") or "") != os_filter:
        return False
    if ram_filter and str(meta.get("ram_bucket") or "") != ram_filter:
        return False
    if disk_filter and str(meta.get("disk_bucket") or "") != disk_filter:
        return False
    if cpu_filter and str(meta.get("cpu_family") or "") != cpu_filter:
        return False
    if cpu_vendor_filter and str(meta.get("cpu_vendor") or "") != cpu_vendor_filter:
        return False
    if agent_filter and str(device.get("agent_version") or "") != agent_filter:
        return False
    if fresh_ok and silence_status != "ok":
        return False
    return True
