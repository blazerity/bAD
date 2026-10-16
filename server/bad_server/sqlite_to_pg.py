"""One-shot import SQLite → Postgres (downtime window; flip BAD_DATABASE_URL after)."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Порядок с учётом FK.
TABLES: tuple[str, ...] = (
    "site_secrets",
    "local_users",
    "ldap_settings",
    "retention_settings",
    "smtp_settings",
    "agent_update",
    "agent_msi_versions",
    "devices",
    "inventory_snapshots",
    "agent_policies",
    "device_config_overrides",
    "device_events",
)


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def _pg_count(url: str, table: str) -> int:
    from .db_backend import connect_postgres

    with connect_postgres(url) as conn:
        row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
        return int(row["c"] if row else 0)


def import_sqlite_to_postgres(
    *,
    sqlite_path: Path,
    database_url: str,
    truncate: bool = True,
) -> dict[str, Any]:
    """Копировать все таблицы. Перед import инициализирует PG schema."""
    from .db import Database

    if not sqlite_path.is_file():
        raise FileNotFoundError(sqlite_path)

    # Schema + singletons on target
    Database(database_url=database_url)

    src = sqlite3.connect(str(sqlite_path))
    src.row_factory = sqlite3.Row
    counts: dict[str, dict[str, int]] = {}

    try:
        from .db_backend import connect_postgres

        with connect_postgres(database_url) as dst:
            if truncate:
                # Обратный порядок для FK
                for table in reversed(TABLES):
                    dst.execute(f"TRUNCATE TABLE {table} CASCADE")

            for table in TABLES:
                cols = _table_columns(src, table)
                if not cols:
                    counts[table] = {"src": 0, "dst": 0}
                    continue
                rows = src.execute(f"SELECT * FROM {table}").fetchall()
                src_n = len(rows)
                if src_n:
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_list = ", ".join(cols)
                    sql = (
                        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                        f"ON CONFLICT DO NOTHING"
                    )
                    for row in rows:
                        dst.execute(sql, tuple(row[c] for c in cols))
                dst.commit()
                dst_n = _pg_count(database_url, table)
                counts[table] = {"src": src_n, "dst": dst_n}
                logger.info("%s: sqlite=%s pg=%s", table, src_n, dst_n)
    finally:
        src.close()

    mismatches = {
        t: c for t, c in counts.items() if c["src"] != c["dst"]
    }
    return {
        "ok": not mismatches,
        "counts": counts,
        "mismatches": mismatches,
        "hint_ru": (
            "После успешного import: пропишите BAD_DATABASE_URL в site.env, "
            "уберите runtime-зависимость от BAD_DB_PATH, restart bad-api."
            if not mismatches
            else "Counts не совпали — не flip URL, разберите mismatches."
        ),
    }


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Import bAD SQLite → Postgres")
    p.add_argument("--sqlite", required=True, type=Path, help="Path to bad.db")
    p.add_argument(
        "--database-url",
        required=True,
        help="postgresql://… (credentials not logged)",
    )
    p.add_argument(
        "--no-truncate",
        action="store_true",
        help="Do not TRUNCATE target tables first",
    )
    args = p.parse_args(argv)
    try:
        result = import_sqlite_to_postgres(
            sqlite_path=args.sqlite,
            database_url=args.database_url,
            truncate=not args.no_truncate,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Import failed: %s", exc)
        return 1
    print(result["hint_ru"])
    if not result["ok"]:
        print("MISMATCHES:", result["mismatches"], file=sys.stderr)
        return 2
    print("OK", {t: c["dst"] for t, c in result["counts"].items()})
    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
