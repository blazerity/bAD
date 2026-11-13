from __future__ import annotations

import csv
import html
import io
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

from markupsafe import Markup
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from . import __version__, panel_root
from .agent_config import (
    ALLOWED_SETTING_KEYS,
    CONDITION_FIELDS,
    CONDITION_OPS,
    DEFAULT_AGENT_SETTINGS,
    UPDATE_TARGET_LATEST,
    sanitize_conditions,
    sanitize_settings,
    sanitize_update_target,
)
from .auth import (
    authenticate_web_user,
    current_web_user,
    get_data_key,
    get_db,
    get_session_secret,
    load_ldap_view,
    require_web_admin,
    require_web_user,
)
from .config import Settings, get_settings
from .crypto_util import decrypt_secret, encrypt_secret
from .csrf import cookie_secure_for_request, ensure_csrf, get_csrf_token, set_csrf_cookie
from .device_refresh import set_device_refresh_request
from .db import Database
from .device_health import (
    DEVICE_RECENT_SITE_SECRET_KEY,
    DEVICE_STALE_SITE_SECRET_KEY,
    badge_recent_after_seconds,
    device_silence_status,
    effective_recent_after_seconds,
    effective_stale_after_seconds,
    health_snippet,
    parse_iso,
    parse_utc,
    retention_threshold_seconds,
    stale_days_form,
)
from .ldap_client import settings_from_row, test_connection
from .security import (
    api_key_lookup,
    generate_token,
    hash_secret,
    new_device_signing_key,
    verify_secret,
)
from .sessions import (
    FLASH_COOKIE,
    FLASH_MAX_AGE,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    WebUser,
    dump_flash,
    dump_session,
    load_flash,
)
from .agent_update import (
    delete_msi_version,
    ingest_uploaded_msi,
    ops_update_signals,
    set_latest_msi_version,
    sync_from_github,
)
from .backup import backup_keys_status, backup_status, run_daily_backup
from .http_bootstrap import HTTP_SENSITIVE_MSG, client_ip, sensitive_over_http_blocked
from .device_meta import (
    format_logged_on_display,
    inventory_meta_cache,
    meta_search_haystack,
    normalize_logged_on_list,
    normalize_logged_on_user,
)
from .server_runtime import build_server_runtime
from .panel_search import (
    device_match_label,
    device_match_parts,
    event_match_label,
    highlight_match,
    matched_serial_subtitle,
)
from .fleet_buckets import (
    disk_bucket_bytes,
    disk_role,
    format_cpu_short,
    format_ram_list_cell,
    meta_facet_matches,
    normalize_os_caption,
)
from .device_uninstall import (
    cancel_device_uninstall,
    device_uninstall_confirm_value,
    request_device_uninstall,
    uninstall_confirm_matches,
    uninstall_ui_context,
)
from .ops_panel import (
    aggregate_incident_feed,
    build_attention_queue,
    build_bootstrap_checklist,
    build_bootstrap_progress,
    build_config_winner,
    build_dashboard_stats,
    build_wave_counts,
    device_has_agent_local,
    enrich_overview_ops_signals,
    filter_devices_by_wave,
    normalize_wave_filter,
)
from .security_ops import merge_security_into_ops, security_status
from .site_bundle import build_key_escrow_archive, build_site_bundle
from .tls_ops import (
    https_panel_url,
    read_domain_from_env,
    save_tls_materials,
    tls_panel_mode,
    tls_status,
    wait_for_apply,
)
from .server_update import (
    check_updates as server_check_updates,
    list_remote_branches,
    poll_msi_workflow,
    read_current as server_read_current,
    releases_dir,
    request_apply as server_request_apply,
    request_set_github_token,
    set_preferred_branch,
    status_panel as server_status_panel,
    trigger_msi_workflow,
    outcome_for_apply_request as server_outcome_for_apply_request,
)
from .event_importance import (
    FILTER_PRESET_LABELS_RU,
    IMPORTANCE_LABELS_RU,
    _EVENT_IMPORTANCE,
    event_importance,
)
from .smtp_mail import (
    DEFAULT_NOTIFY,
    build_hardware_email,
    default_digest_weekdays,
    digest_schedule_preview_ru,
    dump_notify_flags,
    parse_digest_weekdays,
    parse_notify_flags,
    parse_recipients,
    send_email,
)
from .web_http import (
    _clear_session_cookie,
    _flash_check,
    _html,
    _see_other,
    _set_session_cookie,
    _take_flash,
    templates,
)

from .web_common import (
    _chassis_map_for_devices,
    _chassis_type_from_device,
    _device_freshness_tier,
    _fleet_snapshot,
    _format_chassis,
    _freshness_limits,
    _invalidate_fleet_snapshot_cache,
)

router = APIRouter(tags=["web"], dependencies=[Depends(ensure_csrf)])



# Подписи галок почты. Лента остаётся на _EVENT_TYPE_LABELS_RU.
_NOTIFY_CHECK_LABELS_RU = {
    "disk_removed": "Диск отключён",
    "cpu_change": "Сменился процессор",
    "ram_module_removed": "Планка памяти снята",
    "volume_free_critical": "На системном диске критически мало места",
    "minidump_bugcheck": "Синий экран с кодом bugcheck",
    "serial_change": "Сменился серийный номер компьютера",
    "model_change": "Сменилась модель компьютера",
    "manufacturer_change": "Сменился производитель компьютера",
    "smbios_uuid_change": "Сменился SMBIOS UUID",
    "baseboard_serial_change": "Сменился серийный номер платы",
    "bios_serial_change": "Сменился серийный номер BIOS",
    "hostname_change": "Сменилось имя компьютера",
    "domain_change": "Сменился домен",
    "ad_ou_change": "Компьютер переехал в другой OU",
    "device_stale": "Компьютер перестал выходить на связь",
    "device_back_online": "Компьютер снова на связи",
    "device_enrolled": "Зарегистрирован новый компьютер",
    "device_merged": "Карточки компьютера объединены",
    "disk_added": "Подключён диск",
    "ram_module_added": "Поставлена планка памяти",
    "volume_free_drop": "Заметно уменьшилось свободное место",
    "antivirus_change": "Сменился набор антивирусов",
    "tpm_change": "Сменился TPM",
    "secure_boot_change": "Сменился Secure Boot",
    "gpu_added": "Появилась видеокарта",
    "gpu_removed": "Пропала видеокарта",
    "ram_bytes_change": "Сменился объём оперативной памяти",
    "nic_ipv4_change": "Сменился IPv4-адрес",
    "nic_mac_change": "Сетевой интерфейс появился или исчез",
    "pending_reboot_change": "Компьютер стал ждать перезагрузку или перестал",
    "last_boot_change": "Компьютер перезагрузился",
    "chassis_type_change": "Сменился тип корпуса",
    "agent_version_change": "Сменилась версия агента",
    "os_build_change": "Сменилась сборка Windows",
    "bios_update": "Обновился BIOS",
    "monitor_set_change": "Сменился набор мониторов",
    "timezone_change": "Сменился часовой пояс",
    "logged_on_change": "Сменился список вошедших пользователей",
    "last_interactive_change": "Сменился последний интерактивный пользователь",
    "usb_added": "Подключена флешка или USB-диск",
    "usb_removed": "Отключена флешка или USB-диск",
}



class LdapFormData:
    """Общие Form-поля для POST save/test LDAP."""

    def __init__(
        self,
        enabled: Optional[str] = Form(None),
        host: str = Form(""),
        port: str = Form("389"),
        use_ssl: Optional[str] = Form(None),
        start_tls: Optional[str] = Form(None),
        bind_dn: str = Form(""),
        bind_password: str = Form(""),
        user_search_base: str = Form(""),
        user_filter_template: str = Form("(uid={username})"),
        display_name_attr: str = Form("cn"),
        default_role: str = Form("operator"),
        allowed_group: str = Form(""),
        tls_insecure: Optional[str] = Form(None),
    ):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.start_tls = start_tls
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_search_base = user_search_base
        self.user_filter_template = user_filter_template
        self.display_name_attr = display_name_attr
        self.default_role = default_role
        self.allowed_group = allowed_group
        self.tls_insecure = tls_insecure



class SmtpFormData:
    """Общие Form-поля для POST save/test почты."""

    def __init__(
        self,
        enabled: Optional[str] = Form(None),
        host: str = Form(""),
        port: str = Form("587"),
        use_ssl: Optional[str] = Form(None),
        use_starttls: Optional[str] = Form(None),
        username: str = Form(""),
        password: str = Form(""),
        from_addr: str = Form(""),
        to_addrs: str = Form(""),
        notify_hardware: Optional[str] = Form(None),
        notify_stale: Optional[str] = Form(None),
        notify_enroll: Optional[str] = Form(None),
        notify_hostname: Optional[str] = Form(None),
        notify_domain: Optional[str] = Form(None),
        notify_pending_reboot: Optional[str] = Form(None),
        notify_online: Optional[str] = Form(None),
        notify_disk_space: Optional[str] = Form(None),
        notify_type: list[str] = Form(default_factory=list),
        digest_interval_hours: str = Form("3"),
        digest_lookback_hours: str = Form("3"),
        digest_window_start_hour: str = Form("9"),
        digest_window_end_hour: str = Form("19"),
        digest_wd_0: Optional[str] = Form(None),
        digest_wd_1: Optional[str] = Form(None),
        digest_wd_2: Optional[str] = Form(None),
        digest_wd_3: Optional[str] = Form(None),
        digest_wd_4: Optional[str] = Form(None),
        digest_wd_5: Optional[str] = Form(None),
        digest_wd_6: Optional[str] = Form(None),
    ):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.use_starttls = use_starttls
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.notify_hardware = notify_hardware
        self.notify_stale = notify_stale
        self.notify_enroll = notify_enroll
        self.notify_hostname = notify_hostname
        self.notify_domain = notify_domain
        self.notify_pending_reboot = notify_pending_reboot
        self.notify_online = notify_online
        self.notify_disk_space = notify_disk_space
        self.notify_type = list(notify_type or [])
        self.digest_interval_hours = digest_interval_hours
        self.digest_lookback_hours = digest_lookback_hours
        self.digest_window_start_hour = digest_window_start_hour
        self.digest_window_end_hour = digest_window_end_hour
        self.digest_wd_0 = digest_wd_0
        self.digest_wd_1 = digest_wd_1
        self.digest_wd_2 = digest_wd_2
        self.digest_wd_3 = digest_wd_3
        self.digest_wd_4 = digest_wd_4
        self.digest_wd_5 = digest_wd_5
        self.digest_wd_6 = digest_wd_6



class PolicyFormData:
    """Общие Form-поля создания и правки политики агента."""

    def __init__(
        self,
        name: str = Form(""),
        enabled: Optional[str] = Form(None),
        priority: str = Form("100"),
        cond_field: str = Form("hostname"),
        cond_op: str = Form("contains"),
        cond_value: str = Form(""),
        inventory_interval_hours: str = Form(""),
        heartbeat_interval_minutes: str = Form(""),
        update_check_interval_hours: str = Form(""),
        update_enabled: str = Form(""),
        update_target: str = Form(""),
        collect_hardware: str = Form(""),
        collect_users: str = Form(""),
        collect_software: str = Form(""),
    ):
        self.name = name
        self.enabled = enabled
        self.priority = priority
        self.cond_field = cond_field
        self.cond_op = cond_op
        self.cond_value = cond_value
        self.inventory_interval_hours = inventory_interval_hours
        self.heartbeat_interval_minutes = heartbeat_interval_minutes
        self.update_check_interval_hours = update_check_interval_hours
        self.update_enabled = update_enabled
        self.update_target = update_target
        self.collect_hardware = collect_hardware
        self.collect_users = collect_users
        self.collect_software = collect_software



def _ldap_form_context(
    row: dict,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    test_result: Optional[str] = None,
) -> dict:
    has_bind_password = bool(row.get("bind_password_enc"))
    return {
        "user": user,
        "settings_section": "ldap",
        "message": message,
        "error": error,
        "test_result": test_result,
        "has_bind_password": has_bind_password,
        "ldap": {
            "enabled": bool(row.get("enabled")),
            "host": row.get("host") or "",
            "port": int(row.get("port") or 389),
            "use_ssl": bool(row.get("use_ssl")),
            "start_tls": bool(row.get("start_tls")),
            "bind_dn": row.get("bind_dn") or "",
            "user_search_base": row.get("user_search_base") or "",
            "user_filter_template": row.get("user_filter_template")
            or "(uid={username})",
            "display_name_attr": row.get("display_name_attr") or "cn",
            "default_role": row.get("default_role") or "operator",
            "allowed_group": row.get("allowed_group") or "",
            "tls_insecure": bool(row.get("tls_insecure")),
        },
    }



def _parse_ldap_form(form: LdapFormData) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(form.port or "389")
    except ValueError:
        return {}, "Порт должен быть целым числом"
    if port_i < 1 or port_i > 65535:
        return {}, "Порт должен быть от 1 до 65535"
    role = (form.default_role or "operator").strip().lower()
    if role not in {"admin", "operator"}:
        return {}, "Роль по умолчанию: admin или operator"
    template = (form.user_filter_template or "").strip() or "(uid={username})"
    if "{username}" not in template:
        return {}, "Шаблон фильтра должен содержать {username}"
    return {
        "enabled": form.enabled is not None,
        "host": (form.host or "").strip(),
        "port": port_i,
        "use_ssl": form.use_ssl is not None,
        "start_tls": form.start_tls is not None,
        "bind_dn": (form.bind_dn or "").strip(),
        "bind_password": form.bind_password,  # пусто = без изменений
        "user_search_base": (form.user_search_base or "").strip(),
        "user_filter_template": template,
        "display_name_attr": (form.display_name_attr or "cn").strip() or "cn",
        "default_role": role,
        "allowed_group": (form.allowed_group or "").strip(),
        "tls_insecure": form.tls_insecure is not None,
    }, None



def _apply_bool_form_fields(raw: dict, fields: dict[str, str]) -> None:
    for key, raw_val in fields.items():
        text = (raw_val or "").strip().lower()
        if text in {"true", "false", "1", "0"}:
            raw[key] = text in {"true", "1"}



def _settings_raw_from_form(
    *,
    inventory_interval_hours: str = "",
    heartbeat_interval_minutes: str = "",
    update_check_interval_hours: str = "",
    update_enabled: str = "",
    update_target: str = "",
    collect_hardware: str = "",
    collect_users: str = "",
    collect_software: str = "",
) -> dict:
    """Общий harvest interval/bool/update_target из HTML-форм (policy + device override)."""
    raw: dict = {}
    for key, raw_val in (
        ("inventory_interval_hours", inventory_interval_hours),
        ("heartbeat_interval_minutes", heartbeat_interval_minutes),
        ("update_check_interval_hours", update_check_interval_hours),
    ):
        text = (raw_val or "").strip()
        if text:
            raw[key] = text
    _apply_bool_form_fields(
        raw,
        {
            "update_enabled": update_enabled,
            "collect_hardware": collect_hardware,
            "collect_users": collect_users,
            "collect_software": collect_software,
        },
    )
    target = (update_target or "").strip()
    if target:
        raw["update_target"] = target
    return raw



def _parse_policy_form(
    *,
    name: str,
    enabled: Optional[str],
    priority: str,
    cond_field: str,
    cond_op: str,
    cond_value: str,
    inventory_interval_hours: str,
    heartbeat_interval_minutes: str,
    update_check_interval_hours: str,
    update_enabled: str,
    update_target: str = "",
    collect_hardware: str = "",
    collect_users: str = "",
    collect_software: str = "",
) -> tuple[Optional[dict], Optional[str]]:
    name_s = (name or "").strip()
    if not name_s:
        return None, "Укажите имя"
    try:
        priority_i = int((priority or "100").strip())
    except ValueError:
        return None, "Priority должен быть целым числом"
    if priority_i < 0 or priority_i > 1_000_000:
        return None, "Priority вне допустимого диапазона"

    conditions = sanitize_conditions(
        [
            {
                "field": (cond_field or "").strip(),
                "op": (cond_op or "").strip(),
                "value": (cond_value or "").strip(),
            }
        ]
    )
    if not conditions:
        return None, "Нужно одно валидное условие (hostname/domain/os_caption/tag)"

    raw = _settings_raw_from_form(
        inventory_interval_hours=inventory_interval_hours,
        heartbeat_interval_minutes=heartbeat_interval_minutes,
        update_check_interval_hours=update_check_interval_hours,
        update_enabled=update_enabled,
        update_target=update_target,
        collect_hardware=collect_hardware,
        collect_users=collect_users,
        collect_software=collect_software,
    )
    settings = sanitize_settings(raw)
    if not settings:
        return None, "Задайте хотя бы одно поле settings для политики"
    return {
        "name": name_s,
        "enabled": enabled is not None,
        "priority": priority_i,
        "conditions": conditions,
        "settings": settings,
    }, None



def _accept_policy(
    db: Database, form: PolicyFormData
) -> tuple[Optional[dict], Optional[str]]:
    parsed, err = _parse_policy_form(
        name=form.name,
        enabled=form.enabled,
        priority=form.priority,
        cond_field=form.cond_field,
        cond_op=form.cond_op,
        cond_value=form.cond_value,
        inventory_interval_hours=form.inventory_interval_hours,
        heartbeat_interval_minutes=form.heartbeat_interval_minutes,
        update_check_interval_hours=form.update_check_interval_hours,
        update_enabled=form.update_enabled,
        update_target=form.update_target,
        collect_hardware=form.collect_hardware,
        collect_users=form.collect_users,
        collect_software=form.collect_software,
    )
    if err or not parsed:
        return None, err
    pin_err = _validate_update_target_pin(db, parsed["settings"])
    if pin_err:
        return None, pin_err
    return parsed, None



def _validate_update_target_pin(db: Database, settings: dict) -> Optional[str]:
    """Reject pin на версию, которой нет в зеркале (контракт 0.10)."""
    target = sanitize_update_target(settings.get("update_target"))
    if not target or target == UPDATE_TARGET_LATEST:
        return None
    if not db.get_agent_msi_version(target):
        return f"Версия {target} отсутствует в каталоге установщиков — сначала загрузите её"
    return None



_CONDITION_FIELD_LABELS_RU = {
    "hostname": "Имя узла",
    "domain": "Домен",
    "os_caption": "Подпись ОС",
    "tag": "Тег",
}


_CONDITION_OP_LABELS_RU = {
    "equals": "совпадает",
    "contains": "содержит",
}



def _filter_policy_settings(settings: object) -> dict:
    """Тема C: в UI только knobs из ALLOWED_SETTING_KEYS (без server_url/секретов)."""
    if not isinstance(settings, dict):
        return {}
    return {k: v for k, v in settings.items() if k in ALLOWED_SETTING_KEYS}



def _policies_context(
    db: Database,
    user: WebUser,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    edit: Optional[dict] = None,
) -> dict:
    policies = []
    for p in db.list_agent_policies():
        row = dict(p)
        row["settings"] = _filter_policy_settings(row.get("settings"))
        policies.append(row)
    edit_view = edit
    if edit_view is not None:
        edit_view = dict(edit_view)
        edit_view["settings"] = _filter_policy_settings(edit_view.get("settings"))
    return {
        "user": user,
        "policies": policies,
        "defaults": dict(DEFAULT_AGENT_SETTINGS),
        "allowed_setting_keys": sorted(ALLOWED_SETTING_KEYS),
        "condition_fields": sorted(CONDITION_FIELDS),
        "condition_field_labels": _CONDITION_FIELD_LABELS_RU,
        "condition_op_labels": _CONDITION_OP_LABELS_RU,
        "condition_ops": sorted(CONDITION_OPS),
        "msi_versions": db.list_agent_msi_versions(),
        "message": message,
        "error": error,
        "edit": edit_view,
    }



@router.get("/settings/policies", response_class=HTMLResponse)
def policies_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return _html(request, "policies.html", _policies_context(db, user))



@router.get("/settings/policies/{policy_id}", response_class=HTMLResponse)
def policy_edit_page(
    policy_id: int,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    policy = db.get_agent_policy(policy_id)
    if not policy:
        return RedirectResponse(url="/settings/policies", status_code=303)
    return _html(
        request, "policies.html", _policies_context(db, user, edit=policy)
    )



@router.post("/settings/policies")
def policy_create(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    form: PolicyFormData = Depends(),
):
    parsed, err = _accept_policy(db, form)
    if err or not parsed:
        return _html(
            request,
            "policies.html",
            _policies_context(db, user, error=err),
            status_code=400,
        )
    db.create_agent_policy(**parsed)
    return _html(
        request,
        "policies.html",
        _policies_context(db, user, message="Политика создана"),
    )



@router.post("/settings/policies/{policy_id}")
def policy_update(
    policy_id: int,
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    form: PolicyFormData = Depends(),
):
    parsed, err = _accept_policy(db, form)
    if err or not parsed:
        return _html(
            request,
            "policies.html",
            _policies_context(
                db, user, error=err, edit=db.get_agent_policy(policy_id)
            ),
            status_code=400,
        )
    updated = db.update_agent_policy(policy_id, **parsed)
    if not updated:
        return RedirectResponse(url="/settings/policies", status_code=303)
    return _html(
        request,
        "policies.html",
        _policies_context(db, user, message="Политика обновлена", edit=updated),
    )



@router.post("/settings/policies/{policy_id}/delete")
def policy_delete(
    policy_id: int,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    db.delete_agent_policy(policy_id)
    return RedirectResponse(url="/settings/policies", status_code=303)



@router.get("/settings/ldap", response_class=HTMLResponse)
def ldap_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    row = db.get_ldap_settings()
    return _html(
        request,
        "ldap_settings.html",
        _ldap_form_context(row, user=user),
    )



@router.post("/settings/ldap")
def ldap_settings_save(
    request: Request,
    form: LdapFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
    settings: Settings = Depends(get_settings),
):
    parsed, err = _parse_ldap_form(form)
    if err:
        row = db.get_ldap_settings()
        return _html(
            request,
            "ldap_settings.html",
            _ldap_form_context(row, user=user, error=err),
            status_code=400,
        )

    enc: Optional[str] = None
    if parsed["bind_password"].strip():
        if sensitive_over_http_blocked(settings):
            row = db.get_ldap_settings()
            return _html(
                request,
                "ldap_settings.html",
                _ldap_form_context(row, user=user, error=HTTP_SENSITIVE_MSG),
                status_code=403,
            )
        enc = encrypt_secret(data_key, parsed["bind_password"])

    db.update_ldap_settings(
        enabled=parsed["enabled"],
        host=parsed["host"],
        port=parsed["port"],
        use_ssl=parsed["use_ssl"],
        start_tls=parsed["start_tls"],
        bind_dn=parsed["bind_dn"],
        user_search_base=parsed["user_search_base"],
        user_filter_template=parsed["user_filter_template"],
        display_name_attr=parsed["display_name_attr"],
        default_role=parsed["default_role"],
        allowed_group=parsed["allowed_group"],
        tls_insecure=parsed["tls_insecure"],
        bind_password_enc=enc,
    )
    row = db.get_ldap_settings()
    return _html(
        request,
        "ldap_settings.html",
        _ldap_form_context(row, user=user, message="Настройки LDAP сохранены"),
    )



@router.post("/settings/ldap/test")
def ldap_settings_test(
    request: Request,
    form: LdapFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    parsed, err = _parse_ldap_form(form)
    row = db.get_ldap_settings()
    if err:
        return _html(
            request,
            "ldap_settings.html",
            _ldap_form_context(row, user=user, error=err),
            status_code=400,
        )

    password = parsed["bind_password"].strip()
    if not password:
        existing = load_ldap_view(db, data_key)
        password = existing.bind_password

    # Тестовый bind даже если в форме LDAP выключен; defaults из settings_from_row.
    view = settings_from_row({**parsed, "enabled": True}, bind_password=password)
    ok, msg = test_connection(view)
    preview = dict(row)
    preview.update(
        {
            "enabled": 1 if parsed["enabled"] else 0,
            "host": parsed["host"],
            "port": parsed["port"],
            "use_ssl": 1 if parsed["use_ssl"] else 0,
            "start_tls": 1 if parsed["start_tls"] else 0,
            "bind_dn": parsed["bind_dn"],
            "user_search_base": parsed["user_search_base"],
            "user_filter_template": parsed["user_filter_template"],
            "display_name_attr": parsed["display_name_attr"],
            "default_role": parsed["default_role"],
            "allowed_group": parsed["allowed_group"],
            "tls_insecure": 1 if parsed["tls_insecure"] else 0,
        }
    )
    return _html(
        request,
        "ldap_settings.html",
        _ldap_form_context(
            preview,
            user=user,
            test_result=("ОК: " if ok else "Ошибка: ") + msg,
            error=None if ok else msg,
        ),
    )



def _tls_context(
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    tls_applied: bool = False,
) -> dict:
    status = tls_status()
    cert = status.get("cert") or {}
    configured = bool(status.get("configured"))
    mode = status.get("mode") or "http"
    domain = status.get("domain") or ""
    return {
        "user": user,
        "settings_section": "tls",
        "message": message,
        "error": error,
        "warnings": warnings or cert.get("warnings") or [],
        "mode": mode,
        "tls_mode": mode,
        "domain": domain,
        "tls_domain": domain,
        "https_url": status.get("https_url") or https_panel_url(domain),
        "tls_applied": tls_applied,
        "has_private_key": bool(status.get("has_private_key")),
        "cert_path": status.get("cert_path") or "",
        "cert": cert if configured else None,
        "apply": status.get("apply") or {},
    }



def _tls_html(
    request: Request,
    user: WebUser,
    *,
    status_code: int = 200,
    message: Optional[str] = None,
    error: Optional[str] = None,
    warnings: Optional[list[str]] = None,
    tls_applied: bool = False,
):
    return _html(
        request,
        "tls_settings.html",
        _tls_context(
            user=user,
            message=message,
            error=error,
            warnings=warnings,
            tls_applied=tls_applied,
        ),
        status_code=status_code,
    )



@router.get("/settings/tls", response_class=HTMLResponse)
def tls_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
):
    return _tls_html(request, user)



@router.post("/settings/tls")
async def tls_settings_upload(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    certificate: UploadFile = File(...),
    private_key: UploadFile = File(...),
    chain: Optional[UploadFile] = File(None),
):
    cert_raw = await certificate.read()
    key_raw = await private_key.read()
    chain_raw = b""
    if chain is not None and chain.filename:
        chain_raw = await chain.read()

    if not cert_raw:
        return _tls_html(
            request, user, error="Пустой файл сертификата", status_code=400
        )
    if not key_raw:
        return _tls_html(
            request, user, error="Пустой файл закрытого ключа", status_code=400
        )

    try:
        info = save_tls_materials(cert_raw, key_raw, chain_pem=chain_raw)
    except ValueError as exc:
        return _tls_html(request, user, error=str(exc), status_code=400)
    except OSError as exc:
        return _tls_html(
            request,
            user,
            error=f"Не удалось сохранить файлы для установки: {exc}",
            status_code=500,
        )

    apply = wait_for_apply(since=str(info.get("saved_at") or ""), timeout_seconds=12.0)
    warnings = list(info.get("warnings") or [])
    if apply.get("ok") is True:
        message = apply.get("message") or "Сертификат установлен"
        https_ok = apply.get("mode") == "https"
        if https_ok:
            message += ". Защищённое соединение включено — откройте панель по https-адресу и войдите снова."
        return _tls_html(
            request,
            user,
            message=message,
            warnings=warnings,
            tls_applied=https_ok,
        )
    if apply.get("ok") is False:
        return _tls_html(
            request,
            user,
            error=apply.get("message") or "Не удалось применить сертификат на сервере",
            warnings=warnings,
            status_code=502,
        )
    return _tls_html(
        request,
        user,
        message=(
            "Сертификат загружен; сервер применяет изменения. "
            "Обновите страницу через несколько секунд."
        ),
        warnings=warnings,
    )



def _notify_check_groups() -> list[tuple[str, list[tuple[str, str]]]]:
    titles = {
        "critical": "Критичные",
        "high": "Высокие",
        "medium": "Средние",
        "low": "Низкие",
    }
    buckets: dict[str, list[tuple[str, str]]] = {level: [] for level in titles}
    for event_type, level in _EVENT_IMPORTANCE.items():
        label = _NOTIFY_CHECK_LABELS_RU.get(event_type, event_type)
        buckets.setdefault(level, []).append((event_type, label))
    return [
        (titles[level], sorted(buckets[level], key=lambda item: item[1].casefold()))
        for level in ("critical", "high", "medium", "low")
    ]



def _smtp_form_context(
    row: dict,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    test_result: Optional[str] = None,
) -> dict:
    notify = parse_notify_flags(row.get("notify") or row.get("notify_json"))
    return {
        "user": user,
        "settings_section": "mail",
        "message": message,
        "error": error,
        "test_result": test_result,
        "has_password": bool(row.get("password_enc")),
        "notify": notify,
        "notify_groups": _notify_check_groups(),
        "smtp": {
            "enabled": bool(row.get("enabled")),
            "host": row.get("host") or "",
            "port": int(row.get("port") or 587),
            "use_ssl": bool(row.get("use_ssl")),
            "use_starttls": bool(row.get("use_starttls")),
            "username": row.get("username") or "",
            "from_addr": row.get("from_addr") or "",
            "to_addrs": row.get("to_addrs") or "",
            "digest_interval_hours": int(row.get("digest_interval_hours") or 3),
            "digest_lookback_hours": int(row.get("digest_lookback_hours") or 3),
            "digest_window_start_hour": int(row.get("digest_window_start_hour") or 9),
            "digest_window_end_hour": int(row.get("digest_window_end_hour") or 19),
            "digest_weekdays": row.get("digest_weekdays_list")
            or parse_digest_weekdays(row.get("digest_weekdays")),
        },
        "digest_schedule_preview": digest_schedule_preview_ru(row),
        "digest_weekday_labels": [
            (0, "Пн"),
            (1, "Вт"),
            (2, "Ср"),
            (3, "Чт"),
            (4, "Пт"),
            (5, "Сб"),
            (6, "Вс"),
        ],
    }



def _parse_smtp_form(form: SmtpFormData) -> tuple[dict, Optional[str]]:
    try:
        port_i = int(form.port or "587")
    except ValueError:
        return {}, "Порт должен быть целым числом"
    if port_i < 1 or port_i > 65535:
        return {}, "Порт должен быть от 1 до 65535"
    try:
        digest_h = int((form.digest_interval_hours or "3").strip())
    except ValueError:
        return {}, "Интервал сводки должен быть целым числом часов"
    if digest_h < 1 or digest_h > 24:
        return {}, "Интервал сводки: от 1 до 24 часов"
    try:
        lookback_h = int((form.digest_lookback_hours or "3").strip())
    except ValueError:
        return {}, "Окно событий (lookback) должно быть целым числом часов"
    if lookback_h < 1 or lookback_h > 168:
        return {}, "Окно событий: от 1 до 168 часов"
    try:
        win_start = int((form.digest_window_start_hour or "9").strip())
        win_end = int((form.digest_window_end_hour or "19").strip())
    except ValueError:
        return {}, "Часы окна сводки должны быть целыми (0–24)"
    if win_start < 0 or win_start > 23:
        return {}, "Начало окна: час от 0 до 23"
    if win_end < 1 or win_end > 24:
        return {}, "Конец окна: час от 1 до 24 (не включительно)"
    if win_end <= win_start:
        return {}, "Конец окна должен быть позже начала"
    weekdays: list[int] = []
    for wd in range(7):
        if getattr(form, f"digest_wd_{wd}", None) is not None:
            weekdays.append(wd)
    if not weekdays:
        weekdays = default_digest_weekdays()
    selected = [item for item in (form.notify_type or []) if item in _EVENT_IMPORTANCE]
    if selected or form.notify_type:
        flags = {event_type: event_type in set(selected) for event_type in _EVENT_IMPORTANCE}
    else:
        flags = {key: False for key in DEFAULT_NOTIFY}
        notify_flags = {
            "hardware": form.notify_hardware,
            "stale": form.notify_stale,
            "online": form.notify_online,
            "disk_space": form.notify_disk_space,
            "enroll": form.notify_enroll,
            "hostname": form.notify_hostname,
            "domain": form.notify_domain,
            "pending_reboot": form.notify_pending_reboot,
        }
        for key, raw in notify_flags.items():
            if key in flags and raw is not None:
                flags[key] = True
    return {
        "enabled": form.enabled is not None,
        "host": (form.host or "").strip(),
        "port": port_i,
        "use_ssl": form.use_ssl is not None,
        "use_starttls": form.use_starttls is not None,
        "username": (form.username or "").strip(),
        "password": form.password,
        "from_addr": (form.from_addr or "").strip(),
        "to_addrs": (form.to_addrs or "").strip(),
        "digest_interval_hours": digest_h,
        "digest_lookback_hours": lookback_h,
        "digest_window_start_hour": win_start,
        "digest_window_end_hour": win_end,
        "digest_weekdays": json.dumps(weekdays, separators=(",", ":")),
        "notify_json": dump_notify_flags(flags),
    }, None



def _commit_retention(
    db: Database,
    *,
    events_days: int,
    inventory_days: int,
    stale_days: int,
    recent_minutes: int,
) -> Optional[str]:
    """Ошибка — секреты не пишутся. None — оба порога записаны."""
    if events_days < 1 or inventory_days < 1 or events_days > 3650 or inventory_days > 3650:
        return "Диапазон: от 1 до 3650 дней"
    planned = retention_threshold_seconds(stale_days, recent_minutes)
    if isinstance(planned, str):
        return planned
    stale_sec, recent_sec = planned
    db.update_retention_settings(events_days=events_days, inventory_days=inventory_days)
    db.set_site_secret(DEVICE_STALE_SITE_SECRET_KEY, str(stale_sec))
    db.set_site_secret(DEVICE_RECENT_SITE_SECRET_KEY, str(recent_sec))
    return None



def _inventory_signature_flag(raw: Optional[str]) -> str:
    return "1" if (raw or "").strip() in {"1", "on", "true"} else "0"



def _save_inventory_signature(db: Database, raw: Optional[str]) -> None:
    db.set_site_secret(
        "require_inventory_signature",
        _inventory_signature_flag(raw),
    )



def _general_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    return {
        "user": user,
        "settings_section": "general",
        "message": message,
        "error": error,
        "require_inventory_signature": db.get_bool_setting(
            "require_inventory_signature", settings.require_inventory_signature
        ),
    }



def _retention_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    stale_sec = effective_stale_after_seconds(db, settings)
    stale_days, stale_note_minutes = stale_days_form(stale_sec)
    recent_minutes = effective_recent_after_seconds(db) // 60
    return {
        "user": user,
        "settings_section": "retention",
        "retention": db.get_retention_settings(),
        "stale_after_days": stale_days,
        "stale_note_minutes": stale_note_minutes,
        "recent_after_minutes": recent_minutes,
        "message": message,
        "error": error,
    }



def _backup_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    secrets = security_status(db, settings).get("secrets") or {}
    keys = backup_keys_status(
        data_key_file=settings.data_key_file,
        session_secret_file=settings.session_secret_file,
        secrets=secrets,
        last_key_escrow_at=db.get_site_secret("last_key_escrow_at"),
    )
    return {
        "user": user,
        "settings_section": "backups",
        "backup": backup_status(settings.backup_dir),
        "keys": keys,
        "last_backup_at": db.get_site_secret("last_backup_at"),
        "secrets": secrets,
        "message": message,
        "error": error,
    }



@router.get("/settings")
def settings_home(user: WebUser = Depends(require_web_admin)):
    return RedirectResponse(url="/settings/general", status_code=303)



@router.get("/settings/general", response_class=HTMLResponse)
def general_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "general_settings.html",
        _general_context(db, settings, user=user),
    )



@router.post("/settings/general")
def general_settings_save(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    require_inventory_signature: str = Form(""),
):
    _save_inventory_signature(db, require_inventory_signature)
    return _html(
        request,
        "general_settings.html",
        _general_context(db, settings, user=user, message="Сохранено"),
    )



_INTEGRATION_OK = {
    "approved": "Заявка подтверждена. Программа заберёт ключ при следующей проверке.",
    "rejected": "Заявка отклонена.",
    "revoked": "Доступ отозван.",
}

_INTEGRATION_ERR = {
    "missing": "Заявка не найдена.",
    "state": "Это действие сейчас недоступно.",
    "key": "Сервер не может выдать ключ. Повторите подтверждение позже.",
}



@router.get("/settings/integrations", response_class=HTMLResponse)
def integrations_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    ok: str = "",
    err: str = "",
):
    from .integrations import list_integrations

    return _html(
        request,
        "integrations_settings.html",
        {
            "user": user,
            "items": list_integrations(db),
            "message": _INTEGRATION_OK.get(ok, ""),
            "error": _INTEGRATION_ERR.get(err, ""),
        },
    )



def _integration_action(
    db: Database,
    data_key: str,
    integration_id: str,
    action: str,
) -> RedirectResponse:
    from .integrations import IntegrationError, approve, is_integration_id, reject, revoke

    if not is_integration_id(integration_id):
        return RedirectResponse(url="/settings/integrations?err=missing", status_code=303)
    try:
        if action == "approve":
            approve(db, data_key, integration_id)
            code = "approved"
        elif action == "reject":
            reject(db, integration_id)
            code = "rejected"
        else:
            revoke(db, integration_id)
            code = "revoked"
    except IntegrationError as exc:
        err = "key" if exc.code == "no_data_key" else "state"
        if exc.code == "state":
            err = "state"
        return RedirectResponse(url=f"/settings/integrations?err={err}", status_code=303)
    return RedirectResponse(url=f"/settings/integrations?ok={code}", status_code=303)



@router.post("/settings/integrations/{integration_id}/approve")
def integrations_approve(
    integration_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    return _integration_action(db, data_key, integration_id, "approve")



@router.post("/settings/integrations/{integration_id}/reject")
def integrations_reject(
    integration_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return _integration_action(db, "", integration_id, "reject")



@router.post("/settings/integrations/{integration_id}/revoke")
def integrations_revoke(
    integration_id: str,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return _integration_action(db, "", integration_id, "revoke")



@router.get("/settings/retention", response_class=HTMLResponse)
def retention_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "retention_settings.html",
        _retention_context(db, settings, user=user),
    )



@router.post("/settings/retention")
def retention_settings_save(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    events_days: str = Form("90"),
    inventory_days: str = Form("180"),
    stale_after_days: str = Form("1"),
    recent_after_minutes: str = Form("10"),
):
    try:
        ev = int((events_days or "90").strip())
        inv = int((inventory_days or "180").strip())
        stale_days = int((stale_after_days or "1").strip())
        recent_min = int((recent_after_minutes or "10").strip())
    except ValueError:
        return _html(
            request,
            "retention_settings.html",
            _retention_context(
                db,
                settings,
                user=user,
                error="Укажите целые числа",
            ),
            status_code=400,
        )
    error = _commit_retention(
        db,
        events_days=ev,
        inventory_days=inv,
        stale_days=stale_days,
        recent_minutes=recent_min,
    )
    if error:
        return _html(
            request,
            "retention_settings.html",
            _retention_context(db, settings, user=user, error=error),
            status_code=400,
        )
    _invalidate_fleet_snapshot_cache()
    return _html(
        request,
        "retention_settings.html",
        _retention_context(
            db,
            settings,
            user=user,
            message="Настройки хранения сохранены",
        ),
    )



@router.get("/settings/smtp")
def smtp_settings_redirect():
    return RedirectResponse(url="/settings/mail", status_code=303)



@router.get("/settings/mail", response_class=HTMLResponse)
def mail_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
):
    return _html(
        request,
        "smtp_settings.html",
        _smtp_form_context(db.get_smtp_settings(), user=user),
    )



@router.post("/settings/mail")
def mail_settings_save(
    request: Request,
    form: SmtpFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
    settings: Settings = Depends(get_settings),
):
    parsed, err = _parse_smtp_form(form)
    if err:
        return _html(
            request,
            "smtp_settings.html",
            _smtp_form_context(db.get_smtp_settings(), user=user, error=err),
            status_code=400,
        )
    enc: Optional[str] = None
    if parsed["password"].strip():
        if sensitive_over_http_blocked(settings):
            return _html(
                request,
                "smtp_settings.html",
                _smtp_form_context(
                    db.get_smtp_settings(), user=user, error=HTTP_SENSITIVE_MSG
                ),
                status_code=403,
            )
        enc = encrypt_secret(data_key, parsed["password"])
    db.update_smtp_settings(
        enabled=parsed["enabled"],
        host=parsed["host"],
        port=parsed["port"],
        use_ssl=parsed["use_ssl"],
        use_starttls=parsed["use_starttls"],
        username=parsed["username"],
        from_addr=parsed["from_addr"],
        to_addrs=parsed["to_addrs"],
        notify_json=parsed["notify_json"],
        digest_interval_hours=parsed["digest_interval_hours"],
        digest_lookback_hours=parsed["digest_lookback_hours"],
        digest_window_start_hour=parsed["digest_window_start_hour"],
        digest_window_end_hour=parsed["digest_window_end_hour"],
        digest_weekdays=parsed["digest_weekdays"],
        password_enc=enc,
    )
    return _html(
        request,
        "smtp_settings.html",
        _smtp_form_context(
            db.get_smtp_settings(),
            user=user,
            message="Настройки почты сохранены",
        ),
    )



@router.post("/settings/mail/test")
def mail_settings_test(
    request: Request,
    form: SmtpFormData = Depends(),
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    data_key: str = Depends(get_data_key),
):
    parsed, err = _parse_smtp_form(form)
    row = db.get_smtp_settings()
    if err:
        return _html(
            request,
            "smtp_settings.html",
            _smtp_form_context(row, user=user, error=err),
            status_code=400,
        )
    pwd = parsed["password"].strip()
    if not pwd and row.get("password_enc"):
        pwd = decrypt_secret(data_key, row["password_enc"]) or ""
    recipients = parse_recipients(parsed["to_addrs"])
    if not parsed["from_addr"] or not recipients:
        return _html(
            request,
            "smtp_settings.html",
            _smtp_form_context(
                row,
                user=user,
                error="Укажите From и хотя бы одного получателя",
            ),
            status_code=400,
        )
    msg = build_hardware_email(
        bad_id="test-device",
        hostname="TEST-HOST",
        events=[],
        from_addr=parsed["from_addr"],
        to_addrs=recipients,
    )
    ok, detail = send_email(
        host=parsed["host"],
        port=parsed["port"],
        username=parsed["username"],
        password=pwd,
        use_ssl=parsed["use_ssl"],
        use_starttls=parsed["use_starttls"],
        message=msg,
    )
    preview = dict(row)
    preview.update(
        {
            "enabled": 1 if parsed["enabled"] else 0,
            "host": parsed["host"],
            "port": parsed["port"],
            "use_ssl": 1 if parsed["use_ssl"] else 0,
            "use_starttls": 1 if parsed["use_starttls"] else 0,
            "username": parsed["username"],
            "from_addr": parsed["from_addr"],
            "to_addrs": parsed["to_addrs"],
            "notify_json": parsed["notify_json"],
            "digest_interval_hours": parsed["digest_interval_hours"],
            "digest_lookback_hours": parsed["digest_lookback_hours"],
            "digest_window_start_hour": parsed["digest_window_start_hour"],
            "digest_window_end_hour": parsed["digest_window_end_hour"],
            "digest_weekdays": parsed["digest_weekdays"],
        }
    )
    return _html(
        request,
        "smtp_settings.html",
        _smtp_form_context(
            preview,
            user=user,
            test_result=("ОК: " if ok else "Ошибка: ") + detail,
            error=None if ok else detail,
        ),
    )



@router.get("/settings/backups", response_class=HTMLResponse)
def backups_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "backup_settings.html",
        _backup_context(db, settings, user=user),
    )



@router.post("/settings/backups/run")
def backups_settings_run(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    from .db import utc_now

    result = run_daily_backup(
        settings.backup_dir,
        database_url=settings.database_url,
    )
    if result.get("ok"):
        db.set_site_secret("last_backup_at", utc_now())
        db.set_site_secret("last_backup_path", result.get("path") or "")
        message = f"Бэкап записан: {result.get('name')}"
        error = None
    else:
        message = None
        error = result.get("error") or "Ошибка бэкапа"
    return _html(
        request,
        "backup_settings.html",
        _backup_context(db, settings, user=user, message=message, error=error),
        status_code=200 if result.get("ok") else 500,
    )




@router.get("/settings/backups/site-bundle")
def backups_site_bundle_download(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Скачать site bundle (DB + keys + MSI). Секреты только в файле, не в HTML."""
    if sensitive_over_http_blocked(settings):
        return _html(
            request,
            "backup_settings.html",
            _backup_context(db, settings, user=user, error=HTTP_SENSITIVE_MSG),
            status_code=403,
        )
    try:
        payload, filename = build_site_bundle(
            db=db,
            backup_dir=settings.backup_dir,
            updates_dir=settings.agent_updates_dir,
            data_key_file=settings.data_key_file,
            session_secret_file=settings.session_secret_file,
            include_msi_files=False,
        )
    except Exception as exc:  # noqa: BLE001
        return _html(
            request,
            "backup_settings.html",
            _backup_context(
                db, settings, user=user, error=f"Не удалось собрать bundle: {exc}"
            ),
            status_code=500,
        )
    return StreamingResponse(
        iter([payload]),
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )



@router.get("/settings/backups/key-escrow")
def backups_key_escrow_download(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Скачать только escrow keys (без DB). SEC-005; только после HTTPS."""
    from .db import utc_now

    if sensitive_over_http_blocked(settings):
        return _html(
            request,
            "backup_settings.html",
            _backup_context(db, settings, user=user, error=HTTP_SENSITIVE_MSG),
            status_code=403,
        )
    try:
        payload, filename = build_key_escrow_archive(
            data_key_file=settings.data_key_file,
            session_secret_file=settings.session_secret_file,
        )
    except Exception as exc:  # noqa: BLE001
        return _html(
            request,
            "backup_settings.html",
            _backup_context(
                db, settings, user=user, error=f"Не удалось собрать key escrow: {exc}"
            ),
            status_code=500,
        )
    db.set_site_secret("last_key_escrow_at", utc_now())
    return StreamingResponse(
        iter([payload]),
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
        },
    )



def _updates_context(
    db: Database,
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    return {
        "user": user,
        "settings_section": "updates",
        "agent_update": db.get_agent_update(),
        "msi_versions": db.list_agent_msi_versions(),
        "github_repo": settings.github_repo,
        "updates_dir": str(settings.agent_updates_dir),
        "sync_interval": settings.agent_update_sync_interval_seconds,
        "message": message,
        "error": error,
    }



@router.get("/settings/updates", response_class=HTMLResponse)
def updates_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user),
    )



@router.post("/settings/updates/sync")
def updates_settings_sync(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        record = sync_from_github(
            db,
            settings,
            data_key=getattr(request.app.state, "data_key", "") or "",
        )
        message = f"Синхронизировано: {record.get('version') if record else 'ok'}"
        error = None
    except Exception as exc:  # noqa: BLE001
        message = None
        error = f"Ошибка sync: {exc}"
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=200 if message else 502,
    )



@router.post("/settings/updates/upload")
async def updates_settings_upload(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    msi: UploadFile = File(...),
    version: str = Form(""),
    sha256: str = Form(""),
    manifest: Optional[UploadFile] = File(None),
):
    raw = await msi.read()
    if not raw:
        return _html(
            request,
            "updates_settings.html",
            _updates_context(
                db, settings, user=user, error="Пустой файл установщика"
            ),
            status_code=400,
        )
    manifest_text = None
    if manifest is not None and manifest.filename:
        try:
            manifest_text = (await manifest.read()).decode("utf-8")
        except Exception:  # noqa: BLE001
            return _html(
                request,
                "updates_settings.html",
                _updates_context(
                    db, settings, user=user, error="Не удалось прочитать файл описания версии"
                ),
                status_code=400,
            )
    try:
        record = ingest_uploaded_msi(
            db,
            settings,
            raw=raw,
            filename=msi.filename or "",
            version=version,
            sha256=sha256,
            manifest_json=manifest_text,
            data_key=getattr(request.app.state, "data_key", "") or "",
        )
        message = f"Загружено: {record.get('version')} ({record.get('msi_name')})"
        error = None
    except Exception as exc:  # noqa: BLE001
        message = None
        error = f"Ошибка загрузки: {exc}"
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=200 if message else 400,
    )



@router.post("/settings/updates/delete")
def updates_settings_delete(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    version: str = Form(...),
):
    ver = (version or "").strip()
    try:
        delete_msi_version(db, settings, ver)
        message = f"Удалена версия {ver} из каталога"
        error = None
        code = 200
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=code,
    )



@router.post("/settings/updates/set-latest")
def updates_settings_set_latest(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    version: str = Form(...),
):
    try:
        record = set_latest_msi_version(db, version.strip())
        message = f"Основная версия в каталоге: {record.get('version')}"
        error = None
        code = 200
    except ValueError as exc:
        message = None
        error = str(exc)
        code = 400
    return _html(
        request,
        "updates_settings.html",
        _updates_context(db, settings, user=user, message=message, error=error),
        status_code=code,
    )



@router.post("/settings/updates/access")
def updates_access_save(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
    require_inventory_signature: str = Form(""),
):
    _save_inventory_signature(db, require_inventory_signature)
    return _html(
        request,
        "general_settings.html",
        _general_context(db, settings, user=user, message="Сохранено"),
    )



def _server_update_context(
    settings: Settings,
    *,
    user: WebUser,
    message: Optional[str] = None,
    error: Optional[str] = None,
    check: Optional[dict] = None,
    branches: Optional[list] = None,
) -> dict:
    panel = server_status_panel(settings)
    branch_list = branches
    if branch_list is None:
        try:
            branch_list = list_remote_branches(settings)
        except Exception:  # noqa: BLE001
            branch_list = []
    return {
        "user": user,
        "settings_section": "server_update",
        "panel": panel,
        "check": check,
        "branches": branch_list or [],
        "message": message,
        "error": error,
    }



def _server_update_page(
    request: Request,
    settings: Settings,
    user: WebUser,
    *,
    message: Optional[str] = None,
    error: Optional[str] = None,
    check: Optional[dict] = None,
    branches: Optional[list] = None,
    status_code: int = 200,
):
    return _html(
        request,
        "server_update_settings.html",
        _server_update_context(
            settings,
            user=user,
            message=message,
            error=error,
            check=check,
            branches=branches,
        ),
        status_code=status_code,
    )



@router.get("/settings/server-update", response_class=HTMLResponse)
def server_update_settings_page(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
):
    flashed = _take_flash(request)
    return _server_update_page(
        request,
        settings,
        user,
        message=flashed.get("message"),
        error=flashed.get("error"),
        check=flashed.get("check"),
    )



@router.post("/settings/server-update/branch")
def server_update_set_branch(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(...),
):
    try:
        set_preferred_branch(branch, releases_dir(settings))
        message = f"Ветка обновления: {branch.strip()}"
        error = None
    except ValueError as exc:
        message = None
        error = str(exc)
    return _see_other(request, "/settings/server-update", message=message, error=error)



@router.post("/settings/server-update/check")
def server_update_check(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(""),
):
    try:
        result = server_check_updates(
            settings, branch=(branch or "").strip() or None
        )
        if result.get("error"):
            message = None
            error = result["error"]
        elif result.get("update_available"):
            remote = result.get("remote") or {}
            message = (
                f"Доступно обновление: {remote.get('short_sha') or remote.get('sha')}"
            )
            error = None
        else:
            message = "Установленная версия совпадает с HEAD ветки"
            error = None
    except ValueError as exc:
        result = None
        message = None
        error = str(exc)
    return _see_other(
        request,
        "/settings/server-update",
        message=message,
        error=error,
        check=_flash_check(result),
    )



@router.post("/settings/server-update/apply")
def server_update_apply(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(""),
    sha: str = Form(""),
):
    root = releases_dir(settings)
    try:
        req = server_request_apply(
            action="apply",
            branch=branch,
            sha=sha,
            directory=root,
        )
        message, error, _code = server_outcome_for_apply_request(
            root,
            req,
            ok_default="Обновление применено",
            fail_default="apply не удался",
            pending=(
                "Запрос отправлен; сервер устанавливает обновление. "
                "Обновите страницу через минуту."
            ),
        )
    except ValueError as exc:
        message = None
        error = str(exc)
    except OSError as exc:
        message = None
        error = f"Не удалось записать apply.request: {exc}"
    return _see_other(request, "/settings/server-update", message=message, error=error)



@router.post("/settings/server-update/rollback")
def server_update_rollback(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    slot_id: str = Form(...),
):
    root = releases_dir(settings)
    try:
        req = server_request_apply(
            action="rollback", slot_id=slot_id, directory=root
        )
        message, error, _code = server_outcome_for_apply_request(
            root,
            req,
            ok_default="Откат выполнен",
            fail_default="rollback не удался",
            pending="Запрос отката отправлен; дождитесь завершения на сервере.",
        )
    except ValueError as exc:
        message = None
        error = str(exc)
    return _see_other(request, "/settings/server-update", message=message, error=error)



@router.post("/settings/server-update/token")
def server_update_set_token(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    token: str = Form(...),
):
    root = releases_dir(settings)
    try:
        req = request_set_github_token(token, directory=root)
        message, error, _code = server_outcome_for_apply_request(
            root,
            req,
            ok_default="Токен для обновлений сохранён (значение больше не показывается).",
            fail_default="не удалось записать токен",
            pending="Токен передан helper; обновите страницу через несколько секунд.",
        )
        get_settings.cache_clear()
    except ValueError as exc:
        message = None
        error = str(exc)
    return _see_other(
        request,
        "/settings/server-update",
        message=message,
        error=error,
    )



@router.post("/settings/server-update/msi/trigger")
def server_update_msi_trigger(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    settings: Settings = Depends(get_settings),
    branch: str = Form(""),
    version: str = Form(""),
):
    try:
        meta = trigger_msi_workflow(
            settings,
            branch=(branch or "").strip() or None,
            version=version,
        )
        message = f"Запущена сборка установщика агента (ветка {meta.get('branch')})"
        error = None
    except Exception as exc:  # noqa: BLE001
        message = None
        error = str(exc)
    return _see_other(request, "/settings/server-update", message=message, error=error)



@router.post("/settings/server-update/msi/poll")
def server_update_msi_poll(
    request: Request,
    user: WebUser = Depends(require_web_admin),
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        meta = poll_msi_workflow(settings, ingest=True, db=db)
        st = meta.get("status")
        conclusion = meta.get("conclusion")
        if meta.get("ingested"):
            message = (
                f"Установщик добавлен в каталог: {meta['ingested'].get('version')} "
                f"({meta['ingested'].get('msi_name')})"
            )
            error = meta.get("error")
        elif st == "completed" and conclusion != "success":
            message = None
            error = f"Сборка установщика завершилась с ошибкой: {conclusion}"
        else:
            message = f"Статус сборки установщика: {st or '—'} / {conclusion or '—'}"
            error = meta.get("error")
    except Exception as exc:  # noqa: BLE001
        message = None
        error = str(exc)
    return _see_other(request, "/settings/server-update", message=message, error=error)
