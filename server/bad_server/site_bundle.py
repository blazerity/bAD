"""Site backup bundle: DB + key files + MSI mirror meta (+ MSI files)."""

from __future__ import annotations

import io
import json
import logging
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .backup import run_daily_backup
from .db import Database

logger = logging.getLogger(__name__)

BUNDLE_MANIFEST_NAME = "manifest.json"
DEFAULT_KEY_CANDIDATES = (
    Path("/etc/bad/data_key"),
    Path("/etc/bad/session_secret"),
    Path("/etc/bad/site.env"),
    Path("/etc/bad/enrollment_token"),
)


def _utc_stamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _add_file(tar: tarfile.TarFile, arcname: str, path: Path) -> Optional[dict[str, Any]]:
    if not path.is_file():
        return None
    tar.add(str(path), arcname=arcname)
    return {
        "arcname": arcname,
        "source": str(path),
        "size_bytes": path.stat().st_size,
    }


def _dedupe_paths(*groups: Any) -> list[Path]:
    out: list[Path] = []
    for group in groups:
        for p in group if isinstance(group, (list, tuple)) else (group,):
            if not p:
                continue
            path = Path(p)
            if path not in out:
                out.append(path)
    return out


def _write_json_member(tar: tarfile.TarFile, arcname: str, payload: dict[str, Any]) -> int:
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    info = tarfile.TarInfo(name=arcname)
    info.size = len(raw)
    tar.addfile(info, io.BytesIO(raw))
    return len(raw)


def build_key_escrow_archive(
    *,
    data_key_file: Path,
    session_secret_file: Path,
    extra_key_files: Optional[list[Path]] = None,
) -> tuple[bytes, str]:
    """Маленький tar.gz только key files (SEC-005 escrow, без DB)."""
    key_paths = _dedupe_paths(data_key_file, session_secret_file, extra_key_files or [])

    included: list[dict[str, Any]] = []
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in key_paths:
            info = _add_file(tar, f"keys/{path.name}", path)
            if info:
                included.append({**info, "kind": "key"})
        if not included:
            raise RuntimeError(
                "Нет файлов ключей для escrow "
                f"({data_key_file}, {session_secret_file})"
            )
        _write_json_member(
            tar,
            BUNDLE_MANIFEST_NAME,
            {
                "format": "bad-key-escrow/v1",
                "created_at": _utc_stamp(),
                "product_version": __version__,
                "files": included,
                "notes": [
                    "Escrow only — no DB dump. Treat as secret (SEC-005).",
                    "Daily pg_dump alone is not full DR when keys are external.",
                ],
            },
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return buf.getvalue(), f"bad-key-escrow-{stamp}.tar.gz"


def build_site_bundle(
    *,
    db: Database,
    backup_dir: Path,
    updates_dir: Path,
    data_key_file: Path,
    session_secret_file: Path,
    include_msi_files: bool = False,
    extra_key_files: Optional[list[Path]] = None,
    database_url: Optional[str] = None,
) -> tuple[bytes, str]:
    """Собрать tar.gz site bundle. Возвращает (bytes, filename)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    url = (database_url or getattr(db, "database_url", None) or "").strip()
    if not url:
        raise RuntimeError("BAD_DATABASE_URL required for site bundle")
    snap = run_daily_backup(backup_dir, database_url=url)
    if not snap.get("ok"):
        raise RuntimeError(snap.get("error") or "pg_dump failed")
    db_snapshot = Path(snap["path"])
    db_arcname = "bad.dump"

    versions = db.list_agent_msi_versions()
    mirror_meta = {
        "versions": [
            {
                "version": v["version"],
                "msi_name": v["msi_name"],
                "sha256": v["sha256"],
                "source": v.get("source"),
                "source_tag": v.get("source_tag"),
                "release_url": v.get("release_url"),
                "mirrored_at": v.get("mirrored_at") or v.get("synced_at"),
                "file_path": v.get("file_path"),
            }
            for v in versions
        ],
        "latest": db.get_agent_update(),
    }

    key_paths = _dedupe_paths(
        data_key_file,
        session_secret_file,
        DEFAULT_KEY_CANDIDATES,
        extra_key_files or [],
    )
    included: list[dict[str, Any]] = []
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = _add_file(tar, db_arcname, db_snapshot)
        if info:
            included.append({**info, "kind": "db", "backend": "postgres"})

        for path in key_paths:
            info = _add_file(tar, f"keys/{path.name}", path)
            if info:
                included.append({**info, "kind": "key"})

        meta_size = _write_json_member(tar, "agent-updates/manifest.json", mirror_meta)
        included.append(
            {
                "arcname": "agent-updates/manifest.json",
                "size_bytes": meta_size,
                "kind": "mirror-meta",
            }
        )

        if include_msi_files:
            updates_root = Path(updates_dir).resolve()
            for v in versions:
                fp = Path(v["file_path"]) if v.get("file_path") else None
                if not fp or not fp.is_file():
                    ver = (v.get("version") or "").strip()
                    name = (v.get("msi_name") or "").strip()
                    candidate = updates_root / ver / name if ver and name else None
                    fp = candidate if candidate and candidate.is_file() else None
                if not fp:
                    continue
                try:
                    fp.resolve().relative_to(updates_root)
                except ValueError:
                    logger.warning("Skip MSI outside updates dir: %s", fp)
                    continue
                info = _add_file(tar, f"agent-updates/files/{fp.name}", fp)
                if info:
                    included.append({**info, "kind": "msi"})

        _write_json_member(
            tar,
            BUNDLE_MANIFEST_NAME,
            {
                "format": "bad-site-bundle/v1",
                "created_at": _utc_stamp(),
                "product_version": __version__,
                "db_backend": "postgres",
                "files": included,
                "notes": [
                    "Contains pg_dump (-Fc) and site key files — treat as secret.",
                    "DB dump ≠ keys. Restore: deploy/debian/restore-site-bundle.sh.",
                ],
            },
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return buf.getvalue(), f"bad-site-bundle-{stamp}.tar.gz"
