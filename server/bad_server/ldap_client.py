from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ldap3 import ALL, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars


@dataclass
class LdapSettingsView:
    enabled: bool = False
    host: str = ""
    port: int = 389
    use_ssl: bool = False
    start_tls: bool = False
    bind_dn: str = ""
    bind_password: str = ""
    user_search_base: str = ""
    user_filter_template: str = "(uid={username})"
    display_name_attr: str = "cn"
    default_role: str = "operator"


@dataclass
class LdapAuthResult:
    username: str
    display_name: Optional[str]
    dn: str


def _server(settings: LdapSettingsView) -> Server:
    tls = None
    if settings.use_ssl or settings.start_tls:
        tls = Tls(validate=0)
    return Server(
        settings.host,
        port=int(settings.port or (636 if settings.use_ssl else 389)),
        use_ssl=bool(settings.use_ssl),
        get_info=ALL,
        tls=tls,
    )


def _open_bound(settings: LdapSettingsView, user: Optional[str], password: Optional[str]) -> Connection:
    server = _server(settings)
    conn = Connection(
        server,
        user=user or None,
        password=password or None,
        auto_bind=False,
        raise_exceptions=True,
    )
    conn.open()
    if settings.start_tls and not settings.use_ssl:
        conn.start_tls()
    if not conn.bind():
        raise LDAPException(f"Bind failed: {conn.result}")
    return conn


def test_connection(settings: LdapSettingsView) -> tuple[bool, str]:
    """Bind with the service account. Returns (ok, message)."""
    if not settings.host:
        return False, "Укажите хост"
    try:
        conn = _open_bound(settings, settings.bind_dn or None, settings.bind_password or None)
        conn.unbind()
        return True, "Соединение и bind успешны"
    except LDAPException as exc:
        return False, f"Ошибка LDAP: {exc}"
    except Exception as exc:  # noqa: BLE001 — surface to operator UI
        return False, f"Ошибка: {exc}"


def authenticate_user(
    settings: LdapSettingsView, username: str, password: str
) -> Optional[LdapAuthResult]:
    """Search for user with service bind, then bind as that user to verify password."""
    if not settings.enabled or not settings.host or not username or not password:
        return None
    template = settings.user_filter_template or ""
    if "{username}" not in template:
        return None

    filter_str = template.replace("{username}", escape_filter_chars(username))
    try:
        svc = _open_bound(settings, settings.bind_dn or None, settings.bind_password or None)
        try:
            svc.search(
                search_base=settings.user_search_base,
                search_filter=filter_str,
                attributes=[settings.display_name_attr or "cn"],
            )
            if not svc.entries:
                return None
            entry = svc.entries[0]
            user_dn = entry.entry_dn
            display = None
            attr = settings.display_name_attr or "cn"
            if attr in entry and entry[attr].value:
                val = entry[attr].value
                display = val if isinstance(val, str) else str(val)
        finally:
            svc.unbind()

        user_conn = _open_bound(settings, user_dn, password)
        user_conn.unbind()
        return LdapAuthResult(username=username, display_name=display, dn=user_dn)
    except LDAPException:
        return None
    except Exception:
        return None


def settings_from_row(row: dict[str, Any], bind_password: str = "") -> LdapSettingsView:
    return LdapSettingsView(
        enabled=bool(row.get("enabled")),
        host=row.get("host") or "",
        port=int(row.get("port") or 389),
        use_ssl=bool(row.get("use_ssl")),
        start_tls=bool(row.get("start_tls")),
        bind_dn=row.get("bind_dn") or "",
        bind_password=bind_password,
        user_search_base=row.get("user_search_base") or "",
        user_filter_template=row.get("user_filter_template") or "(uid={username})",
        display_name_attr=row.get("display_name_attr") or "cn",
        default_role=row.get("default_role") or "operator",
    )
