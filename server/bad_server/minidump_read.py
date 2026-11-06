"""Разбор заголовка минидампа библиотекой minidump. Тело дампа не хранится."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

MAX_BYTES = 8 * 1024 * 1024
REQUEST_META = "minidump_request"
READS_META = "minidump_reads"

# Коды, которые сами по себе говорят о памяти, а не о конкретном .sys.
_MEMORY = {0x1A, 0x2E, 0x4E, 0x7A, 0x124}
_DRIVER = {
    0x0A,
    0x3B,
    0x50,
    0x76,
    0x7E,
    0x9F,
    0xBE,
    0xC2,
    0xC4,
    0xC5,
    0xC9,
    0xCA,
    0xD1,
    0xD5,
    0xD6,
    0xE1,
    0xEA,
    0xFE,
    0x133,
}
_PROGRAM = {0xEF, 0xF4, 0x1E}
_KERNEL = {"ntoskrnl.exe", "ntkrnlmp.exe", "ntkrnlpa.exe", "ntkrpamp.exe"}


def dump_name_ok(name: str) -> bool:
    if not name or name != Path(name).name:
        return False
    if "\\" in name or "/" in name:
        return False
    if not name.lower().endswith(".dmp"):
        return False
    return name.casefold() != "memory.dmp"


def cause_label(code: int, module: Optional[str]) -> str:
    ext = ""
    if module and "." in module:
        ext = module.rsplit(".", 1)[-1].lower()
    if code in _MEMORY:
        return "память"
    if code >= 0x80000000 or code in _PROGRAM or ext in {"exe", "dll"}:
        return "программа"
    if code in _DRIVER or ext == "sys" or code < 0x10000:
        return "драйвер"
    return "программа"


def cause_text(cause: str, bugcheck: str, module: Optional[str]) -> str:
    parts = [cause, bugcheck]
    if module:
        parts.append(module)
    return " · ".join(parts)


def read_header(path: str) -> Optional[dict[str, str]]:
    from minidump.minidumpfile import MinidumpFile

    with open(path, "rb") as handle:
        parsed = MinidumpFile.parse_external(handle, path)
        return _from_parsed(parsed)


def _module_name(raw: Any) -> str:
    text = str(raw or "").replace("/", "\\").strip("\x00 ")
    return text.split("\\")[-1]


def _from_parsed(mf: Any) -> Optional[dict[str, str]]:
    exception = getattr(mf, "exception", None)
    records = list(getattr(exception, "exception_records", None) or [])
    if not records:
        return None
    record = records[0].ExceptionRecord
    code = int(record.ExceptionCode_raw)
    address = int(record.ExceptionAddress or 0)
    module = _module_for_address(mf, address)
    cause = cause_label(code, module)
    bugcheck = f"0x{code:08X}"
    out = {
        "cause": cause,
        "bugcheck": bugcheck,
        "text": cause_text(cause, bugcheck, module),
    }
    if module:
        out["module"] = module
    return out


def _module_for_address(mf: Any, address: int) -> Optional[str]:
    listing = getattr(mf, "modules", None)
    modules = list(getattr(listing, "modules", None) or [])
    chosen = None
    for mod in modules:
        base = int(getattr(mod, "baseaddress", 0) or 0)
        size = int(getattr(mod, "size", 0) or 0)
        if size and base <= address < base + size:
            chosen = mod
            break
    if chosen is None:
        for mod in modules:
            if _module_name(getattr(mod, "name", "")).casefold() not in _KERNEL:
                chosen = mod
                break
    if chosen is None and modules:
        chosen = modules[0]
    if chosen is None:
        return None
    name = _module_name(getattr(chosen, "name", ""))
    return name or None


def unlink_dump(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
