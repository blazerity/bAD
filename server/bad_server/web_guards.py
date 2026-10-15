"""CSRF cookie issuance + APIRoute CSRF check; must_change lives in auth.require_web_user."""

from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware

from .csrf import (
    CSRF_COOKIE,
    CSRF_FIELD,
    csrf_cookie_needs_set,
    ensure_request_csrf,
    get_request_csrf,
    set_csrf_cookie,
    validate_csrf,
)

_CSRF_SKIP_PREFIXES = ("/v1/", "/static/")


def _csrf_forbidden() -> HTMLResponse:
    return HTMLResponse(
        "<!DOCTYPE html><html lang='ru'><body>"
        "<h1>Ошибка CSRF</h1>"
        "<p>Запрос отклонён. Обновите страницу и повторите.</p>"
        "<p><a href='/'>На главную</a></p>"
        "</body></html>",
        status_code=403,
    )


class CsrfCookieMiddleware(BaseHTTPMiddleware):
    """Issue/refresh bad_csrf cookie on HTML responses (does not read body)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/v1/"):
            ensure_request_csrf(request)
        response = await call_next(request)
        if not path.startswith("/v1/"):
            token = get_request_csrf(request)
            if token and (csrf_cookie_needs_set(request) or CSRF_COOKIE not in request.cookies):
                set_csrf_cookie(response, token)
        return response


class CsrfAwareRoute(APIRoute):
    """Validate csrf_token on POST for web router handlers (SEC-010)."""

    def get_route_handler(self) -> Callable:
        original = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            path = request.url.path
            if (
                request.method == "POST"
                and not any(path.startswith(p) for p in _CSRF_SKIP_PREFIXES)
            ):
                form = await request.form()
                form_token = form.get(CSRF_FIELD)
                cookie_token = request.cookies.get(CSRF_COOKIE)
                if not validate_csrf(
                    cookie_token,
                    str(form_token) if form_token is not None else "",
                ):
                    return _csrf_forbidden()
            return await original(request)

        return custom_handler
