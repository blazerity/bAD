"""Ежедневный бэкап SQLite: сегодня + вчера в каталоге backups."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

KEEP_DAILY = 2  # сегодня + вчера


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
        # Daily SQLite alone is never full DR when keys live in files (SEC-005).
        "daily_is_full_dr": False,
        "daily_hint_ru": (
            "Ежедневный снимок SQLite — inventory/метаданные, не полный DR. "
            "Ключи escrow и site-bundle — отдельно."
        ),
    }


def backup_keys_status(
    *,
    data_key_file: Path,
    session_secret_file: Path,
    secrets: dict[str, Any],
    last_key_escrow_at: Optional[str] = None,
) -> dict[str, Any]:
    """SEC-005 honesty: keys external vs legacy-in-SQLite for backups UI/API."""
    data_exists = data_key_file.is_file() and data_key_file.stat().st_size > 0
    session_exists = (
        session_secret_file.is_file() and session_secret_file.stat().st_size > 0
    )
    legacy = bool(secrets.get("legacy_keys_in_sqlite"))
    keys_external = bool(secrets.get("ok")) and not legacy
    return {
        "keys_external": keys_external,
        "legacy_keys_in_sqlite": legacy,
        "data_key_path": str(data_key_file),
        "session_secret_path": str(session_secret_file),
        "data_key_exists": data_exists,
        "session_secret_exists": session_exists,
        "data_key_source": secrets.get("data_key_source"),
        "session_secret_source": secrets.get("session_secret_source"),
        "last_key_escrow_at": last_key_escrow_at,
        "hint_ru": secrets.get("hint_ru"),
        "escrow_hint_ru": (
            "Скачайте escrow ключей отдельно от daily DB; храните как секрет. "
            "Site bundle = полный DR (DB+keys) — тоже только в сейфе."
            if keys_external
            else (
                "Legacy: keys в SQLite — любой DB backup = полный компромисс. "
                "Вынесите keys в /etc/bad/* (440)."
                if legacy
                else "Файлы ключей не найдены — проверьте /etc/bad/data_key и session_secret."
            )
        ),
    }


def run_daily_backup(db_path: Path, backup_dir: Path) -> dict[str, Any]:
    """Создать/заменить сегодняшний снимок через SQLite Online Backup API; удалить старые."""
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
            # Временный файл, затем replace — безопаснее при обрыве копирования.
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

    # Оставить сегодня + вчера (удалить более старые файлы по имени).
    cutoff = today - timedelta(days=KEEP_DAILY - 1)
    removed: list[str] = []
    for f in list_backup_files(backup_dir):
        try:
            day = date.fromisoformat(f.stem.replace("bad-", "", 1))
        except ValueError:
            continue
        if day < cutoff:
            try:
                f.unlink()
                removed.append(f.name)
            except OSError:
                logger.warning("Failed to remove old backup %s", f)

    logger.info("SQLite backup written to %s", dest)
    return {
        "ok": True,
        "path": str(dest),
        "name": dest.name,
        "removed": removed,
        "status": backup_status(backup_dir),
    }
