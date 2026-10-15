"""SMTP helpers for operator alerts (soft-fail on misconfig)."""

from __future__ import annotations

import json
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Optional

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
    }
)

# Toggle keys stored in smtp_settings.notify_json (defaults documented in UI).
DEFAULT_NOTIFY: dict[str, bool] = {
    "hardware": True,  # RAM / CPU / disks / serial / model
    "stale": True,  # device went silent
    "enroll": True,  # new device enrolled
    "hostname": False,  # hostname change
    "domain": False,  # domain change
}

NOTIFY_LABELS_RU: dict[str, str] = {
    "hardware": "Изменение железа (ОЗУ, CPU, диски, serial/model)",
    "stale": "Устройство перестало отвечать (устарело)",
    "enroll": "Новое устройство зарегистрировано",
    "hostname": "Смена hostname",
    "domain": "Смена domain",
}


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


def build_inventory_events_email(
    *,
    device_id: str,
    hostname: Optional[str],
    events: list[dict[str, Any]],
    from_addr: str,
    to_addrs: list[str],
) -> EmailMessage:
    host = hostname or device_id
    subject = f"bAD: изменения — {host}"
    lines = [
        f"Устройство: {host}",
        f"device_id: {device_id}",
        "",
        "События:",
        "",
    ]
    for ev in events:
        lines.append(f"• [{ev.get('type')}] {ev.get('summary')}")
    return build_alert_email(
        subject=subject, body_lines=lines, from_addr=from_addr, to_addrs=to_addrs
    )


# Back-compat alias used by settings test form.
build_hardware_email = build_inventory_events_email


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
    except Exception as exc:  # noqa: BLE001 — soft-fail for operators
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


def notify_inventory_events(
    smtp_row: dict[str, Any],
    *,
    password: str,
    device_id: str,
    hostname: Optional[str],
    events: list[dict[str, Any]],
) -> None:
    """Best-effort notify for inventory diffs. Never raises."""
    from_addr, recipients = _smtp_ready(smtp_row)
    if not from_addr:
        return
    flags = parse_notify_flags(smtp_row.get("notify_json"))
    selected = filter_events_for_mail(events, flags)
    if not selected:
        return
    msg = build_inventory_events_email(
        device_id=device_id,
        hostname=hostname,
        events=selected,
        from_addr=from_addr,
        to_addrs=recipients,
    )
    _dispatch(smtp_row, password=password, message=msg, log_label=device_id)


def notify_enroll(
    smtp_row: dict[str, Any],
    *,
    password: str,
    device_id: str,
    hostname: Optional[str],
) -> None:
    from_addr, recipients = _smtp_ready(smtp_row)
    if not from_addr:
        return
    flags = parse_notify_flags(smtp_row.get("notify_json"))
    if not flags.get("enroll"):
        return
    host = hostname or device_id
    msg = build_alert_email(
        subject=f"bAD: новое устройство — {host}",
        body_lines=[
            "Зарегистрировано новое устройство.",
            f"Имя узла: {host}",
            f"device_id: {device_id}",
        ],
        from_addr=from_addr,
        to_addrs=recipients,
    )
    _dispatch(smtp_row, password=password, message=msg, log_label=f"enroll:{device_id}")


def notify_stale_device(
    smtp_row: dict[str, Any],
    *,
    password: str,
    device_id: str,
    hostname: Optional[str],
    last_seen_at: Optional[str],
) -> None:
    from_addr, recipients = _smtp_ready(smtp_row)
    if not from_addr:
        return
    flags = parse_notify_flags(smtp_row.get("notify_json"))
    if not flags.get("stale"):
        return
    host = hostname or device_id
    msg = build_alert_email(
        subject=f"bAD: устройство устарело — {host}",
        body_lines=[
            "Устройство перестало присылать heartbeat.",
            f"Имя узла: {host}",
            f"device_id: {device_id}",
            f"Последний контакт: {last_seen_at or '—'}",
        ],
        from_addr=from_addr,
        to_addrs=recipients,
    )
    _dispatch(smtp_row, password=password, message=msg, log_label=f"stale:{device_id}")
