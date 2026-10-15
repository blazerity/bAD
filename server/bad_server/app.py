from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .agent_update import sync_from_github
from .api import router as api_router
from .auth import ensure_bootstrap_secrets, seed_default_admin
from .config import get_settings
from .db import Database
from .rate_limit import SlidingWindowRateLimiter
from .security import hash_secret
from .web import router as web_router

logger = logging.getLogger(__name__)


async def _agent_update_sync_loop(app: FastAPI) -> None:
    settings = get_settings()
    interval = max(0, int(settings.agent_update_sync_interval_seconds))
    if interval <= 0:
        return
    db: Database = app.state.db
    while True:
        try:
            await asyncio.to_thread(sync_from_github, db, settings)
        except Exception:  # noqa: BLE001
            logger.exception("Background agent-update sync failed")
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings.db_path)
    settings.agent_updates_dir.mkdir(parents=True, exist_ok=True)

    # Persist hashed site secrets when plaintext tokens provided via env
    if settings.enrollment_token and not db.get_site_secret("enrollment_token_hash"):
        db.set_site_secret("enrollment_token_hash", hash_secret(settings.enrollment_token))
    if settings.admin_token and not db.get_site_secret("admin_token_hash"):
        db.set_site_secret("admin_token_hash", hash_secret(settings.admin_token))

    session_secret, data_key = ensure_bootstrap_secrets(db, settings)
    seed_default_admin(db, settings)

    # Restrict DB file permissions when possible (bind password lives encrypted inside).
    try:
        settings.db_path.chmod(0o600)
    except OSError:
        pass

    app.state.db = db
    app.state.session_secret = session_secret
    app.state.data_key = data_key
    app.state.enroll_limiter = SlidingWindowRateLimiter(
        max_calls=settings.enroll_rate_limit_per_minute,
        window_seconds=60.0,
    )

    sync_task: asyncio.Task | None = None
    # Background/startup sync is best-effort; disable in tests via env.
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
        sync_task = asyncio.create_task(_agent_update_sync_loop(app))

    yield

    if sync_task is not None:
        sync_task.cancel()
        try:
            await sync_task
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
