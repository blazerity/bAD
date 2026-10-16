"""Ротация site enrollment token (UI / ops) без обязательного restart."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from .config import Settings
from .db import Database, utc_now
from .security import generate_token, hash_secret

logger = logging.getLogger(__name__)

ENROLLMENT_ROTATE_HINT_RU = (
    "После волны MSI смените enrollment token (SEC-011): уже записанные агенты "
    "продолжат работу по API key; новый token нужен только для следующих установок."
)

_ENROLL_LINE_RE = re.compile(
    r"^(BAD_ENROLLMENT_TOKEN=)(.*)$", re.MULTILINE
)


def enrollment_token_file(settings: Settings) -> Path:
    return Path(
        getattr(settings, "enrollment_token_file", None)
        or Path("/etc/bad/enrollment_token")
    )


def site_env_path() -> Path:
    return Path("/etc/bad/site.env")


def _write_private_file(path: Path, value: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value.rstrip("\n") + "\n", encoding="utf-8")
        try:
            path.chmod(0o440)
        except OSError:
            try:
                path.chmod(0o400)
            except OSError:
                pass
        return True
    except OSError as exc:
        logger.warning("Cannot write %s: %s", path, exc)
        return False


def _update_site_env_enrollment(token: str) -> bool:
    path = site_env_path()
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Cannot read site.env: %s", exc)
        return False
    replacement = f"BAD_ENROLLMENT_TOKEN={token}"
    if _ENROLL_LINE_RE.search(text):
        new_text = _ENROLL_LINE_RE.sub(replacement, text, count=1)
    else:
        new_text = text.rstrip() + "\n" + replacement + "\n"
    try:
        path.write_text(new_text, encoding="utf-8")
        return True
    except OSError as exc:
        logger.warning("Cannot update site.env enrollment token: %s", exc)
        return False


def rotate_enrollment_token(
    db: Database,
    settings: Settings,
    *,
    new_token: Optional[str] = None,
) -> dict:
    """Сгенерировать/задать enrollment token, инвалидировать старый hash.

    Возвращает plaintext один раз (+ куда записали). Restart не нужен:
    ``require_enrollment_token`` читает hash из SQLite.
    """
    token = (new_token or "").strip() or generate_token("bad_en_")
    db.set_site_secret("enrollment_token_hash", hash_secret(token))
    db.set_site_secret("enrollment_token_rotated_at", utc_now())

    wrote_file = _write_private_file(enrollment_token_file(settings), token)
    # Dev fallback рядом с БД.
    wrote_fallback = False
    if not wrote_file:
        fallback = settings.db_path.parent / ".enrollment_token"
        wrote_fallback = _write_private_file(fallback, token)

    updated_env = _update_site_env_enrollment(token)
    return {
        "token": token,
        "rotated_at": db.get_site_secret("enrollment_token_rotated_at"),
        "wrote_token_file": wrote_file,
        "wrote_fallback_file": wrote_fallback,
        "updated_site_env": updated_env,
        "token_file": str(enrollment_token_file(settings)),
    }


def enrollment_status(db: Database, settings: Settings) -> dict:
    has_hash = bool(db.get_site_secret("enrollment_token_hash"))
    return {
        "configured": has_hash or bool(settings.enrollment_token),
        "has_hash": has_hash,
        "rotated_at": db.get_site_secret("enrollment_token_rotated_at"),
        "token_file": str(enrollment_token_file(settings)),
        "token_file_exists": enrollment_token_file(settings).is_file(),
        "env_bootstrap": bool(settings.enrollment_token),
        "last_enrollment_at": db.get_site_secret("last_enrollment_at"),
    }


def mark_device_enrolled(db: Database) -> None:
    """Stamp last successful new enroll (wave signal for rotation runbook)."""
    db.set_site_secret("last_enrollment_at", utc_now())


def enrollment_rotation_signals(
    db: Database,
    settings: Settings,
) -> dict[str, Any]:
    """UI/admin hook: remind to rotate enrollment after an MSI wave (SEC-011).

    ``rotation_due`` when active devices enrolled at/after last rotation
    (or all actives if never rotated) reach ``enrollment_rotate_after_enrolls``.
    """
    status = enrollment_status(db, settings)
    rotated_at = status.get("rotated_at") or None
    threshold = max(1, int(settings.enrollment_rotate_after_enrolls or 1))
    enrolled_since = db.count_enrolled_since(rotated_at)
    due = enrolled_since >= threshold
    return {
        **status,
        "enrolled_since_rotation": enrolled_since,
        "rotation_due": due,
        "threshold": threshold,
        "hint_ru": ENROLLMENT_ROTATE_HINT_RU if due else None,
        "ui_path": "/settings/updates",
        "api_path": "/v1/admin/enrollment/rotate",
    }
