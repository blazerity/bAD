from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .bad_id import is_bad_id
from .db_backend import CompatConnection
from .db import (
    PENDING_ENROLLMENT_CAP,
    PENDING_ENROLLMENT_TTL,
    _compact_json,
    _utc_cutoff,
    logger,
    utc_now,
)

class DbIdentityMixin:

    # Placeholder serials (как CleanWmiString у агента) — не сигналы «та же машина».
    _WEAK_SERIAL_EXACT = frozenset(
        {
            "none",
            "n/a",
            "na",
            "default string",
            "system serial number",
            "system product name",
            "system manufacturer",
            "to be filled by o.e.m.",
            "o.e.m.",
            "oem",
            "unknown",
            "not specified",
            "not available",
            "0",
            "00000000",
        }
    )


    # Скалярные hardware-id для duplicates / meta (не PK).
    IDENTITY_SCALAR_KEYS = (
        "serial_number",
        "smbios_uuid",
        "bios_serial",
        "identifying_number",
        "baseboard_serial",
    )


    # Merge match (вариант 2, без диска/hostname) — одна функция на список и merge_devices.
    MERGE_STRONG_KEYS = ("serial_number", "smbios_uuid")

    MERGE_WEAK_KEYS = ("bios_serial", "identifying_number", "baseboard_serial")


    @classmethod
    def _identity_values_equal(cls, key: str, left: Any, right: Any) -> bool:
        if not left or not right:
            return False
        if key == "smbios_uuid":
            a = cls.normalize_smbios_uuid(left)
            b = cls.normalize_smbios_uuid(right)
            return bool(a and b and a == b)
        a = cls.normalize_serial_number(left)
        b = cls.normalize_serial_number(right)
        return bool(a and b and a.casefold() == b.casefold())


    @classmethod
    def _matched_identity_keys(
        cls,
        keys: tuple[str, ...],
        left: dict[str, Any],
        right: dict[str, Any],
    ) -> list[str]:
        return [
            key
            for key in keys
            if cls._identity_values_equal(key, left.get(key), right.get(key))
        ]


    @classmethod
    def merge_identity_matched(
        cls,
        left: Optional[dict[str, Any]],
        right: Optional[dict[str, Any]],
    ) -> list[str]:
        """Поля, дающие право на склейку (пусто = кнопки merge нет).

        Сильное: достаточно одного из ``serial_number`` / ``smbios_uuid``.
        Слабая пара: ≥2 из ``bios_serial`` / ``identifying_number`` / ``baseboard_serial``.
        Hostname и ``disk_serial*`` не входят. OEM/пустые отсекаются нормализацией.
        """
        a = left if isinstance(left, dict) else {}
        b = right if isinstance(right, dict) else {}
        strong = cls._matched_identity_keys(cls.MERGE_STRONG_KEYS, a, b)
        weak = cls._matched_identity_keys(cls.MERGE_WEAK_KEYS, a, b)
        # strong непустой → strong+weak; иначе weak только при паре (≥2).
        if strong or len(weak) >= 2:
            return strong + weak
        return []


    @staticmethod
    def normalize_smbios_uuid(raw: Any) -> Optional[str]:
        """Нормализованный SMBIOS UUID или None для пустых/placeholder (all-F / all-zero)."""
        if raw is None:
            return None
        text = str(raw).strip().casefold()
        if not text:
            return None
        if text.startswith("{") and text.endswith("}"):
            text = text[1:-1].strip()
        compact = text.replace("-", "")
        if compact == "f" * 32 or compact == "0" * 32:
            return None
        return text


    @staticmethod
    def _serial_compact(text: str) -> str:
        """Как CleanHardwareSerial: без - _ пробелов и точек."""
        return (
            text.replace("-", "")
            .replace("_", "")
            .replace(" ", "")
            .replace(".", "")
        )


    @classmethod
    def normalize_serial_number(cls, raw: Any) -> Optional[str]:
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        folded = text.casefold()
        if folded in cls._WEAK_SERIAL_EXACT:
            return None
        if folded.startswith("to be filled") or folded.startswith("fill by oem"):
            return None
        compact = cls._serial_compact(folded)
        if not compact:
            return None
        if all(c == "0" for c in compact) or all(c == "f" for c in compact):
            return None
        return text


    def _pick_serial(
        self,
        *candidates: Any,
    ) -> Optional[str]:
        for raw in candidates:
            value = self.normalize_serial_number(raw)
            if value:
                return value
        return None


    def _disk_serials_from_hardware(self, hw: dict[str, Any]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for disk in hw.get("disks") or []:
            if not isinstance(disk, dict):
                continue
            serial = self.normalize_serial_number(disk.get("serial_number"))
            if not serial:
                continue
            key = serial.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(serial)
        return out


    def _disk_serials_from_meta(self, meta: dict[str, Any]) -> list[str]:
        raw = meta.get("disk_serials")
        if not isinstance(raw, list):
            # одиночное значение на всякий случай
            one = self.normalize_serial_number(meta.get("disk_serial_number"))
            return [one] if one else []
        out: list[str] = []
        seen: set[str] = set()
        for item in raw:
            serial = self.normalize_serial_number(item)
            if not serial:
                continue
            key = serial.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(serial)
        return out


    def extract_identity_signals(
        self,
        *,
        meta: Optional[dict[str, Any]] = None,
        hardware: Optional[dict[str, Any]] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Сигналы «та же железка» из inventory/meta (не PK, без merge).

        Скаляры: serial_number, smbios_uuid, bios_serial, identifying_number,
        baseboard_serial. Список: disk_serials (Win32_DiskDrive.SerialNumber).
        """
        meta = meta if isinstance(meta, dict) else {}
        hw = hardware if isinstance(hardware, dict) else None
        if hw is None and isinstance(payload, dict):
            raw_hw = payload.get("hardware")
            hw = raw_hw if isinstance(raw_hw, dict) else {}
        if hw is None:
            hw = {}
        ids = meta.get("hardware_ids") if isinstance(meta.get("hardware_ids"), dict) else {}

        serial = self._pick_serial(
            hw.get("serial_number"),
            meta.get("serial_number"),
            ids.get("serial_number"),
        )
        bios_serial = self._pick_serial(
            hw.get("bios_serial"),
            meta.get("bios_serial"),
            ids.get("bios_serial"),
        )
        identifying_number = self._pick_serial(
            hw.get("identifying_number"),
            meta.get("identifying_number"),
            ids.get("identifying_number"),
        )
        baseboard_serial = self._pick_serial(
            hw.get("baseboard_serial"),
            meta.get("baseboard_serial"),
            ids.get("baseboard_serial"),
        )

        uuid = self.normalize_smbios_uuid(hw.get("smbios_uuid"))
        if not uuid:
            uuid = self.normalize_smbios_uuid(hw.get("uuid"))
        if not uuid:
            uuid = self.normalize_smbios_uuid(meta.get("smbios_uuid"))
        if not uuid:
            uuid = self.normalize_smbios_uuid(ids.get("smbios_uuid"))

        disk_serials = self._disk_serials_from_hardware(hw)
        if not disk_serials:
            disk_serials = self._disk_serials_from_meta(meta)

        return {
            "serial_number": serial,
            "smbios_uuid": uuid,
            "bios_serial": bios_serial,
            "identifying_number": identifying_number,
            "baseboard_serial": baseboard_serial,
            "disk_serials": disk_serials,
        }


    def identity_signals_for_meta(self, signals: dict[str, Any]) -> dict[str, Any]:
        """Подмножество сигналов для записи в devices.meta_json."""
        out: dict[str, Any] = {}
        for key in self.IDENTITY_SCALAR_KEYS:
            value = signals.get(key)
            if value:
                out[key] = value
        disks = signals.get("disk_serials") or []
        if isinstance(disks, list) and disks:
            out["disk_serials"] = list(disks)
        return out


    def _identity_signals_enriched(
        self, bad_id: str, meta: dict[str, Any]
    ) -> dict[str, Any]:
        """meta + при пробелах — последний inventory (для старых снимков без кэша)."""
        signals = self.extract_identity_signals(meta=meta)
        need_inv = False
        for key in self.IDENTITY_SCALAR_KEYS:
            if not signals.get(key):
                need_inv = True
                break
        if not signals.get("disk_serials"):
            need_inv = True
        if not need_inv:
            return signals
        detail = self.get_device_detail(bad_id)
        if not detail:
            return signals
        payload = (detail.get("latest_inventory") or {}).get("payload")
        from_inv = self.extract_identity_signals(
            meta=detail.get("meta") or meta,
            payload=payload if isinstance(payload, dict) else None,
        )
        for key in self.IDENTITY_SCALAR_KEYS:
            if not signals.get(key):
                signals[key] = from_inv.get(key)
        if not signals.get("disk_serials"):
            signals["disk_serials"] = list(from_inv.get("disk_serials") or [])
        return signals


    def duplicate_signal_index(
        self,
        *,
        devices: Optional[list[dict[str, Any]]] = None,
        meta_only: bool = False,
    ) -> dict[str, Any]:
        """Индекс дублей: hostname + hardware ids (serial/uuid/bios/board/disk).

        Без auto-merge: только подсказки. Archived учитываются.
        ``devices`` — уже загруженные строки (без второго list_devices).
        ``meta_only`` — только meta (без get_device_detail на каждую строку).
        """
        by_host: dict[str, list[str]] = {}
        by_scalar: dict[str, dict[str, list[str]]] = {
            key: {} for key in self.IDENTITY_SCALAR_KEYS
        }
        by_disk: dict[str, list[str]] = {}
        rows: list[dict[str, Any]] = []

        device_rows = (
            devices if devices is not None else self.list_devices(archived=None)
        )
        for d in device_rows:
            bad_id = d["bad_id"]
            meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
            if meta_only:
                signals = self.extract_identity_signals(meta=meta)
            else:
                signals = self._identity_signals_enriched(bad_id, meta)
            hostname = (d.get("hostname") or "").strip()
            host_key = hostname.casefold() if hostname else ""
            scalar_keys = {
                key: (signals.get(key) or "").casefold()
                if key != "smbios_uuid"
                else (signals.get(key) or "")
                for key in self.IDENTITY_SCALAR_KEYS
            }
            # smbios already casefolded by normalize
            disk_keys = [
                s.casefold() for s in (signals.get("disk_serials") or []) if s
            ]
            row = {
                "bad_id": bad_id,
                "hostname": d.get("hostname"),
                "archived": d.get("archived"),
                "signals": signals,
                "host_key": host_key,
                "scalar_keys": scalar_keys,
                "disk_keys": disk_keys,
            }
            rows.append(row)
            if host_key:
                by_host.setdefault(host_key, []).append(bad_id)
            for key, value in scalar_keys.items():
                if value:
                    by_scalar[key].setdefault(value, []).append(bad_id)
            for disk_key in disk_keys:
                by_disk.setdefault(disk_key, []).append(bad_id)

        device_signals: dict[str, dict[str, Any]] = {}
        for row in rows:
            did = row["bad_id"]
            flags: dict[str, bool] = {
                "hostname": bool(
                    row["host_key"] and len(by_host.get(row["host_key"], [])) > 1
                )
            }
            for key, value in row["scalar_keys"].items():
                flags[key] = bool(value and len(by_scalar[key].get(value, [])) > 1)
            disk_dup = any(len(by_disk.get(k, [])) > 1 for k in row["disk_keys"])
            flags["disk_serial_number"] = disk_dup

            kinds = [name for name, hit in flags.items() if hit]
            signals = row["signals"]
            device_signals[did] = {
                **flags,
                "is_duplicate": bool(kinds),
                "kinds": kinds,
                "serial_value": signals.get("serial_number"),
                "smbios_uuid_value": signals.get("smbios_uuid"),
                "bios_serial_value": signals.get("bios_serial"),
                "identifying_number_value": signals.get("identifying_number"),
                "baseboard_serial_value": signals.get("baseboard_serial"),
                "disk_serials_value": list(signals.get("disk_serials") or []),
            }

        return {
            "by_hostname": by_host,
            "by_serial": by_scalar.get("serial_number") or {},
            "by_smbios_uuid": by_scalar.get("smbios_uuid") or {},
            "by_bios_serial": by_scalar.get("bios_serial") or {},
            "by_identifying_number": by_scalar.get("identifying_number") or {},
            "by_baseboard_serial": by_scalar.get("baseboard_serial") or {},
            "by_disk_serial": by_disk,
            "device_signals": device_signals,
        }


    def find_duplicate_devices(self, bad_id: str) -> dict[str, list[dict[str, Any]]]:
        """Другие устройства с совпавшим hostname / hardware id.

        Сигналы «та же железка», не PK. Автослияния нет.
        Бакеты не сужаются; на каждом кандидате ``merge_matched``
        (``merge_identity_matched``) — пусто = склейка недоступна.
        """
        empty: dict[str, list[dict[str, Any]]] = {
            "hostname": [],
            "serial_number": [],
            "smbios_uuid": [],
            "bios_serial": [],
            "identifying_number": [],
            "baseboard_serial": [],
            "disk_serial_number": [],
        }
        detail = self.get_device_detail(bad_id)
        if not detail:
            return empty
        payload = (detail.get("latest_inventory") or {}).get("payload")
        signals = self.extract_identity_signals(
            meta=detail.get("meta") if isinstance(detail.get("meta"), dict) else {},
            payload=payload if isinstance(payload, dict) else None,
        )
        hostname = (detail.get("hostname") or "").strip()
        my_disks = {
            s.casefold() for s in (signals.get("disk_serials") or []) if s
        }

        buckets: dict[str, list[dict[str, Any]]] = {k: [] for k in empty}

        for other in self.list_devices(archived=None):
            if other["bad_id"] == bad_id:
                continue
            other_meta = other.get("meta") if isinstance(other.get("meta"), dict) else {}
            other_signals = self.extract_identity_signals(meta=other_meta)
            # Одно правило с merge_devices: пусто = UI без кнопки склейки.
            merge_matched = self.merge_identity_matched(signals, other_signals)

            base = {
                "bad_id": other["bad_id"],
                "hostname": other["hostname"],
                "archived": other.get("archived"),
                "merge_matched": list(merge_matched),
            }

            other_hn = (other.get("hostname") or "").strip()
            if hostname and other_hn and hostname.casefold() == other_hn.casefold():
                buckets["hostname"].append(dict(base))

            for key in (
                "serial_number",
                "smbios_uuid",
                "bios_serial",
                "identifying_number",
                "baseboard_serial",
            ):
                mine = signals.get(key)
                theirs = other_signals.get(key)
                if not mine or not theirs:
                    continue
                if key == "smbios_uuid":
                    match = mine == theirs
                else:
                    match = str(mine).casefold() == str(theirs).casefold()
                if match:
                    row = dict(base)
                    row[key] = theirs
                    buckets[key].append(row)

            other_disks = {
                s.casefold() for s in (other_signals.get("disk_serials") or []) if s
            }
            shared = sorted(my_disks & other_disks)
            if shared:
                row = dict(base)
                row["disk_serial_number"] = shared[0]
                row["disk_serials"] = shared
                buckets["disk_serial_number"].append(row)

        return buckets


    def merge_devices(
        self,
        survivor_id: str,
        donor_id: str,
        *,
        stale_after_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Ручная склейка дублей: история donor → survivor, donor в архив+revoke.

        Identity: ``merge_identity_matched`` (сильное serial/uuid или слабая
        пара bios/identifying/board). Donor — stale или archived.
        Hostname/disk в match не входят. Без UNIQUE(serial), PK не меняется.
        Одна транзакция: archive **и** revoke api_key донора.

        Raises ValueError с кодом:
        ``merge_same_device`` · ``merge_survivor_missing`` · ``merge_donor_missing``
        · ``merge_no_identity_match`` · ``merge_donor_not_stale_or_archived``.
        """
        from .device_health import device_silence_status

        survivor_id = (survivor_id or "").strip()
        donor_id = (donor_id or "").strip()
        if not survivor_id or not donor_id:
            raise ValueError("merge_survivor_missing")
        if survivor_id == donor_id:
            raise ValueError("merge_same_device")

        survivor = self.get_device_detail(survivor_id)
        if not survivor:
            raise ValueError("merge_survivor_missing")
        donor = self.get_device_detail(donor_id)
        if not donor:
            raise ValueError("merge_donor_missing")

        s_meta = survivor.get("meta") if isinstance(survivor.get("meta"), dict) else {}
        d_meta = donor.get("meta") if isinstance(donor.get("meta"), dict) else {}
        s_sig = self._identity_signals_enriched(survivor_id, s_meta)
        d_sig = self._identity_signals_enriched(donor_id, d_meta)

        matched = self.merge_identity_matched(s_sig, d_sig)
        if not matched:
            raise ValueError("merge_no_identity_match")

        donor_archived = bool(donor.get("archived"))
        if not donor_archived:
            silence = device_silence_status(
                donor.get("last_seen_at"),
                stale_after_seconds=stale_after_seconds,
            )
            if silence.get("status") != "stale":
                raise ValueError("merge_donor_not_stale_or_archived")

        donor_hostname = donor.get("hostname")
        now = utc_now()
        detail = {
            "donor_id": donor_id,
            "hostname": donor_hostname,
            "matched": matched,
        }
        detail_json = _compact_json(detail)
        summary = (
            f"Склейка с {donor_hostname}"
            if donor_hostname
            else f"Склейка с {donor_id}"
        )

        with self.connection() as conn:
            # Повторная проверка существования внутри транзакции (TOCTOU).
            s_row = conn.execute(
                "SELECT bad_id FROM devices WHERE bad_id = %s",
                (survivor_id,),
            ).fetchone()
            d_row = conn.execute(
                """
                SELECT bad_id, hostname, last_seen_at, archived
                FROM devices WHERE bad_id = %s
                """,
                (donor_id,),
            ).fetchone()
            if not s_row:
                raise ValueError("merge_survivor_missing")
            if not d_row:
                raise ValueError("merge_donor_missing")

            snap_cur = conn.execute(
                """
                UPDATE inventory_snapshots
                SET bad_id = %s
                WHERE bad_id = %s
                """,
                (survivor_id, donor_id),
            )
            ev_cur = conn.execute(
                """
                UPDATE device_events
                SET bad_id = %s
                WHERE bad_id = %s
                """,
                (survivor_id, donor_id),
            )
            # archived ≠ block auth — revoke в той же транзакции (#96 review).
            conn.execute(
                """
                UPDATE devices
                SET archived = 1, revoked = 1, api_key_lookup = NULL
                WHERE bad_id = %s
                """,
                (donor_id,),
            )
            self._insert_device_event(
                conn, survivor_id, "device_merged", summary, detail_json, now
            )
            snapshots_moved = int(snap_cur.rowcount or 0)
            events_moved = int(ev_cur.rowcount or 0)

        return {
            "survivor_id": survivor_id,
            "donor_id": donor_id,
            "donor_hostname": donor_hostname,
            "matched": matched,
            "snapshots_moved": snapshots_moved,
            "events_moved": events_moved,
            "donor_archived": True,
            "donor_revoked": True,
        }
