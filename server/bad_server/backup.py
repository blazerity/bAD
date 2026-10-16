"""Ежедневный бэкап: SQLite Online Backup или pg_dump (сегодня + вчера)."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

KEEP_DAILY = 2  # сегодня + вчера


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def backup_filename_sqlite(day: date) -> str:
    return f"bad-{day.isoformat()}.db"


def backup_filename_pg(day: date) -> str:
    return f"bad-{day.isoformat()}.dump"


def list_backup_files(backup_dir: Path, *, postgres: bool = False) -> list[Path]:
    if not backup_dir.is_dir():
        return []
    pattern = "bad-????-??-??.dump" if postgres else "bad-????-??-??.db"
    return sorted(backup_dir.glob(pattern))


def backup_status(
    backup_dir: Path, *, database_url: Optional[str] = None
) -> dict[str, Any]:
    postgres = bool((database_url or "").strip())
    files = list_backup_files(backup_dir, postgres=postgres)
    latest: Optional[Path] = files[-1] if files else None
    today_name = (
        backup_filename_pg(utc_today())
        if postgres
        else backup_filename_sqlite(utc_today())
    )
    hint = (
        "Ежедневный pg_dump — данные БД, не полный DR. "
        "Ключи escrow и site-bundle — отдельно."
        if postgres
        else (
            "Ежедневный снимок SQLite — inventory/метаданные, не полный DR. "
            "Ключи escrow и site-bundle — отдельно."
        )
    )
    return {
        "backup_dir": str(backup_dir),
        "backend": "postgres" if postgres else "sqlite",
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
        "today_exists": (backup_dir / today_name).is_file(),
        "daily_is_full_dr": False,
        "daily_hint_ru": hint,
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


def _pg_dump_env(database_url: str) -> dict[str, str]:
    env = os.environ.copy()
    parsed = urlparse(database_url)
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    return env


def _chmod_private(path: Path, mode: int = 0o600) -> None:
    try:
        path.chmod(mode)
    except OSError:
        pass


def run_pg_dump(database_url: str, dest: Path) -> None:
    """pg_dump custom format (-Fc) → dest."""
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        raise RuntimeError("pg_dump not found in PATH")
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    cmd = [
        pg_dump,
        "--format=custom",
        "--file",
        str(tmp),
        "--no-owner",
        "--no-acl",
        database_url,
    ]
    proc = subprocess.run(
        cmd,
        env=_pg_dump_env(database_url),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError(proc.stderr.strip() or f"pg_dump exit {proc.returncode}")
    tmp.replace(dest)
    _chmod_private(dest)


def run_daily_backup(
    backup_dir: Path,
    *,
    db_path: Optional[Path] = None,
    database_url: Optional[str] = None,
) -> dict[str, Any]:
    """Снимок сегодня + prune старых. Postgres → pg_dump; иначе SQLite Online Backup."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    _chmod_private(backup_dir, 0o700)

    today = utc_today()
    url = (database_url or "").strip()
    if url:
        dest = backup_dir / backup_filename_pg(today)
        try:
            run_pg_dump(url, dest)
        except Exception as exc:  # noqa: BLE001
            logger.exception("pg_dump backup failed")
            return {"ok": False, "error": str(exc), "path": str(dest), "backend": "postgres"}
        removed = _prune_old(backup_dir, today, postgres=True)
        logger.info("pg_dump backup written to %s", dest)
        return _ok_backup(dest, removed, backend="postgres", database_url=url)

    dest = backup_dir / backup_filename_sqlite(today)
    src = Path(db_path) if db_path else None
    if not src or not src.is_file():
        return {
            "ok": False,
            "error": f"DB missing: {src}",
            "path": str(dest),
            "backend": "sqlite",
        }

    try:
        src_conn = sqlite3.connect(str(src))
        try:
            tmp = dest.with_suffix(".db.tmp")
            if tmp.exists():
                tmp.unlink()
            dst_conn = sqlite3.connect(str(tmp))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
            tmp.replace(dest)
            _chmod_private(dest)
        finally:
            src_conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("SQLite backup failed")
        return {"ok": False, "error": str(exc), "path": str(dest), "backend": "sqlite"}

    removed = _prune_old(backup_dir, today, postgres=False)
    logger.info("SQLite backup written to %s", dest)
    return _ok_backup(dest, removed, backend="sqlite")


def _ok_backup(
    dest: Path,
    removed: list[str],
    *,
    backend: str,
    database_url: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "path": str(dest),
        "name": dest.name,
        "removed": removed,
        "backend": backend,
        "status": backup_status(
            dest.parent, database_url=database_url if backend == "postgres" else None
        ),
    }


def _prune_old(backup_dir: Path, today: date, *, postgres: bool) -> list[str]:
    cutoff = today - timedelta(days=KEEP_DAILY - 1)
    removed: list[str] = []
    for f in list_backup_files(backup_dir, postgres=postgres):
        try:
            stem = f.stem.replace("bad-", "", 1)
            day = date.fromisoformat(stem)
        except ValueError:
            continue
        if day < cutoff:
            try:
                f.unlink()
                removed.append(f.name)
            except OSError:
                logger.warning("Failed to remove old backup %s", f)
    return removed
