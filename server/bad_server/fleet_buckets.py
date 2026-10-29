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


def normalize_os_caption(value: object) -> str:
    """Единые ярлыки ОС: Windows 10 Pro / Enterprise; пусто → «Не определена»."""
    text = str(value or "").strip()
    if not text or text in {"—", "-", "?"}:
        return "Не определена"
    low = text.casefold()
    low = re.sub(r"^(microsoft|майкрософт)\s+", "", low)
    ver: Optional[str] = None
    if "windows server" in low:
        m = re.search(r"windows server\s+(\d{4})", low)
        ver = f"Windows Server {m.group(1)}" if m else "Windows Server"
    elif "windows 11" in low or "windows11" in low:
        ver = "Windows 11"
    elif "windows 10" in low or "windows10" in low:
        ver = "Windows 10"
    elif "windows 8.1" in low:
        ver = "Windows 8.1"
    elif "windows 8" in low:
        ver = "Windows 8"
    elif "windows 7" in low:
        ver = "Windows 7"
    edition: Optional[str] = None
    if "корпоратив" in low or "enterprise" in low:
        edition = "Enterprise"
    elif "образовательн" in low or "education" in low:
        edition = "Education"
    elif re.search(r"\bpro\b", low) or "профессион" in low:
        edition = "Pro"
    elif "home" in low or "домашн" in low:
        edition = "Home"
    if ver and edition:
        return f"{ver} {edition}"
    if ver:
        return ver
    cleaned = re.sub(
        r"^(Microsoft|Майкрософт)\s+", "", text, flags=re.IGNORECASE
    ).strip()
    return cleaned or "Не определена"


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


def format_ram_ddr(value: object) -> str:
    """Короткий тип ОЗУ для списка: DDR4 / DDR5."""
    text = str(value or "").strip()
    if not text or text in {"—", "-", "?", "Unknown", "unknown"}:
        return ""
    m = re.search(r"DDR\s*([345])", text, flags=re.IGNORECASE)
    if m:
        return f"DDR{m.group(1)}"
    m2 = re.search(r"\bLPDDR\s*([345])", text, flags=re.IGNORECASE)
    if m2:
        return f"LPDDR{m2.group(1)}"
    return ""


def format_ram_list_cell(ram_bytes: object, memory_type: object = None) -> str:
    """Ячейка ОЗУ в таблице устройств: «32 ГБ · DDR5»."""
    bucket = ram_bucket(ram_bytes) or format_ram_gib(ram_bytes)
    if not bucket or bucket == "—":
        return "—"
    ddr = format_ram_ddr(memory_type)
    if ddr:
        return f"{bucket} · {ddr}"
    return bucket


def _normalize_core_i_model(raw: str) -> str:
    """Один префикс i + SKU: ii5-… / I5-… → i5-…"""
    m = re.match(r"^i+([3579][\w-]*)$", raw.strip(), flags=re.IGNORECASE)
    if m:
        return f"i{m.group(1)}"
    return raw.strip()


def format_cpu_short(name: object) -> str:
    """Короткая подпись CPU для списка устройств (без ®, частоты @ GHz)."""
    text = str(name or "").strip()
    if not text or text in {"—", "-", "?"}:
        return "—"
    text = re.sub(r"\(R\)|\(TM\)|®|™", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*@\s*[\d.,]+\s*GHz\s*", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    gen_m = re.search(r"(\d+(?:st|nd|rd|th)\s+Gen)\b", text, flags=re.IGNORECASE)
    gen = gen_m.group(1) if gen_m else None
    core_i = re.search(
        r"(?:Intel\s+)?Core\s+(i+[3579][\w-]*)",
        text,
        flags=re.IGNORECASE,
    )
    if core_i:
        model = _normalize_core_i_model(core_i.group(1))
        if gen:
            return f"Core {model} ({gen})"
        return f"Core {model}"
    ultra = re.search(
        r"(?:Intel\s+)?Core\s+Ultra\s+(\d+)\s+([\w-]+)",
        text,
        flags=re.IGNORECASE,
    )
    if ultra:
        label = f"Core Ultra {ultra.group(1)} {ultra.group(2)}"
        return f"{label} ({gen})" if gen else label
    ryzen = re.search(
        r"(?:AMD\s+)?Ryzen\s+(\d+)\s+([\w-]+)",
        text,
        flags=re.IGNORECASE,
    )
    if ryzen:
        return f"Ryzen {ryzen.group(1)} {ryzen.group(2)}"
    cleaned = re.sub(r"\bIntel\b|\bAMD\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\bwith\s+Radeon(?:\s+Graphics)?\b|\bCPU\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    if not cleaned:
        cleaned = text
    if len(cleaned) > 56:
        return cleaned[:53].rstrip() + "…"
    return cleaned


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


def normalize_cpu_name(cpu_name: str) -> str:
    """Убрать (R)/(TM)/® — иначе «Core(TM) Ultra» не матчится как «core ultra»."""
    text = (cpu_name or "").strip()
    if not text:
        return ""
    text = re.sub(r"\((?:r|tm|c)\)", " ", text, flags=re.IGNORECASE)
    text = text.replace("®", " ").replace("™", " ").replace("©", " ")
    return re.sub(r"\s+", " ", text).strip()


def cpu_vendor_label(cpu_name: str) -> Optional[str]:
    low = normalize_cpu_name(cpu_name).casefold()
    if any(x in low for x in ("intel", "xeon", "core i", "pentium", "celeron", "core ultra")):
        return "Intel"
    if any(x in low for x in ("amd", "ryzen", "epyc")):
        return "AMD"
    return None


def cpu_family_label(cpu_name: str) -> Optional[str]:
    name = normalize_cpu_name(cpu_name)
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


def resolve_cpu_family(meta: dict[str, Any]) -> Optional[str]:
    """Актуальное семейство: сначала из cpu_name (свежий разбор), иначе кэш meta."""
    name = str(meta.get("cpu_name") or "").strip()
    if name:
        fam = cpu_family_label(name)
        if fam:
            return fam
    fam = str(meta.get("cpu_family") or "").strip()
    return fam or None


# ---------------------------------------------------------------------------
# Intel Core i: поколение, кодовое имя, сегмент (Mobile/Desktop)
# ---------------------------------------------------------------------------

_CORE_I_RE = re.compile(
    r"\bi([3579])[\s-]+(?:cpu\s+)?(\d{3,5})([a-z]*)",
    re.IGNORECASE,
)

_CORE_I_CODENAMES: dict[int, str] = {
    1: "Nehalem",
    2: "Sandy Bridge",
    3: "Ivy Bridge",
    4: "Haswell",
    5: "Broadwell",
    6: "Skylake",
    7: "Kaby Lake",
    8: "Coffee Lake",
    9: "Coffee Lake Refresh",
    10: "Comet Lake",
    11: "Rocket Lake",
    12: "Alder Lake",
    13: "Raptor Lake",
    14: "Raptor Lake Refresh",
}

# Суффиксы мобильных процессоров: U, Y, H, HX, G (Iris), P, B, M, Q
_MOBILE_SUFFIXES = frozenset("UHGYPBMQ")


def _core_i_generation(digits: str) -> int:
    if len(digits) == 3:       # i7-920, i5-750 → 1-е поколение
        return 1
    if len(digits) == 5:       # i7-10700K, i9-14900K → первые 2 цифры
        return int(digits[:2])
    if digits[0] == "1":       # 4 цифры с «1»: i5-1135G7 (11), i7-1065G7 (10)
        return int(digits[:2])
    return int(digits[0])      # i7-8700, i5-2500, i9-9900K → первая цифра


def _ordinal_en(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _intel_core_i_family(name: str) -> Optional[str]:
    m = _CORE_I_RE.search(name)
    if not m:
        return None
    series, digits, suffix = m.group(1), m.group(2), m.group(3).upper()
    gen = _core_i_generation(digits)

    # 4-значные модели с «1» в начале (1035G1, 1165G7, 1235U) — мобильные;
    # дополнительно учитываем буквенные суффиксы (U, H, G, P, M, ...)
    mobile = bool(set(suffix) & _MOBILE_SUFFIXES) or (len(digits) == 4 and digits[0] == "1")
    segment = "Mobile" if mobile else "Desktop"

    if gen == 10:
        codename = "Ice Lake" if len(digits) == 4 else "Comet Lake"
    elif gen == 11:
        codename = "Tiger Lake" if (mobile or len(digits) == 4) else "Rocket Lake"
    else:
        codename = _CORE_I_CODENAMES.get(gen)

    if codename is None:
        return f"Intel Core i{series}"
    return f"Intel {codename} ({segment} {_ordinal_en(gen)} Gen)"


def _intel_family(name: str, low: str) -> str:
    # После normalize_cpu_name: «Intel Core Ultra 7 265U» без (TM)
    if "core ultra" in low or re.search(r"\bultra\s*[3579]\b", low):
        m = re.search(r"(?:ultra\s*[3579]\s*)?(\d{3})\s*([a-z]*)", low)
        if m:
            n = int(m.group(1))
            suf = (m.group(2) or "").upper()
            if 200 <= n < 300 and "V" in suf:
                return "Intel Lunar Lake (Core Ultra)"
            if 200 <= n < 300:
                return "Intel Arrow Lake (Core Ultra)"
            if 100 <= n < 200:
                return "Intel Meteor Lake (Core Ultra)"
        return "Intel Core Ultra"

    core_i = _intel_core_i_family(name)
    if core_i:
        return core_i

    if re.search(r"\bn100\b|\bn200\b|\bn95\b", low):
        return "Intel N-series (Alder Lake-N)"
    if "xeon" in low:
        if re.search(r"silver\s*43|gold\s*53|platinum\s*83", low):
            return "Intel Xeon (Ice Lake)"
        if re.search(r"silver\s*42|gold\s*62|platinum\s*82|bronze\s*32", low):
            return "Intel Xeon (Cascade Lake)"
        if re.search(r"gold\s*5[46]|gold\s*6[45]|platinum\s*84|w-24|w-34", low):
            return "Intel Xeon (Sapphire Rapids)"
        if re.search(r"gold\s*55|gold\s*65|platinum\s*85", low):
            return "Intel Xeon (Granite Rapids)"
        if "e-23" in low or "e23" in low:
            return "Intel Xeon (Rocket Lake)"
        for tier in ("bronze", "silver", "gold", "platinum"):
            if tier in low:
                return f"Intel Xeon ({tier.title()})"
        return "Intel Xeon"
    if "pentium" in low:
        return "Intel Pentium"
    if "celeron" in low:
        return "Intel Celeron"
    # Никогда не отдаём голый ярлык «Intel» — он схлопывал Ultra и прочее в один куб
    return "Intel (другое)"


def _amd_family(name: str, low: str) -> str:
    if "ryzen ai" in low:
        return "AMD Ryzen AI (Strix Point)"
    if "ryzen" in low:
        m = re.search(r"ryzen\s*(\d)", low)
        if m:
            d = int(m.group(1))
            if d >= 9:
                return "AMD Ryzen (Zen 5)"
            if d >= 7:
                return "AMD Ryzen (Zen 4)"
            if d >= 5:
                return "AMD Ryzen (Zen 3)"
            if d >= 3:
                return "AMD Ryzen (Zen 2)"
        return "AMD Ryzen"
    if "epyc" in low:
        if "9005" in name:
            return "AMD EPYC (Turin)"
        if "9004" in name:
            return "AMD EPYC (Genoa)"
        if "7003" in name:
            return "AMD EPYC (Milan)"
        return "AMD EPYC"
    return "AMD (другое)"


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
    model_filter: Optional[str] = None,
    chassis_filter: Optional[str] = None,
    fresh_ok: bool = False,
    silence_status: Optional[str] = None,
) -> bool:
    if os_filter:
        have_os = normalize_os_caption(meta.get("os_caption") or meta.get("os") or "")
        if have_os != os_filter and str(meta.get("os_caption") or meta.get("os") or "") != os_filter:
            return False
    if ram_filter and str(meta.get("ram_bucket") or "") != ram_filter:
        return False
    if disk_filter and str(meta.get("disk_bucket") or "") != disk_filter:
        return False
    if cpu_filter and (resolve_cpu_family(meta) or "") != cpu_filter:
        return False
    if cpu_vendor_filter and str(meta.get("cpu_vendor") or "") != cpu_vendor_filter:
        return False
    if model_filter and str(meta.get("hardware_model") or "").strip() != model_filter:
        return False
    if chassis_filter and str(meta.get("chassis_type") or "").strip() != chassis_filter:
        return False
    if agent_filter and str(device.get("agent_version") or "") != agent_filter:
        return False
    if fresh_ok and silence_status != "ok":
        return False
    return True
