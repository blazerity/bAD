from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "bad_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 часов
SESSION_SALT = "bad-web-session-v1"


@dataclass
class WebUser:
    username: str
    role: str
    source: str  # local | ldap
    must_change_password: bool = False
    display_name: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "u": self.username,
            "r": self.role,
            "s": self.source,
            "mcp": bool(self.must_change_password),
            "dn": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebUser":
        return cls(
            username=str(data.get("u") or ""),
            role=str(data.get("r") or "operator"),
            source=str(data.get("s") or "local"),
            must_change_password=bool(data.get("mcp")),
            display_name=data.get("dn"),
        )


def dump_session(secret: str, user: WebUser) -> str:
    ser = URLSafeTimedSerializer(secret, salt=SESSION_SALT)
    return ser.dumps(user.to_dict())


def load_session(secret: str, token: Optional[str]) -> Optional[WebUser]:
    if not token or not secret:
        return None
    ser = URLSafeTimedSerializer(secret, salt=SESSION_SALT)
    try:
        data = ser.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired, Exception):
        return None
    if not isinstance(data, dict) or not data.get("u"):
        return None
    return WebUser.from_dict(data)
