"""SMTP-хелперы для алертов оператору (soft-fail при неверной конфигурации)."""

from __future__ import annotations

import html
import json
import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .db import Database

logger = logging.getLogger(__name__)

HARDWARE_ALERT_TYPES = frozenset(
    {
        "disk_added",
        "disk_removed",
        "cpu_change",
        "ram_module_added",
        "ram_module_removed",
        "ram_bytes_change",
        "serial_change",
        "model_change",
        "manufacturer_change",
        "chassis_type_change",
        # inventory-plus: BSOD bugcheck (mail default on via hardware)
        "minidump_bugcheck",
    }
)

# Ключи-переключатели в smtp_settings.notify_json (defaults описаны в UI).
DEFAULT_NOTIFY: dict[str, bool] = {
    "hardware": True,  # ОЗУ / CPU / диски / serial / model / BSOD
    "stale": True,  # устройство перестало отвечать
    "online": True,  # устройство снова на связи после stale
    "disk_space": True,  # мало / критически мало места на диске
    "enroll": True,  # новое устройство зарегистрировано
    "hostname": False,  # смена hostname
    "domain": False,  # смена domain
    # inventory-plus: ops-сигнал; default off (не спамить)
    "pending_reboot": False,
}

INVENTORY_MAIL_LAST_DIGEST_KEY = "inventory_mail_last_digest_at"

Polarity = Literal["added", "removed", "changed"]

_POLARITY_LABEL_RU: dict[Polarity, str] = {
    "added": "Появилось",
    "removed": "Пропало",
    "changed": "Изменилось",
}

_POLARITY_STYLE: dict[Polarity, tuple[str, str]] = {
    "added": ("#166534", "#dcfce7"),
    "removed": ("#991b1b", "#fee2e2"),
    "changed": ("#92400e", "#fef3c7"),
}

# Внутренности SVG (viewBox 0 0 20 20), как в templates/macros/icons.html
_ICON_PATHS: dict[str, str] = {
    "host": (
        '<rect x="2.5" y="3.5" width="15" height="10" rx="1.75"/>'
        '<path d="M7 16.5h6M10 13.5v3"/>'
    ),
    "cpu": (
        '<rect x="5" y="5" width="10" height="10" rx="1.5"/>'
        '<rect x="7.5" y="7.5" width="5" height="5" rx="0.75"/>'
        '<path d="M8 2.75v2.25M12 2.75v2.25M8 15v2.25M12 15v2.25M2.75 8h2.25M2.75 12h2.25M15 8h2.25M15 12h2.25"/>'
    ),
    "ram": (
        '<rect x="2.5" y="6" width="15" height="8" rx="1.25"/>'
        '<path d="M5.5 6V4.25M8.5 6V4.25M11.5 6V4.25M14.5 6V4.25M6.5 10.25h2M11.5 10.25h2"/>'
    ),
    "disk": (
        '<ellipse cx="10" cy="5.5" rx="6.5" ry="2.4"/>'
        '<path d="M3.5 5.5v8.5c0 1.35 2.9 2.45 6.5 2.45s6.5-1.1 6.5-2.45V5.5"/>'
        '<path d="M3.5 10c0 1.35 2.9 2.45 6.5 2.45s6.5-1.1 6.5-2.45"/>'
    ),
    "serial": (
        '<rect x="3.5" y="5" width="13" height="10" rx="1.5"/>'
        '<path d="M6.5 8v4M9 8v4M11.5 8v4M14 8v4"/>'
    ),
    "model": (
        '<rect x="2.5" y="4.5" width="15" height="10" rx="1.75"/>'
        '<path d="M8 14.5h4"/>'
    ),
    "events": (
        '<path d="M10 3.5v2M10 14.5v2M3.5 10h2M14.5 10h2"/>'
        '<circle cx="10" cy="10" r="3.25"/>'
    ),
    "devices": (
        '<rect x="3" y="4" width="9" height="7" rx="1.25"/>'
        '<rect x="8" y="9" width="9" height="7" rx="1.25"/>'
    ),
    "bios": (
        '<rect x="3.5" y="4" width="13" height="12" rx="1.5"/>'
        '<path d="M6.5 7h7M6.5 10h7M6.5 13h4"/>'
    ),
    "updates": (
        '<path d="M10 3.5a6.5 6.5 0 1 0 6.1 4.1"/>'
        '<path d="M16.5 3.5v4h-4"/>'
    ),
}

NOTIFY_LABELS_RU: dict[str, str] = {
    "hardware": "Изменение железа (ОЗУ, CPU, диски, serial/model, BSOD)",
    "stale": "Устройство перестало отвечать (устарело)",
    "online": "Устройство снова на связи после простоя",
    "disk_space": "Мало / критически мало места на диске",
    "enroll": "Новое устройство зарегистрировано",
    "hostname": "Смена hostname",
    "domain": "Смена domain",
    "pending_reboot": "Ожидание перезагрузки (pending reboot)",
}

_WD_SHORT_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def default_digest_weekdays() -> list[int]:
    return [0, 1, 2, 3, 4, 5]


def parse_digest_weekdays(raw: Any) -> list[int]:
    data: Any = raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
    out: list[int] = []
    if isinstance(data, list):
        for item in data:
            try:
                wd = int(item)
            except (TypeError, ValueError):
                continue
            if 0 <= wd <= 6 and wd not in out:
                out.append(wd)
    if not out:
        return default_digest_weekdays()
    return sorted(out)


def digest_slot_hours(start_hour: int, end_hour: int, interval_hours: int) -> list[int]:
    start = max(0, min(int(start_hour), 23))
    end = max(1, min(int(end_hour), 24))
    step = max(1, min(int(interval_hours), 24))
    if end <= start:
        end = min(24, start + step)
    return list(range(start, end, step))


def digest_schedule_preview_ru(settings: dict[str, Any]) -> str:
    """Человекочитаемое расписание сводки для UI и писем."""
    interval = max(1, min(int(settings.get("digest_interval_hours") or 3), 24))
    start = int(settings.get("digest_window_start_hour") or 9)
    end = int(settings.get("digest_window_end_hour") or 19)
    weekdays = settings.get("digest_weekdays_list")
    if not isinstance(weekdays, list):
        weekdays = parse_digest_weekdays(settings.get("digest_weekdays"))
    wd_labels = [_WD_SHORT_RU[d] for d in weekdays if 0 <= d <= 6]
    if len(wd_labels) >= 2 and weekdays == list(range(weekdays[0], weekdays[-1] + 1)):
        wd_text = f"{wd_labels[0]}–{wd_labels[-1]}"
    elif wd_labels:
        wd_text = ", ".join(wd_labels)
    else:
        wd_text = "—"
    slots = digest_slot_hours(start, end, interval)
    slot_text = ", ".join(f"{h}:00" for h in slots) if slots else "—"
    return (
        f"{wd_text}, с {start}:00 до {end}:00, каждые {interval} ч ({slot_text})"
    )


def digest_send_due(
    smtp_row: dict[str, Any], *, last_slot_key: Optional[str], force: bool
) -> tuple[bool, str, str]:
    """Пора ли слать сводку: локальное время, слот YYYY-MM-DDTHH."""
    if force:
        now = datetime.now()
        return True, now.strftime("%Y-%m-%dT%H"), "принудительная отправка"
    now = datetime.now()
    if now.minute >= 10:
        return False, "", "digest_minute_window"
    weekdays = parse_digest_weekdays(smtp_row.get("digest_weekdays"))
    if now.weekday() not in weekdays:
        return False, "", "digest_weekday"
    interval = max(1, min(int(smtp_row.get("digest_interval_hours") or 3), 24))
    start = int(smtp_row.get("digest_window_start_hour") or 9)
    end = int(smtp_row.get("digest_window_end_hour") or 19)
    slots = digest_slot_hours(start, end, interval)
    if now.hour not in slots:
        return False, "", "digest_slot"
    slot_key = now.strftime("%Y-%m-%dT%H")
    if (last_slot_key or "").strip() == slot_key:
        return False, "", "digest_slot_sent"
    window_label = (
        f"{digest_schedule_preview_ru(smtp_row)} · все неотправленные события"
    )
    return True, slot_key, window_label


def parse_notify_flags(raw: Any) -> dict[str, bool]:
    flags = dict(DEFAULT_NOTIFY)
    data: Any = raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
    if isinstance(data, dict):
        for key in DEFAULT_NOTIFY:
            if key in data:
                flags[key] = bool(data[key])
    return flags


def dump_notify_flags(flags: dict[str, bool]) -> str:
    merged = parse_notify_flags(flags)
    return json.dumps(merged, separators=(",", ":"), ensure_ascii=False)


def parse_recipients(raw: str) -> list[str]:
    parts = []
    for chunk in (raw or "").replace(";", ",").split(","):
        addr = chunk.strip()
        if addr:
            parts.append(addr)
    return parts


def filter_events_for_mail(
    events: list[dict[str, Any]], flags: dict[str, bool]
) -> list[dict[str, Any]]:
    wanted: set[str] = set()
    if flags.get("hardware"):
        wanted |= HARDWARE_ALERT_TYPES
    if flags.get("hostname"):
        wanted.add("hostname_change")
    if flags.get("domain"):
        wanted.add("domain_change")
    if flags.get("pending_reboot"):
        wanted.add("pending_reboot_change")
    if flags.get("enroll"):
        wanted.add("device_enrolled")
    if flags.get("stale"):
        wanted.add("device_stale")
    if flags.get("online"):
        wanted.add("device_back_online")
    if flags.get("disk_space"):
        wanted.add("volume_free_drop")
        wanted.add("volume_free_critical")
    # last_boot_change / timezone_change — в ленте событий, mail default off
    return [e for e in events if e.get("type") in wanted]


def build_alert_email(
    *,
    subject: str,
    body_lines: list[str],
    from_addr: str,
    to_addrs: list[str],
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    lines = list(body_lines)
    lines.extend(["", "—", "Сообщение сформировано сервером bAD."])
    msg.set_content("\n".join(lines))
    return msg


def event_visual(event_type: str) -> dict[str, str]:
    """Иконка и полярность события для digest-письма."""
    t = (event_type or "").strip()
    if t == "device_enrolled":
        return {"icon": "devices", "polarity": "added"}
    if t == "device_stale":
        return {"icon": "host", "polarity": "removed"}
    if t == "device_back_online":
        return {"icon": "host", "polarity": "added"}
    if t == "volume_free_critical":
        return {"icon": "disk", "polarity": "removed"}
    if t == "volume_free_drop":
        return {"icon": "disk", "polarity": "changed"}

    polarity: Polarity = "changed"
    if t.endswith("_added"):
        polarity = "added"
    elif t.endswith("_removed"):
        polarity = "removed"

    icon = "events"
    if "disk" in t:
        icon = "disk"
    elif "ram" in t:
        icon = "ram"
    elif "cpu" in t:
        icon = "cpu"
    elif "serial" in t:
        icon = "serial"
    elif any(x in t for x in ("model", "manufacturer", "chassis")):
        icon = "model"
    elif "hostname" in t or "domain" in t:
        icon = "host"
    elif "pending_reboot" in t or "reboot" in t:
        icon = "updates"
    elif "bios" in t or "bugcheck" in t or "minidump" in t:
        icon = "bios"
    return {"icon": icon, "polarity": polarity}


def _polarity_marker_html(polarity: Polarity) -> str:
    """Outlook-safe маркер вместо SVG."""
    char = {"added": "+", "removed": "−", "changed": "~"}.get(polarity, "~")
    fg, _bg = _POLARITY_STYLE.get(polarity, _POLARITY_STYLE["changed"])
    return (
        f'<span style="font-weight:700;font-size:16px;line-height:1;color:{fg}">'
        f"{html.escape(char)}</span>"
    )


def _badge_html(polarity: Polarity) -> str:
    fg, bg = _POLARITY_STYLE[polarity]
    label = _POLARITY_LABEL_RU[polarity]
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f"font-size:12px;font-weight:600;color:{fg};background:{bg}\">"
        f"{html.escape(label)}</span>"
    )


def build_inventory_digest_email(
    *,
    devices_groups: list[dict[str, Any]],
    from_addr: str,
    to_addrs: list[str],
    window_label: str,
    park_stats: Optional[dict[str, Any]] = None,
) -> EmailMessage:
    """Сводка inventory-событий: plain + HTML, группировка по устройствам."""
    n_devices = len(devices_groups)
    n_events = sum(len(g.get("events") or []) for g in devices_groups)
    # Локальное время сервера — коротко в теме (удобно в Outlook).
    ts = datetime.now().strftime("%d.%m %H:%M")
    subject = f"bAD: сводка {ts} · {n_devices} устр., {n_events} событ."
    plain_lines = [
        f"Сводка уведомлений ({window_label}).",
        "",
    ]
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body "
        'style="font-family:Segoe UI,system-ui,sans-serif;font-size:14px;'
        'color:#1f2937;line-height:1.45;margin:0;padding:16px">',
        f"<p style=\"margin:0 0 16px\">Сводка уведомлений "
        f"({html.escape(window_label)}).</p>",
    ]
    if park_stats:
        total = int(park_stats.get("total_active") or 0)
        online = int(park_stats.get("online") or 0)
        plain_lines.extend(
            [f"Парк: всего хостов {total}, онлайн {online}", ""]
        )
        html_parts.append(
            '<table role="presentation" cellpadding="8" cellspacing="0" '
            'style="margin:0 0 16px;border-collapse:collapse;border:1px solid #e5e7eb">'
            "<tr>"
            '<td style="background:#f9fafb;font-weight:600;border:1px solid #e5e7eb">'
            "Всего хостов</td>"
            f'<td style="border:1px solid #e5e7eb">{total}</td>'
            '<td style="background:#f9fafb;font-weight:600;border:1px solid #e5e7eb">'
            "Онлайн</td>"
            f'<td style="border:1px solid #e5e7eb">{online}</td>'
            "</tr></table>"
        )
    for group in devices_groups:
        device_id = group.get("device_id") or "—"
        hostname = group.get("hostname") or device_id
        model = (group.get("hardware_model") or "").strip()
        owner = (group.get("user_display_name") or "").strip()
        presence = (group.get("user_presence_caption") or "").strip()
        meta_bits: list[str] = []
        if model:
            meta_bits.append(f"модель: {model}")
        if owner:
            pres = f" ({presence})" if presence else ""
            meta_bits.append(f"пользователь: {owner}{pres}")
        meta_plain = " · ".join(meta_bits)
        plain_lines.append(f"=== {hostname} ({device_id}) ===")
        if meta_plain:
            plain_lines.append(f"  {meta_plain}")
        sub_lines = [html.escape(device_id)]
        if meta_bits:
            sub_lines.append(html.escape(" · ".join(meta_bits)))
        sub_html = "<br>".join(
            f'<span style="color:#6b7280;font-weight:400;font-size:12px">{line}</span>'
            for line in sub_lines
        )
        html_parts.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:0 0 20px;border:1px solid #e5e7eb;border-radius:8px;'
            'border-collapse:separate;overflow:hidden">'
            f'<tr><td colspan="2" style="padding:10px 12px;background:#f3f4f6;'
            f'font-weight:600">{html.escape(hostname)} {sub_html}</td></tr>'
        )
        for ev in group.get("events") or []:
            vis = event_visual(str(ev.get("type") or ""))
            polarity = vis["polarity"]  # type: ignore[assignment]
            badge_plain = _POLARITY_LABEL_RU[polarity]
            summary = str(ev.get("summary") or "")
            plain_lines.append(f"  [{badge_plain}] {summary}")
            marker = _polarity_marker_html(polarity)
            html_parts.append(
                "<tr><td style=\"padding:8px 12px;width:28px;vertical-align:top;"
                'text-align:center">'
                f"{marker}</td>"
                f'<td style="padding:8px 12px;vertical-align:top">'
                f"{_badge_html(polarity)} "
                f'<span style="margin-left:6px">{html.escape(summary)}</span>'
                "</td></tr>"
            )
        html_parts.append("</table>")
        plain_lines.append("")
    plain_lines.extend(["—", "Сообщение сформировано сервером bAD."])
    html_parts.append(
        '<p style="margin:16px 0 0;color:#9ca3af;font-size:12px">'
        "Сообщение сформировано сервером bAD.</p></body></html>"
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content("\n".join(plain_lines))
    msg.add_alternative("".join(html_parts), subtype="html")
    return msg


def build_hardware_email(
    *,
    device_id: str,
    hostname: Optional[str],
    events: list[dict[str, Any]],
    from_addr: str,
    to_addrs: list[str],
) -> EmailMessage:
    """Образец digest для тестовой отправки из настроек почты."""
    sample_groups = [
        {
            "device_id": device_id,
            "hostname": hostname or "WORKSTATION-01",
            "hardware_model": "Dell OptiPlex 7090 (пример)",
            "user_display_name": "ivanov",
            "user_presence_caption": "в системе",
            "events": [
                {
                    "type": "disk_added",
                    "summary": "Диск Samsung SSD 500 ГБ (пример: появилось)",
                },
                {
                    "type": "ram_module_removed",
                    "summary": "Модуль ОЗУ 8 ГБ слот 2 (пример: пропало)",
                },
                {
                    "type": "cpu_change",
                    "summary": "Тестовое письмо SMTP / сводка digest (пример: изменилось)",
                },
            ],
        },
        {
            "device_id": "sample-device-2",
            "hostname": "LAPTOP-02",
            "hardware_model": "Lenovo ThinkPad T14",
            "user_display_name": "petrov",
            "user_presence_caption": "последний",
            "events": [
                {
                    "type": "hostname_change",
                    "summary": "hostname: OLD → NEW (пример второго устройства)",
                },
                {
                    "type": "device_enrolled",
                    "summary": "Зарегистрировано новое устройство (пример: появилось)",
                },
                {
                    "type": "volume_free_critical",
                    "summary": "Критически мало места на системном диске C: — осталось 8 ГБ",
                },
            ],
        },
    ]
    if events:
        sample_groups[0]["events"] = events
    return build_inventory_digest_email(
        devices_groups=sample_groups,
        from_addr=from_addr,
        to_addrs=to_addrs,
        window_label="тестовая отправка",
        park_stats={"online": 18, "total_active": 24},
    )


def _mail_digest_enabled(flags: dict[str, bool]) -> bool:
    merged = parse_notify_flags(flags)
    return any(merged.values())


def _parse_utc_iso(ts: str) -> Optional[datetime]:
    raw = (ts or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _mail_group_from_device(device: Optional[dict[str, Any]]) -> dict[str, Any]:
    from .device_meta import normalize_logged_on_list

    if not device:
        return {}
    meta = device.get("meta") if isinstance(device.get("meta"), dict) else {}
    presence = str(meta.get("user_presence") or "")
    if presence == "online":
        names = normalize_logged_on_list(meta.get("logged_on"))
        user_display_name = names[0] if names else None
        user_presence_caption = "в системе"
    else:
        user_display_name = meta.get("last_logged_on") or None
        user_presence_caption = "последний" if user_display_name else ""
    out: dict[str, Any] = {}
    model = (meta.get("hardware_model") or "").strip()
    if model:
        out["hardware_model"] = model
    if user_display_name:
        out["user_display_name"] = user_display_name
        out["user_presence_caption"] = user_presence_caption
    host = device.get("hostname")
    if host:
        out["hostname"] = host
    return out


def _finalize_digest_send(
    db: "Database", event_ids: list[int], slot_key: str
) -> None:
    if event_ids:
        db.mark_device_events_mailed(event_ids, utc_now_iso())
    db.set_site_secret(INVENTORY_MAIL_LAST_DIGEST_KEY, slot_key)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def flush_inventory_mail_digest(
    db: "Database",
    smtp_row: dict[str, Any],
    password: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Отправить накопленные inventory-события одним digest (soft-fail)."""
    result: dict[str, Any] = {"sent": False, "skipped": True, "reason": ""}
    from_addr, recipients = _smtp_ready(smtp_row)
    if not from_addr:
        result["reason"] = "smtp_not_ready"
        return result
    flags = parse_notify_flags(smtp_row.get("notify_json"))
    if not _mail_digest_enabled(flags):
        result["reason"] = "mail_digest_disabled"
        return result

    last_slot = (db.get_site_secret(INVENTORY_MAIL_LAST_DIGEST_KEY) or "").strip()
    due, slot_key, label_or_reason = digest_send_due(
        smtp_row, last_slot_key=last_slot, force=force
    )
    if not due:
        result["reason"] = label_or_reason
        return result
    window_label = label_or_reason

    unmailed = db.list_unmailed_device_events()
    if not unmailed:
        result["reason"] = "no_events"
        result["skipped"] = True
        return result

    filtered = filter_events_for_mail(unmailed, flags)

    if not filtered:
        result["skipped"] = True
        result["reason"] = "filtered_empty"
        return result

    # Все неотправленные (накопленные вне слота тоже уйдут в ближайший слот).
    from .config import get_settings
    from .device_health import effective_stale_after_seconds

    settings = get_settings()
    stale_sec = effective_stale_after_seconds(db, settings)
    active, archived = db.list_fleet_active_archived()
    stats = db.overview_stats(
        stale_after_seconds=stale_sec, active=active, archived=archived
    )
    park_stats = {
        "online": int(stats.get("online") or 0),
        "total_active": int(stats.get("total_active") or 0),
    }

    groups_map: dict[str, dict[str, Any]] = {}
    for ev in filtered:
        did = str(ev.get("device_id") or "")
        if did not in groups_map:
            detail = db.get_device_detail(did) if did else None
            base = {
                "device_id": did,
                "hostname": ev.get("hostname"),
                "events": [],
            }
            base.update(_mail_group_from_device(detail))
            if not base.get("hostname") and detail:
                base["hostname"] = detail.get("hostname")
            groups_map[did] = base
        groups_map[did]["events"].append(ev)
    devices_groups = list(groups_map.values())

    msg = build_inventory_digest_email(
        devices_groups=devices_groups,
        from_addr=from_addr,
        to_addrs=recipients,
        window_label=window_label,
        park_stats=park_stats,
    )
    ok, detail = send_email(
        host=smtp_row.get("host") or "",
        port=int(smtp_row.get("port") or 587),
        username=smtp_row.get("username") or "",
        password=password or "",
        use_ssl=bool(smtp_row.get("use_ssl")),
        use_starttls=bool(smtp_row.get("use_starttls")),
        message=msg,
    )
    if not ok:
        logger.warning("Mail digest email failed: %s", detail)
        result["reason"] = "smtp_error"
        result["detail"] = detail
        return result

    sent_ids = [int(e["id"]) for e in filtered]
    _finalize_digest_send(db, sent_ids, slot_key)
    logger.info(
        "Mail digest emailed: devices=%s events=%s marked=%s",
        len(devices_groups),
        len(filtered),
        len(sent_ids),
    )
    result["sent"] = True
    result["skipped"] = False
    result["reason"] = "ok"
    return result


def flush_mail_digest(
    db: "Database",
    smtp_row: dict[str, Any],
    password: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Алиас периодической сводки уведомлений по почте."""
    return flush_inventory_mail_digest(
        db, smtp_row, password, force=force
    )


def send_email(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    use_ssl: bool,
    use_starttls: bool,
    message: EmailMessage,
) -> tuple[bool, str]:
    if not host:
        return False, "Не задан SMTP-хост"
    to_hdr = message.get("To") or ""
    if not to_hdr.strip():
        return False, "Не заданы получатели"

    def _login_and_send(smtp: smtplib.SMTP) -> None:
        if username:
            smtp.login(username, password)
        smtp.send_message(message)

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                host, int(port or 465), context=context, timeout=30
            ) as smtp:
                _login_and_send(smtp)
        else:
            with smtplib.SMTP(host, int(port or 587), timeout=30) as smtp:
                smtp.ehlo()
                if use_starttls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                _login_and_send(smtp)
        return True, "Письмо отправлено"
    except Exception as exc:  # noqa: BLE001 — soft-fail для операторов
        return False, f"SMTP ошибка: {exc}"


def _smtp_ready(smtp_row: dict[str, Any]) -> tuple[Optional[str], list[str]]:
    if not smtp_row.get("enabled"):
        return None, []
    from_addr = (smtp_row.get("from_addr") or "").strip()
    recipients = parse_recipients(smtp_row.get("to_addrs") or "")
    if not from_addr or not recipients:
        return None, []
    return from_addr, recipients


def _dispatch(
    smtp_row: dict[str, Any],
    *,
    password: str,
    message: EmailMessage,
    log_label: str,
) -> None:
    ok, detail = send_email(
        host=smtp_row.get("host") or "",
        port=int(smtp_row.get("port") or 587),
        username=smtp_row.get("username") or "",
        password=password or "",
        use_ssl=bool(smtp_row.get("use_ssl")),
        use_starttls=bool(smtp_row.get("use_starttls")),
        message=message,
    )
    if ok:
        logger.info("Alert emailed (%s)", log_label)
    else:
        logger.warning("Alert email failed (%s): %s", log_label, detail)


def notify_enroll(
    db: "Database",
    smtp_row: dict[str, Any],
    *,
    device_id: str,
    hostname: Optional[str],
) -> None:
    """Поставить событие enroll в очередь digest (soft-fail)."""
    try:
        host = hostname or device_id
        db.insert_device_event(
            device_id,
            "device_enrolled",
            f"Зарегистрировано новое устройство: {host}",
            detail={"hostname": hostname},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Enqueue enroll event failed for %s", device_id)


def notify_device_back_online(
    db: "Database",
    smtp_row: dict[str, Any],
    *,
    device_id: str,
    hostname: Optional[str],
) -> None:
    """Событие «снова на связи» после stale (очередь digest)."""
    try:
        host = hostname or device_id
        db.insert_device_event(
            device_id,
            "device_back_online",
            "Устройство снова вышло на связь",
            detail={"hostname": hostname, "summary_host": host},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Enqueue back-online event failed for %s", device_id)


def notify_stale_device(
    db: "Database",
    smtp_row: dict[str, Any],
    *,
    device_id: str,
    hostname: Optional[str],
    last_seen_at: Optional[str],
) -> None:
    """Поставить событие stale в очередь digest (soft-fail)."""
    try:
        host = hostname or device_id
        db.insert_device_event(
            device_id,
            "device_stale",
            f"Устройство перестало присылать heartbeat: {host}",
            detail={"hostname": hostname, "last_seen_at": last_seen_at},
        )
    except Exception:  # noqa: BLE001
        logger.exception("Enqueue stale event failed for %s", device_id)
