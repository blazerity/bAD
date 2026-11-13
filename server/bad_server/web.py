"""Панель: сборка роутера. Страницы живут в web_*.py."""

from fastapi import APIRouter

from . import __version__
from .device_meta import (
    format_logged_on_display,
    normalize_logged_on_list,
    normalize_logged_on_user,
)
from .event_importance import FILTER_PRESET_LABELS_RU, event_importance
from .web_common import (
    _format_bytes,
    _format_chassis,
    _format_config_interval,
    _format_os,
    _pager_items,
    _pager_url,
)
from .web_devices import (
    _disk_role_label_ru,
    render_device_report,
    router as devices_router,
)
from .web_events import (
    _EVENT_TYPE_LABELS_RU,
    _day_heading_ru,
    _event_summary_anchor_hostname,
    _format_event_type,
    _importance_label_ru,
    router as events_router,
)
from .web_http import router as http_router, templates
from .web_overview import router as overview_router
from .web_search import router as search_router
from .web_settings import router as settings_router

templates.env.globals["app_version"] = __version__



templates.env.filters["format_bytes"] = _format_bytes

templates.env.filters["format_os"] = _format_os

templates.env.filters["format_chassis"] = _format_chassis

templates.env.filters["format_event_type"] = _format_event_type

templates.env.filters["format_config_interval"] = _format_config_interval

templates.env.filters["event_summary_anchor_hostname"] = _event_summary_anchor_hostname



templates.env.globals["day_heading_ru"] = _day_heading_ru



templates.env.filters["importance_label_ru"] = _importance_label_ru

templates.env.filters["format_logged_on"] = format_logged_on_display

templates.env.filters["logged_on_names"] = normalize_logged_on_list

templates.env.filters["logged_on_user"] = normalize_logged_on_user



templates.env.filters["disk_role_label"] = _disk_role_label_ru



templates.env.filters["pager_items"] = _pager_items

templates.env.filters["pager_url"] = _pager_url

templates.env.globals["event_importance"] = event_importance

templates.env.globals["importance_filter_labels"] = FILTER_PRESET_LABELS_RU

templates.env.globals["event_type_filter_labels"] = _EVENT_TYPE_LABELS_RU

router = APIRouter()
router.include_router(http_router)
router.include_router(overview_router)
router.include_router(search_router)
router.include_router(devices_router)
router.include_router(events_router)
router.include_router(settings_router)
