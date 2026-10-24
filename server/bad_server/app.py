from __future__ import annotations

import asyncio
import logging
import random
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent_update import sync_from_github
from .api import router as api_router
from .auth import ensure_bootstrap_secrets, seed_default_admin
from .backup import run_daily_backup
from .config import get_settings, resolve_agent_updates_dir
from .crypto_util import decrypt_secret
from .db import Database, open_database, utc_now
from .device_health import effective_stale_after_seconds
from .rate_limit import SlidingWindowRateLimiter
from .security import hash_secret
from .smtp_mail import flush_inventory_mail_digest, notify_stale_device
from .web import router as web_router

logger = logging.getLogger(__name__)

_BG_JITTER_RATIO = 0.12


async def _sleep_interval(seconds: float) -> None:
    base = max(1.0, float(seconds))
    spread = base * _BG_JITTER_RATIO
    await asyncio.sleep(base + random.uniform(-spread, spread))


async def _run_bg_cycle(name: str, fn, *args, **kwargs):
    started = time.perf_counter()
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    finally:
        logger.info("Фоновый цикл %s: %.2f с", name, time.perf_counter() - started)


async def _agent_update_sync_loop(app: FastAPI) -> None:
    settings = get_settings()
    interval = max(0, int(settings.agent_update_sync_interval_seconds))
    if interval <= 0:
        return
    db: Database = app.state.db
    await _sleep_interval(min(interval, 90.0))
    while True:
        try:
            await _run_bg_cycle("msi_sync", sync_from_github, db, settings)
        except Exception:  # noqa: BLE001
            logger.exception("Background agent-update sync failed")
        try:
            await _sleep_interval(interval)
        except asyncio.CancelledError:
            raise


async def _retention_prune_loop(app: FastAPI) -> None:
    """Периодически удалять просроченные events / старые inventory-снимки."""
    interval = 3600
    db: Database = app.state.db
    await _sleep_interval(45.0)
    while True:
        try:
            cfg = db.get_retention_settings()
            stats = await _run_bg_cycle(
                "retention_prune",
                db.prune_expired_data,
                events_days=cfg["events_days"],
                inventory_days=cfg["inventory_days"],
            )
            if stats["events_deleted"] or stats["snapshots_deleted"]:
                logger.info(
                    "Retention prune: events=%s snapshots=%s",
                    stats["events_deleted"],
                    stats["snapshots_deleted"],
                )
        except Exception:  # noqa: BLE001
            logger.exception("Background retention prune failed")
        try:
            await _sleep_interval(interval)
        except asyncio.CancelledError:
            raise


async def _backup_loop(app: FastAPI) -> None:
    settings = get_settings()
    interval = max(60, int(settings.backup_interval_seconds or 3600))
    db: Database = app.state.db
    while True:
        try:
            result = await asyncio.to_thread(
                run_daily_backup,
                settings.backup_dir,
                database_url=settings.database_url,
            )
            if result.get("ok"):
                db.set_site_secret("last_backup_at", utc_now())
                db.set_site_secret("last_backup_path", result.get("path") or "")
            else:
                logger.warning("Daily backup skipped/failed: %s", result.get("error"))
        except Exception:  # noqa: BLE001
            logger.exception("Background pg_dump backup failed")
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise


def _smtp_password(app: FastAPI, smtp_row: dict) -> str:
    enc = smtp_row.get("password_enc") or ""
    data_key = getattr(app.state, "data_key", None)
    if enc and data_key:
        return decrypt_secret(data_key, enc) or ""
    return ""


async def _inventory_mail_digest_loop(app: FastAPI) -> None:
    """Периодическая сводка всех mail-уведомлений (inventory / enroll / stale)."""
    interval = 300  # 5 минут — проверка интервала digest внутри flush
    db: Database = app.state.db
    await _sleep_interval(20.0)
    while True:
        try:
            smtp_row = db.get_smtp_settings()
            if smtp_row.get("enabled"):
                await _run_bg_cycle(
                    "mail_digest",
                    flush_inventory_mail_digest,
                    db,
                    smtp_row,
                    _smtp_password(app, smtp_row),
                )
        except Exception:  # noqa: BLE001
            logger.exception("Background mail digest failed")
        try:
            await _sleep_interval(interval)
        except asyncio.CancelledError:
            raise


async def _stale_alert_loop(app: FastAPI) -> None:
    settings = get_settings()
    interval = 300  # 5 минут
    db: Database = app.state.db
    await _sleep_interval(25.0)
    while True:
        try:
            smtp_row = db.get_smtp_settings()
            if smtp_row.get("enabled"):
                stale_sec = effective_stale_after_seconds(db, settings)

                def _stale_pass() -> int:
                    needing = db.devices_needing_stale_alert(
                        stale_after_seconds=stale_sec
                    )
                    for device in needing:
                        notify_stale_device(
                            db,
                            smtp_row,
                            device_id=device["device_id"],
                            hostname=device.get("hostname"),
                            last_seen_at=device.get("last_seen_at"),
                        )
                        db.patch_device_meta(
                            device["device_id"], {"stale_notified_at": utc_now()}
                        )
                    return len(needing)

                n = await _run_bg_cycle("stale_alert", _stale_pass)
                if n:
                    logger.info("Stale alert: уведомлений=%s", n)
        except Exception:  # noqa: BLE001
            logger.exception("Background stale alert failed")
        try:
            await _sleep_interval(interval)
        except asyncio.CancelledError:
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = open_database(database_url=settings.database_url)
    settings.agent_updates_dir = resolve_agent_updates_dir(settings)
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.warning("Cannot create backup dir %s", settings.backup_dir)

    # Сохранить hashed site secrets, если plaintext-токены заданы через env
    if settings.enrollment_token and not db.get_site_secret("enrollment_token_hash"):
        db.set_site_secret("enrollment_token_hash", hash_secret(settings.enrollment_token))
    if settings.admin_token and not db.get_site_secret("admin_token_hash"):
        db.set_site_secret("admin_token_hash", hash_secret(settings.admin_token))

    session_secret, data_key = ensure_bootstrap_secrets(db, settings)
    seed_default_admin(db, settings)

    app.state.db = db
    app.state.session_secret = session_secret
    app.state.data_key = data_key
    app.state.enroll_limiter = SlidingWindowRateLimiter(
        max_calls=settings.enroll_rate_limit_per_minute,
        window_seconds=60.0,
    )
    app.state.login_ip_limiter = SlidingWindowRateLimiter(
        max_calls=settings.login_rate_limit_per_minute,
        window_seconds=60.0,
    )
    app.state.login_user_limiter = SlidingWindowRateLimiter(
        max_calls=settings.login_username_rate_limit_per_minute,
        window_seconds=60.0,
    )

    tasks: list[asyncio.Task] = []
    # Фоновый/startup sync — best-effort; в тестах отключается через env.
    if (
        settings.agent_update_sync_on_startup
        and settings.github_repo
        and settings.agent_update_sync_interval_seconds >= 0
    ):
        try:
            await asyncio.to_thread(sync_from_github, db, settings)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Startup agent-update sync skipped/failed (repo=%s)",
                settings.github_repo,
                exc_info=True,
            )

    if settings.agent_update_sync_interval_seconds > 0 and settings.github_repo:
        tasks.append(asyncio.create_task(_agent_update_sync_loop(app)))

    tasks.append(asyncio.create_task(_retention_prune_loop(app)))
    tasks.append(asyncio.create_task(_backup_loop(app)))
    tasks.append(asyncio.create_task(_stale_alert_loop(app)))
    tasks.append(asyncio.create_task(_inventory_mail_digest_loop(app)))

    yield

    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="bAD — blazerity Asset Discovery",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(api_router)
    app.include_router(web_router)
    return app


app = create_app()
