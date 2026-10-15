from __future__ import annotations

import ssl
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
    # AD sAMAccountName security-группы, которой разрешён вход (пусто = без ограничения).
    allowed_group: str = ""
    # Opt-in only: disable certificate verification (lab). Default verify (SEC-003).
    tls_insecure: bool = False


@dataclass
class LdapAuthResult:
    username: str
    display_name: Optional[str]
    dn: str


class LdapGroupDenied(Exception):
    """Пользователь аутентифицирован, но не состоит в настроенной группе AD."""

    def __init__(self, group: str) -> None:
        self.group = group
        super().__init__(group)


def _server(settings: LdapSettingsView) -> Server:
    tls = None
    if settings.use_ssl or settings.start_tls:
        validate = ssl.CERT_NONE if settings.tls_insecure else ssl.CERT_REQUIRED
        tls = Tls(validate=validate)
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
    """Bind сервисной учёткой. Возвращает (ok, message)."""
    if not settings.host:
        return False, "Укажите хост"
    try:
        conn = _open_bound(settings, settings.bind_dn or None, settings.bind_password or None)
        conn.unbind()
        return True, "Соединение и bind успешны"
    except LDAPException as exc:
        return False, f"Ошибка LDAP: {exc}"
    except Exception as exc:  # noqa: BLE001 — показать оператору в UI
        return False, f"Ошибка: {exc}"


def _resolve_group_dn(
    conn: Connection, group_sam: str, search_base: str
) -> Optional[str]:
    """Разрешить AD-группу sAMAccountName (или DN) в distinguishedName."""
    group_sam = (group_sam or "").strip()
    if not group_sam:
        return None
    # Если оператор уже вставил DN — использовать как есть.
    if group_sam.lower().startswith("cn=") or ",dc=" in group_sam.lower():
        return group_sam
    filt = (
        f"(&(objectClass=group)"
        f"(sAMAccountName={escape_filter_chars(group_sam)}))"
    )
    bases = [b for b in [search_base, ""] if b is not None]
    # Предпочитать настроенный search base; пустой base — только в крайнем случае.
    seen: set[str] = set()
    for base in bases:
        key = base or "__root__"
        if key in seen:
            continue
        seen.add(key)
        try:
            conn.search(
                search_base=base,
                search_filter=filt,
                attributes=["distinguishedName"],
            )
        except LDAPException:
            continue
        if conn.entries:
            return conn.entries[0].entry_dn
    return None


def _user_in_group(
    conn: Connection, user_dn: str, group_dn: str, search_base: str
) -> bool:
    """True, если user_dn — (возможно вложенный) член group_dn."""
    from ldap3 import BASE

    # LDAP_MATCHING_RULE_IN_CHAIN — вложенное членство в группах AD.
    chain = "1.2.840.113556.1.4.1941"
    filt = f"(member:{chain}:={escape_filter_chars(user_dn)})"
    try:
        conn.search(
            search_base=group_dn,
            search_filter=f"(&(distinguishedName={escape_filter_chars(group_dn)}){filt})",
            search_scope=BASE,
            attributes=["cn"],
        )
        if conn.entries:
            return True
    except LDAPException:
        pass
    # Fallback: прямой memberOf у записи пользователя.
    try:
        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            search_scope=BASE,
            attributes=["memberOf"],
        )
    except LDAPException:
        return False
    if not conn.entries:
        return False
    entry = conn.entries[0]
    if "memberOf" not in entry:
        return False
    values = entry["memberOf"].values if entry["memberOf"].values else []
    group_cf = group_dn.casefold()
    for v in values:
        text = v if isinstance(v, str) else str(v)
        if text.casefold() == group_cf:
            return True
    # Крайний случай: поиск по атрибуту member группы (только прямое членство).
    base = search_base or group_dn
    try:
        conn.search(
            search_base=base,
            search_filter=(
                f"(&(objectClass=group)"
                f"(distinguishedName={escape_filter_chars(group_dn)})"
                f"(member={escape_filter_chars(user_dn)}))"
            ),
            attributes=["cn"],
        )
        return bool(conn.entries)
    except LDAPException:
        return False


def authenticate_user(
    settings: LdapSettingsView, username: str, password: str
) -> Optional[LdapAuthResult]:
    """Найти пользователя через service bind, затем bind от его имени для проверки пароля.

    Если задан ``allowed_group`` (AD sAMAccountName или DN), требуется членство,
    иначе поднимается :class:`LdapGroupDenied`.
    """
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

            allowed = (settings.allowed_group or "").strip()
            if allowed:
                group_dn = _resolve_group_dn(
                    svc, allowed, settings.user_search_base
                )
                if not group_dn:
                    raise LdapGroupDenied(allowed)
                if not _user_in_group(
                    svc, user_dn, group_dn, settings.user_search_base
                ):
                    raise LdapGroupDenied(allowed)
        finally:
            svc.unbind()

        user_conn = _open_bound(settings, user_dn, password)
        user_conn.unbind()
        return LdapAuthResult(username=username, display_name=display, dn=user_dn)
    except LdapGroupDenied:
        raise
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
        allowed_group=(row.get("allowed_group") or "").strip(),
        tls_insecure=bool(row.get("tls_insecure")),
    )
