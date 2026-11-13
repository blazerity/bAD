"""Сервер blazerity Asset Discovery."""

from __future__ import annotations

from pathlib import Path


def _read_server_version() -> str:
    """Корневой VERSION = semver сервера (не agent/VERSION)."""
    here = Path(__file__).resolve()
    for candidate in (
        Path("/opt/bad/VERSION"),
        here.parents[2] / "VERSION",
    ):
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8").strip()
                if text:
                    return text.splitlines()[0].strip()
            except OSError:
                continue
    return "0.4.0-beta"


__version__ = _read_server_version()


def panel_root() -> Path:
    """Панель лежит рядом с каталогом server: в репозитории и в /opt/bad."""
    root = Path(__file__).resolve().parents[2] / "panel"
    templates = root / "templates"
    if not templates.is_dir():
        raise FileNotFoundError(f"panel templates not found: {templates}")
    return root
