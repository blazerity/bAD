"""Зеркалировать MSI (GitHub / upload) и отвечать на проверки обновлений агента."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from .agent_config import (
    UPDATE_TARGET_LATEST,
    compute_effective_config,
    sanitize_update_target,
)
from .config import Settings
from .db import Database
from .github_release import (
    fetch_latest_release_assets,
    mirror_release_to_dir,
    safe_msi_filename,
    sha256_hex,
)

logger = logging.getLogger(__name__)

_SEMVER_RE = re.compile(
    r"^\s*v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)",
    re.IGNORECASE,
)
_VERSION_FROM_MSI_RE = re.compile(
    r"^bad-agent-(?P<ver>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)\.msi$",
    re.IGNORECASE,
)


def parse_semver(value: str) -> Optional[tuple[int, int, int]]:
    if not value:
        return None
    m = _SEMVER_RE.match(value)
    if not m:
        return None
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def is_newer(candidate: str, current: str) -> bool:
    """True, если candidate — более высокий semver, чем current."""
    a = parse_semver(candidate)
    b = parse_semver(current)
    if a is None:
        return False
    if b is None:
        return True
    return a > b


def version_from_msi_name(msi_name: str) -> Optional[str]:
    m = _VERSION_FROM_MSI_RE.match((msi_name or "").strip())
    return m.group("ver") if m else None


def sync_from_github(db: Database, settings: Settings) -> dict[str, Any]:
    """Скачать assets последнего Release, сохранить MSI в каталог updates, записать в БД."""
    if not settings.github_repo:
        raise RuntimeError("BAD_GITHUB_REPO is not configured")

    # Токены в лог не писать.
    logger.info(
        "Syncing agent update from GitHub repo=%s",
        settings.github_repo,
    )
    assets = fetch_latest_release_assets(
        repo=settings.github_repo,
        token=settings.github_token or "",
        api_base=settings.github_api_base,
    )
    ver_dir = settings.agent_updates_dir / assets.version
    path = mirror_release_to_dir(
        assets,
        ver_dir,
        token=settings.github_token or "",
    )
    record = db.set_agent_update(
        version=assets.version,
        msi_name=assets.msi_name,
        sha256=assets.sha256,
        file_path=str(path),
        source_tag=assets.tag,
        release_url=assets.release_url,
        source="github",
    )
    prune_old_msi_versions(db, settings, keep=MSI_VERSION_CAP)
    logger.info(
        "Mirrored agent MSI version=%s sha256=%s path=%s",
        record["version"],
        record["sha256"],
        record["file_path"],
    )
    return record


MSI_VERSION_CAP = 10


def ingest_uploaded_msi(
    db: Database,
    settings: Settings,
    *,
    raw: bytes,
    filename: str,
    version: str = "",
    sha256: str = "",
    manifest_json: Optional[str] = None,
    set_as_latest: bool = True,
) -> dict[str, Any]:
    """Ручная заливка MSI (+ optional agent-release.json) для air-gap.

    Диск: ``{updates_dir}/{version}/bad-agent-{version}.msi`` (+ agent-release.json).
    """
    settings.agent_updates_dir.mkdir(parents=True, exist_ok=True)
    dest_root = settings.agent_updates_dir.resolve()

    manifest: dict[str, Any] = {}
    if manifest_json:
        try:
            parsed = json.loads(manifest_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid manifest JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Manifest must be a JSON object")
        manifest = parsed

    ver = (
        sanitize_update_target(version)
        or sanitize_update_target(manifest.get("version"))
        or version_from_msi_name((filename or "").strip())
        or version_from_msi_name(str(manifest.get("msi_name") or ""))
    )
    if not ver or ver == UPDATE_TARGET_LATEST:
        raise ValueError("version required (form, manifest, or bad-agent-X.Y.Z.msi name)")

    msi_name = safe_msi_filename(f"bad-agent-{ver}.msi")
    digest = sha256_hex(raw)
    expected = (sha256 or str(manifest.get("sha256") or "")).strip().lower()
    if expected and expected != digest:
        raise ValueError(f"sha256 mismatch: expected {expected}, got {digest}")

    ver_dir = (settings.agent_updates_dir / ver).resolve()
    try:
        ver_dir.relative_to(dest_root)
    except ValueError as exc:
        raise ValueError("version dir escapes updates dir") from exc
    ver_dir.mkdir(parents=True, exist_ok=True)

    target = (ver_dir / msi_name).resolve()
    try:
        target.relative_to(dest_root)
    except ValueError as exc:
        raise ValueError("MSI path escapes updates dir") from exc

    tmp = (ver_dir / f".{msi_name}.tmp").resolve()
    tmp.write_bytes(raw)
    tmp.replace(target)
    try:
        target.chmod(0o640)
    except OSError:
        pass

    side = ver_dir / "agent-release.json"
    side.write_text(
        json.dumps(
            {
                "version": ver,
                "msi_name": msi_name,
                "sha256": digest,
                "source": "upload",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    record = db.upsert_agent_msi_version(
        version=ver,
        msi_name=msi_name,
        sha256=digest,
        file_path=str(target),
        source="upload",
        source_tag="upload",
        release_url=None,
        set_as_latest=set_as_latest,
    )
    prune_old_msi_versions(db, settings, keep=MSI_VERSION_CAP)
    return record


def set_latest_msi_version(db: Database, version: str) -> dict[str, Any]:
    """Переставить указатель latest на существующую версию (rollback pointer)."""
    row = db.get_agent_msi_version(version)
    if not row:
        raise ValueError(f"version not in catalog: {version}")
    return db.upsert_agent_msi_version(
        version=row["version"],
        msi_name=row["msi_name"],
        sha256=row["sha256"],
        file_path=row["file_path"],
        source=row.get("source") or "github",
        source_tag=row.get("source_tag"),
        release_url=row.get("release_url"),
        set_as_latest=True,
        force_latest=True,
    )


def versions_pinned_in_config(db: Database) -> set[str]:
    """Semver pins из политик и device overrides."""
    pinned: set[str] = set()
    for policy in db.list_agent_policies():
        settings = policy.get("settings") or {}
        target = sanitize_update_target(settings.get("update_target"))
        if target and target != UPDATE_TARGET_LATEST:
            pinned.add(target)
    # overrides
    for d in db.list_devices(archived=None):
        ov = db.get_device_config_override(d["device_id"])
        if not ov:
            continue
        target = sanitize_update_target((ov.get("settings") or {}).get("update_target"))
        if target and target != UPDATE_TARGET_LATEST:
            pinned.add(target)
    return pinned


def delete_msi_version(
    db: Database, settings: Settings, version: str
) -> None:
    """Удалить версию с запретом, если latest или pinned."""
    ver = (version or "").strip()
    row = db.get_agent_msi_version(ver)
    if not row:
        raise ValueError("version not found")
    latest = db.get_agent_update()
    if latest and latest.get("version") == ver:
        raise ValueError("cannot delete latest — set another latest first")
    if ver in versions_pinned_in_config(db):
        raise ValueError("cannot delete — pinned by policy/override")
    db.delete_agent_msi_version(ver)
    # remove version dir if under updates_dir
    try:
        fp = Path(row["file_path"]).resolve()
        root = settings.agent_updates_dir.resolve()
        fp.relative_to(root)
        ver_dir = fp.parent
        if ver_dir.name == ver and ver_dir.is_dir():
            for child in ver_dir.iterdir():
                if child.is_file():
                    child.unlink()
            ver_dir.rmdir()
        elif fp.is_file():
            fp.unlink()
    except (OSError, ValueError):
        pass


def prune_old_msi_versions(
    db: Database, settings: Settings, *, keep: int = MSI_VERSION_CAP
) -> list[str]:
    """Удалить самые старые версии сверх cap (не latest, не pinned)."""
    keep = max(1, int(keep))
    removed: list[str] = []
    # Pins/latest не меняются от удаления MSI — один скан на prune.
    pinned = versions_pinned_in_config(db)
    latest = (db.get_agent_update() or {}).get("version")
    while True:
        versions = db.list_agent_msi_versions()  # newest first
        if len(versions) <= keep:
            break
        # oldest first candidates
        candidate = None
        for row in reversed(versions):
            ver = row["version"]
            if ver == latest or ver in pinned:
                continue
            candidate = ver
            break
        if not candidate:
            break
        try:
            delete_msi_version(db, settings, candidate)
            removed.append(candidate)
        except ValueError:
            break
    return removed


def resolve_target_msi(
    db: Database,
    target_version: str,
) -> Optional[dict[str, Any]]:
    """Resolve policy target → MSI catalog row."""
    target = sanitize_update_target(target_version) or UPDATE_TARGET_LATEST
    if target == UPDATE_TARGET_LATEST:
        return db.get_agent_update()
    return db.get_agent_msi_version(target)


def effective_settings_for_device(
    db: Database,
    device: dict[str, Any],
    *,
    policies: Optional[list[dict[str, Any]]] = None,
    override_settings: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Эффективные agent settings (defaults < policies < override).

    Без get_device_detail: meta на устройстве + опционально override из batch-map.
    """
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    override = override_settings
    if override is None:
        row = db.get_device_config_override(device.get("device_id") or "")
        override = row.get("settings") if row else None
    computed = compute_effective_config(
        hostname=device.get("hostname"),
        meta=meta,
        inventory_payload=None,
        tags=device.get("tags"),
        policies=policies if policies is not None else db.list_agent_policies(),
        override=override if isinstance(override, dict) else None,
    )
    return computed.get("settings") or {}


def effective_update_target_for_device(
    db: Database,
    device: dict[str, Any],
    *,
    policies: Optional[list[dict[str, Any]]] = None,
) -> str:
    """Эффективный update_target для устройства (defaults < policies < override)."""
    settings = effective_settings_for_device(db, device, policies=policies)
    return (
        sanitize_update_target(settings.get("update_target"))
        or UPDATE_TARGET_LATEST
    )


def _semver_equal(a: str, b: str) -> bool:
    pa, pb = parse_semver(a), parse_semver(b)
    if pa is not None and pb is not None:
        return pa == pb
    return (a or "").strip() == (b or "").strip()


def check_update(
    db: Database,
    current: str,
    *,
    device: Optional[dict[str, Any]] = None,
    target_version: Optional[str] = None,
    download_path: str = "/v1/agent/update/msi",
) -> dict[str, Any]:
    """Проверка обновления с учётом target (latest или pin).

    ``update_available`` при target ≠ current (в т.ч. downgrade) — контракт 0.10.
    """
    if target_version is None and device is not None:
        target_version = effective_update_target_for_device(db, device)
    target_version = (
        sanitize_update_target(target_version) or UPDATE_TARGET_LATEST
    )
    mirrored = resolve_target_msi(db, target_version)
    if not mirrored:
        reason = "mirror_empty" if target_version == UPDATE_TARGET_LATEST else "broken_pin"
        return {
            "update_available": False,
            "version": None,
            "target_version": None,
            "sha256": None,
            "url": None,
            "current": current,
            "target": target_version,
            "reason": reason,
        }
    target_ver = mirrored["version"]
    available = not _semver_equal(target_ver, current or "")
    reason = "ok" if available else "already_on_target"
    if available and is_newer(current or "0.0.0", target_ver):
        reason = "downgrade"
    elif available and is_newer(target_ver, current or "0.0.0"):
        reason = "upgrade"
    url = f"{download_path}?version={target_ver}" if available else None
    return {
        "update_available": available,
        "version": target_ver,
        "target_version": target_ver,
        "sha256": mirrored["sha256"],
        "url": url,
        "current": current,
        "msi_name": mirrored["msi_name"],
        "synced_at": mirrored.get("synced_at") or mirrored.get("mirrored_at"),
        "target": target_version,
        "source": mirrored.get("source"),
        "reason": reason,
    }


def ops_update_signals(
    db: Database,
    *,
    stale_after_seconds: int,
    active: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Сводка для Обзора: зеркало, drift vs policy target, revoke/recovery."""
    from .device_health import device_silence_status

    versions = db.list_agent_msi_versions()
    latest = db.get_agent_update()
    versions_by_ver = {v["version"]: v for v in versions}
    target_msi_cache: dict[str, Optional[dict[str, Any]]] = {}

    def resolve_target_cached(target_version: str) -> Optional[dict[str, Any]]:
        target = sanitize_update_target(target_version) or UPDATE_TARGET_LATEST
        if target in target_msi_cache:
            return target_msi_cache[target]
        if target == UPDATE_TARGET_LATEST:
            mirrored = latest
        else:
            mirrored = versions_by_ver.get(target)
            if mirrored is None:
                mirrored = db.get_agent_msi_version(target)
        target_msi_cache[target] = mirrored
        return mirrored

    if active is None:
        active = db.list_devices(archived=False)
    policies = db.list_agent_policies()
    overrides = db.list_device_config_overrides_map()
    drift: list[dict[str, Any]] = []
    pinned_missing: list[dict[str, Any]] = []
    revoked_active = 0
    for d in active:
        if d.get("revoked"):
            revoked_active += 1
            continue
        # {} = нет override; None нельзя — effective_* уйдёт в get_device_config_override (N+1)
        ov = overrides.get(d.get("device_id") or "", {})
        settings = effective_settings_for_device(
            db,
            d,
            policies=policies,
            override_settings=ov,
        )
        target = (
            sanitize_update_target(settings.get("update_target"))
            or UPDATE_TARGET_LATEST
        )
        mirrored = resolve_target_cached(target)
        if target != UPDATE_TARGET_LATEST and not mirrored:
            pinned_missing.append(
                {
                    "device_id": d["device_id"],
                    "hostname": d.get("hostname"),
                    "target": target,
                    "agent_version": d.get("agent_version"),
                }
            )
            continue
        want = mirrored["version"] if mirrored else None
        have = (d.get("agent_version") or "").strip()
        if want and have and is_newer(want, have):
            # Only flag when updates enabled for this device.
            if not settings.get("update_enabled", True):
                continue
            silence = device_silence_status(
                d.get("last_seen_at"), stale_after_seconds=stale_after_seconds
            )
            drift.append(
                {
                    "device_id": d["device_id"],
                    "hostname": d.get("hostname"),
                    "agent_version": have,
                    "target": target,
                    "want_version": want,
                    "silence": silence.get("status"),
                }
            )

    return {
        "mirror_count": len(versions),
        "latest_version": latest.get("version") if latest else None,
        "latest_synced_at": (latest or {}).get("synced_at")
        or (latest or {}).get("mirrored_at"),
        "mirror_empty": not versions,
        "version_drift": drift[:25],
        "version_drift_count": len(drift),
        "pinned_missing": pinned_missing[:25],
        "pinned_missing_count": len(pinned_missing),
        "revoked_active": revoked_active,
        "versions": [
            {
                "version": v["version"],
                "source": v.get("source"),
                "mirrored_at": v.get("mirrored_at") or v.get("synced_at"),
            }
            for v in versions[:12]
        ],
    }
