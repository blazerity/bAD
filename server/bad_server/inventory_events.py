"""Дифф соседних inventory-снимков в осмысленные события устройства."""

from __future__ import annotations

from typing import Any, Optional

from .device_meta import normalize_logged_on_user
from .fleet_buckets import disk_role

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
        if isinstance(v, dict):
            text = normalize_logged_on_user(v) or ""
        else:
            text = _norm_str(v)
        if text:
            items.append(text)
    return sorted(set(items), key=str.casefold)


def _disk_key(disk: dict[str, Any]) -> str:
    """Ключ диска: serial|model|size если serial есть, иначе legacy model|size."""
    model = _norm_str(disk.get("model")) or "?"
    size = disk.get("size_bytes")
    size_part = size if size is not None else "?"
    serial = _norm_str(disk.get("serial_number"))
    if serial:
        return f"{serial}|{model}|{size_part}"
    return f"{model}|{size_part}"


def _av_name_set(security: dict[str, Any]) -> frozenset[str]:
    names: set[str] = set()
    for item in _as_list(security.get("antivirus")):
        if isinstance(item, dict):
            text = _norm_str(item.get("name"))
        else:
            text = _norm_str(item)
        if text:
            names.add(text.casefold())
    return frozenset(names)


def _minidump_files_by_name(minidumps: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in _as_list(minidumps.get("files")):
        if not isinstance(item, dict):
            continue
        name = _norm_str(item.get("name"))
        if not name:
            continue
        out[name.casefold()] = item
    return out


def _bugcheck_code(file_row: dict[str, Any]) -> str:
    return _norm_str(file_row.get("bugcheck_code"))


def sanitize_inventory_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Убрать запрещённые тела дампов/файлов; оставить status/names/codes.

    Additive schema_version=2: не режем неизвестные ключи верхнего уровня,
    только опасные поля внутри minidumps.files[].
    """
    if not isinstance(payload, dict):
        return payload
    md = payload.get("minidumps")
    if not isinstance(md, dict):
        return payload
    files = md.get("files")
    if not isinstance(files, list):
        return payload
    banned = {
        "content",
        "data",
        "body",
        "bytes",
        "raw",
        "blob",
        "dump",
        "base64",
        "payload",
    }
    cleaned_files: list[Any] = []
    changed = False
    for item in files:
        if not isinstance(item, dict):
            cleaned_files.append(item)
            continue
        row = dict(item)
        for key in list(row.keys()):
            if key.casefold() in banned:
                row.pop(key, None)
                changed = True
        # bugcheck_message ≤200 (контракт)
        msg = row.get("bugcheck_message")
        if isinstance(msg, str) and len(msg) > 200:
            row["bugcheck_message"] = msg[:200]
            changed = True
        # parameters: max 4
        params = row.get("bugcheck_parameters")
        if isinstance(params, list) and len(params) > 4:
            row["bugcheck_parameters"] = params[:4]
            changed = True
        cleaned_files.append(row)
    if not changed:
        return payload
    out = dict(payload)
    md_out = dict(md)
    md_out["files"] = cleaned_files
    out["minidumps"] = md_out
    return out


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

    prev_boot = _norm_str(prev_host.get("last_boot_at"))
    cur_boot = _norm_str(cur_host.get("last_boot_at"))
    if prev_boot != cur_boot and (prev_boot or cur_boot):
        events.append(
            {
                "type": "last_boot_change",
                "summary": (
                    f"Last boot: {prev_boot or '(none)'} → {cur_boot or '(none)'}"
                ),
                "detail": {"from": prev_boot or None, "to": cur_boot or None},
            }
        )

    prev_tz = _norm_str(prev_host.get("timezone"))
    cur_tz = _norm_str(cur_host.get("timezone"))
    if prev_tz != cur_tz and (prev_tz or cur_tz):
        events.append(
            {
                "type": "timezone_change",
                "summary": (
                    f"Timezone: {prev_tz or '(none)'} → {cur_tz or '(none)'}"
                ),
                "detail": {"from": prev_tz or None, "to": cur_tz or None},
            }
        )

    prev_pending = prev_host.get("pending_reboot")
    cur_pending = cur_host.get("pending_reboot")
    if prev_pending != cur_pending and (
        prev_pending is not None or cur_pending is not None
    ):
        events.append(
            {
                "type": "pending_reboot_change",
                "summary": f"Pending reboot: {prev_pending} → {cur_pending}",
                "detail": {"from": prev_pending, "to": cur_pending},
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

    prev_li = normalize_logged_on_user(prev_users.get("last_interactive")) or ""
    cur_li = normalize_logged_on_user(cur_users.get("last_interactive")) or ""
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

    prev_chassis = _norm_str(prev_hw.get("chassis_type"))
    cur_chassis = _norm_str(cur_hw.get("chassis_type"))
    if prev_chassis != cur_chassis and (prev_chassis or cur_chassis):
        events.append(
            {
                "type": "chassis_type_change",
                "summary": (
                    f"Chassis: {prev_chassis or '(none)'} → {cur_chassis or '(none)'}"
                ),
                "detail": {"from": prev_chassis or None, "to": cur_chassis or None},
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
        role = disk_role(d)
        label = _norm_str(d.get("model")) or key
        disk_detail = {**d, "role": role}
        if role == "fixed":
            events.append(
                {
                    "type": "disk_added",
                    "summary": f"Диск подключён: {label}",
                    "detail": {"disk": disk_detail},
                }
            )
        elif role == "flash":
            events.append(
                {
                    "type": "usb_added",
                    "summary": f"Флешка подключена: {label}",
                    "detail": {"disk": disk_detail},
                }
            )
        else:
            events.append(
                {
                    "type": "usb_added",
                    "summary": f"USB-диск подключён: {label}",
                    "detail": {"disk": disk_detail},
                }
            )
    for key in sorted(prev_disks.keys() - cur_disks.keys()):
        d = prev_disks[key]
        role = disk_role(d)
        label = _norm_str(d.get("model")) or key
        disk_detail = {**d, "role": role}
        if role == "fixed":
            events.append(
                {
                    "type": "disk_removed",
                    "summary": f"Диск отключён: {label}",
                    "detail": {"disk": disk_detail},
                }
            )
        elif role == "flash":
            events.append(
                {
                    "type": "usb_removed",
                    "summary": f"Флешка отключена: {label}",
                    "detail": {"disk": disk_detail},
                }
            )
        else:
            events.append(
                {
                    "type": "usb_removed",
                    "summary": f"USB-диск отключён: {label}",
                    "detail": {"disk": disk_detail},
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

    # security (optional top-level; soft-fail на агенте)
    prev_sec = _as_dict(previous.get("security"))
    cur_sec = _as_dict(current.get("security"))
    if prev_sec or cur_sec:
        prev_tpm = (
            prev_sec.get("tpm_present"),
            _norm_str(prev_sec.get("tpm_spec_version")) or None,
        )
        cur_tpm = (
            cur_sec.get("tpm_present"),
            _norm_str(cur_sec.get("tpm_spec_version")) or None,
        )
        if prev_tpm != cur_tpm and (
            prev_tpm[0] is not None
            or cur_tpm[0] is not None
            or prev_tpm[1]
            or cur_tpm[1]
        ):
            events.append(
                {
                    "type": "tpm_change",
                    "summary": (
                        f"TPM: present={prev_tpm[0]} spec={prev_tpm[1] or '(none)'} → "
                        f"present={cur_tpm[0]} spec={cur_tpm[1] or '(none)'}"
                    ),
                    "detail": {
                        "from": {
                            "tpm_present": prev_sec.get("tpm_present"),
                            "tpm_spec_version": prev_tpm[1],
                        },
                        "to": {
                            "tpm_present": cur_sec.get("tpm_present"),
                            "tpm_spec_version": cur_tpm[1],
                        },
                    },
                }
            )

        prev_sb = prev_sec.get("secure_boot")
        cur_sb = cur_sec.get("secure_boot")
        if prev_sb != cur_sb and (prev_sb is not None or cur_sb is not None):
            events.append(
                {
                    "type": "secure_boot_change",
                    "summary": f"Secure Boot: {prev_sb} → {cur_sb}",
                    "detail": {"from": prev_sb, "to": cur_sb},
                }
            )

        prev_av = _av_name_set(prev_sec)
        cur_av = _av_name_set(cur_sec)
        if prev_av != cur_av and (prev_av or cur_av):
            events.append(
                {
                    "type": "antivirus_change",
                    "summary": (
                        "Antivirus: "
                        f"{', '.join(sorted(prev_av)) or '(none)'} → "
                        f"{', '.join(sorted(cur_av)) or '(none)'}"
                    ),
                    "detail": {
                        "from": sorted(prev_av),
                        "to": sorted(cur_av),
                    },
                }
            )

    # minidump_bugcheck: новый файл с кодом или тот же name с другим code
    prev_md = _minidump_files_by_name(_as_dict(previous.get("minidumps")))
    cur_md = _minidump_files_by_name(_as_dict(current.get("minidumps")))
    for name_key in sorted(cur_md.keys()):
        cur_file = cur_md[name_key]
        code = _bugcheck_code(cur_file)
        if not code:
            continue
        prev_file = prev_md.get(name_key)
        prev_code = _bugcheck_code(prev_file) if prev_file else ""
        if prev_file is None or prev_code != code:
            fname = _norm_str(cur_file.get("name")) or name_key
            msg = _norm_str(cur_file.get("bugcheck_message"))
            summary = f"BSOD {code}"
            if msg:
                summary = f"{summary}: {msg[:120]}"
            summary = f"{summary} ({fname})"
            detail: dict[str, Any] = {
                "bugcheck_code": code,
                "bugcheck_message": msg or None,
                "filename": fname,
            }
            params = cur_file.get("bugcheck_parameters")
            if isinstance(params, list):
                detail["bugcheck_parameters"] = [
                    _norm_str(p) for p in params[:4] if _norm_str(p)
                ]
            events.append(
                {
                    "type": "minidump_bugcheck",
                    "summary": summary,
                    "detail": detail,
                }
            )

    return events
