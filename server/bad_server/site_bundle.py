"""Site backup bundle: DB + key files + MSI mirror meta (+ MSI files)."""

from __future__ import annotations

import io
import json
import logging
import tarfile
import tempfile
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


def build_site_bundle(
    *,
    db: Database,
    db_path: Path,
    backup_dir: Path,
    updates_dir: Path,
    data_key_file: Path,
    session_secret_file: Path,
    include_msi_files: bool = False,
    extra_key_files: Optional[list[Path]] = None,
) -> tuple[bytes, str]:
    """Собрать tar.gz site bundle. Возвращает (bytes, filename)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Свежий снимок БД через online backup (не копировать live WAL напрямую).
    snap = run_daily_backup(db_path, backup_dir)
    if not snap.get("ok"):
        raise RuntimeError(snap.get("error") or "SQLite backup failed")
    db_snapshot = Path(snap["path"])

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

    key_paths: list[Path] = []
    for p in (
        data_key_file,
        session_secret_file,
        *DEFAULT_KEY_CANDIDATES,
        *(extra_key_files or []),
    ):
        if p and p not in key_paths:
            key_paths.append(Path(p))

    included: list[dict[str, Any]] = []
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # DB snapshot
        info = _add_file(tar, "bad.db", db_snapshot)
        if info:
            included.append(info)

        # Keys (contents never rendered to HTML — only inside download)
        for path in key_paths:
            if not path.is_file():
                continue
            arc = f"keys/{path.name}"
            info = _add_file(tar, arc, path)
            if info:
                included.append({**info, "kind": "key"})

        # Mirror meta
        meta_bytes = json.dumps(mirror_meta, indent=2, ensure_ascii=False).encode(
            "utf-8"
        )
        meta_info = tarfile.TarInfo(name="agent-updates/manifest.json")
        meta_info.size = len(meta_bytes)
        tar.addfile(meta_info, io.BytesIO(meta_bytes))
        included.append(
            {
                "arcname": "agent-updates/manifest.json",
                "size_bytes": len(meta_bytes),
                "kind": "mirror-meta",
            }
        )

        if include_msi_files:
            updates_root = Path(updates_dir)
            for v in versions:
                fp = Path(v["file_path"]) if v.get("file_path") else None
                if not fp or not fp.is_file():
                    # try by msi_name under updates_dir
                    candidate = updates_root / v["msi_name"]
                    fp = candidate if candidate.is_file() else None
                if not fp:
                    continue
                try:
                    fp.resolve().relative_to(updates_root.resolve())
                except ValueError:
                    logger.warning("Skip MSI outside updates dir: %s", fp)
                    continue
                arc = f"agent-updates/files/{fp.name}"
                info = _add_file(tar, arc, fp)
                if info:
                    included.append({**info, "kind": "msi"})

        manifest = {
            "format": "bad-site-bundle/v1",
            "created_at": _utc_stamp(),
            "product_version": __version__,
            "files": included,
            "notes": [
                "Contains SQLite snapshot and site key files — treat as secret.",
                "Restore: deploy/debian/restore-site-bundle.sh (stop service first).",
            ],
        }
        man_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        man_info = tarfile.TarInfo(name=BUNDLE_MANIFEST_NAME)
        man_info.size = len(man_bytes)
        tar.addfile(man_info, io.BytesIO(man_bytes))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"bad-site-bundle-{stamp}.tar.gz"
    return buf.getvalue(), filename


def inspect_site_bundle(archive: Path) -> dict[str, Any]:
    """Прочитать manifest без распаковки ключей в plaintext logs."""
    with tarfile.open(archive, mode="r:gz") as tar:
        try:
            member = tar.getmember(BUNDLE_MANIFEST_NAME)
        except KeyError:
            return {"ok": False, "error": "manifest.json missing"}
        f = tar.extractfile(member)
        if not f:
            return {"ok": False, "error": "cannot read manifest"}
        data = json.loads(f.read().decode("utf-8"))
    return {"ok": True, "manifest": data}
