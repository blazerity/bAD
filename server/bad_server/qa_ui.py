"""Режим QA-панели (BAD_QA_UI=1): скриншоты без HTTP-bootstrap трения."""

from __future__ import annotations

from typing import Any

from .config import Settings


def qa_ui_active(settings: Settings) -> bool:
    return bool(settings.qa_ui)


def panel_tls_mode(settings: Settings, actual: str) -> str:
    """TLS-режим для шаблонов: в QA показываем chrome как при HTTPS."""
    if qa_ui_active(settings):
        return "https"
    return (actual or "http").lower()


def patch_security_for_qa(security: dict[str, Any], settings: Settings) -> dict[str, Any]:
    if not qa_ui_active(settings):
        return security
    out = dict(security)
    hf = dict(security.get("https_first") or {})
    hf["tls_mode"] = "https"
    hf["sensitive_over_http_blocked"] = False
    hf["hint_ru"] = (
        "Режим QA (BAD_QA_UI=1): баннеры и гейты bootstrap отключены — только lab."
    )
    out["https_first"] = hf
    return out
