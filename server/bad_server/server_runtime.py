"""Метрики процесса панели (uptime, ping БД, RSS) для SSR Обзора."""

from __future__ import annotations

import sys
import time
from typing import Any, Optional

_PROCESS_STARTED_AT = time.time()
_db_probe_cache: Optional[tuple[float, bool, Optional[float]]] = None
_DB_PROBE_TTL = 15.0


def reset_process_start() -> None:
    global _PROCESS_STARTED_AT
    _PROCESS_STARTED_AT = time.time()


def _probe_database(db: Any) -> tuple[bool, Optional[float]]:
    global _db_probe_cache
    now = time.time()
    if _db_probe_cache is not None:
        cached_at, ok, latency = _db_probe_cache
        if now - cached_at < _DB_PROBE_TTL:
            return ok, latency
    ok = False
    latency_ms: Optional[float] = None
    t0 = time.perf_counter()
    try:
        with db.connection() as conn:
            conn.execute("SELECT 1")
        ok = True
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    except Exception:
        ok = False
        latency_ms = None
    _db_probe_cache = (now, ok, latency_ms)
    return ok, latency_ms


def _process_memory_bytes() -> Optional[int]:
    if not sys.platform.startswith("linux"):
        return None
    try:
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux: kilobytes; macOS would be bytes — панель в проде на Linux.
        if sys.platform == "darwin":
            return int(rss)
        return int(rss) * 1024
    except Exception:
        return None


def build_server_runtime(db: Any) -> dict[str, Any]:
    uptime_seconds = max(0, int(time.time() - _PROCESS_STARTED_AT))
    db_ok, db_latency_ms = _probe_database(db)
    mem = _process_memory_bytes()
    return {
        "uptime_seconds": uptime_seconds,
        "db_ok": db_ok,
        "db_latency_ms": db_latency_ms if db_ok else None,
        "process_memory_bytes": mem,
        "cpu_percent": None,
    }
