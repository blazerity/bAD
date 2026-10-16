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
    return "1.1.1"


__version__ = _read_server_version()
