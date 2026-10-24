"""Postgres DDL без долгих блокировок на старте (CONCURRENTLY, lock_timeout)."""

from __future__ import annotations

import logging

from .db_backend import CompatConnection, connect_postgres

logger = logging.getLogger(__name__)

LOCK_TIMEOUT = "5s"


def connect_autocommit(database_url: str) -> CompatConnection:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Postgres requires psycopg: pip install 'psycopg[binary]'"
        ) from exc
    raw = psycopg.connect(database_url, row_factory=dict_row, autocommit=True)
    return CompatConnection(raw)


def index_exists(conn: CompatConnection, index_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname = ?",
        (index_name,),
    ).fetchone()
    return bool(row)


def set_lock_timeout(conn: CompatConnection, timeout: str = LOCK_TIMEOUT) -> None:
    conn.execute(f"SET lock_timeout = '{timeout}'")


def create_index_concurrently(
    database_url: str,
    index_name: str,
    ddl: str,
    *,
    lock_timeout: str = LOCK_TIMEOUT,
) -> bool:
    """CREATE INDEX CONCURRENTLY вне транзакции; False если пропущено из‑за lock/ошибки."""
    with connect_autocommit(database_url) as conn:
        if index_exists(conn, index_name):
            return True
        try:
            set_lock_timeout(conn, lock_timeout)
            conn.execute(ddl)
            return True
        except Exception as exc:
            logger.warning(
                "Index %s not created on this start (retry later): %s",
                index_name,
                exc,
            )
            return False


def ensure_trgm_search_indexes(database_url: str) -> None:
    with connect_postgres(database_url) as conn:
        try:
            set_lock_timeout(conn)
            conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            conn.commit()
        except Exception as exc:
            logger.warning("pg_trgm extension skipped: %s", exc)
            conn.rollback()

    create_index_concurrently(
        database_url,
        "idx_devices_meta_trgm",
        "CREATE INDEX CONCURRENTLY idx_devices_meta_trgm "
        "ON devices USING gin (meta_json gin_trgm_ops)",
    )
    create_index_concurrently(
        database_url,
        "idx_devices_hostname_trgm",
        "CREATE INDEX CONCURRENTLY idx_devices_hostname_trgm "
        "ON devices USING gin (hostname gin_trgm_ops)",
    )


def ensure_devices_bad_id_index(database_url: str) -> None:
    create_index_concurrently(
        database_url,
        "idx_devices_bad_id",
        "CREATE UNIQUE INDEX CONCURRENTLY idx_devices_bad_id ON devices(bad_id)",
    )
