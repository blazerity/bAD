"""Daily SQLite backup: keep today + yesterday under a backups directory."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

KEEP_DAILY = 2  # today + yesterday


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def backup_filename(day: date) -> str:
    return f"bad-{day.isoformat()}.db"


def list_backup_files(backup_dir: Path) -> list[Path]:
    if not backup_dir.is_dir():
        return []
    files = sorted(backup_dir.glob("bad-????-??-??.db"))
    return files


def backup_status(backup_dir: Path) -> dict[str, Any]:
    files = list_backup_files(backup_dir)
    latest: Optional[Path] = files[-1] if files else None
    return {
        "backup_dir": str(backup_dir),
        "files": [
            {
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "mtime": datetime.fromtimestamp(
                    f.stat().st_mtime, tz=timezone.utc
                )
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
            for f in files
        ],
        "latest": latest.name if latest else None,
        "today_exists": (backup_dir / backup_filename(utc_today())).is_file(),
    }


def run_daily_backup(db_path: Path, backup_dir: Path) -> dict[str, Any]:
    """Create/replace today's snapshot via SQLite Online Backup API; prune old."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        backup_dir.chmod(0o700)
    except OSError:
        pass

    today = utc_today()
    dest = backup_dir / backup_filename(today)
    src = Path(db_path)
    if not src.is_file():
        return {"ok": False, "error": f"DB missing: {src}", "path": str(dest)}

    try:
        src_conn = sqlite3.connect(str(src))
        try:
            # Temporary file then replace — safer if process dies mid-copy.
            tmp = dest.with_suffix(".db.tmp")
            if tmp.exists():
                tmp.unlink()
            dst_conn = sqlite3.connect(str(tmp))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
            tmp.replace(dest)
            try:
                dest.chmod(0o600)
            except OSError:
                pass
        finally:
            src_conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("SQLite backup failed")
        return {"ok": False, "error": str(exc), "path": str(dest)}

    # Keep only the newest KEEP_DAILY dated files.
    files = list_backup_files(backup_dir)
    removed: list[str] = []
    if len(files) > KEEP_DAILY:
        for old in files[:-KEEP_DAILY]:
            try:
                old.unlink()
                removed.append(old.name)
            except OSError:
                logger.warning("Failed to remove old backup %s", old)

    # Also drop anything older than yesterday-1 explicitly by date parse.
    cutoff = today - timedelta(days=KEEP_DAILY - 1)
    for f in list_backup_files(backup_dir):
        try:
            day = date.fromisoformat(f.stem.replace("bad-", "", 1))
        except ValueError:
            continue
        if day < cutoff:
            try:
                f.unlink()
                if f.name not in removed:
                    removed.append(f.name)
            except OSError:
                pass

    logger.info("SQLite backup written to %s", dest)
    return {
        "ok": True,
        "path": str(dest),
        "name": dest.name,
        "removed": removed,
        "status": backup_status(backup_dir),
    }
