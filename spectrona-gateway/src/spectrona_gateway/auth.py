from __future__ import annotations

import hmac
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse

from . import config


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
_ALL_INTERFACE_HOSTS = {"0.0.0.0", "::", "[::]"}


async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    host_error = _validate_host_header(request)
    if host_error:
        return _error(400, host_error)

    origin_error = _validate_origin_header(request)
    if origin_error:
        return _error(403, origin_error)

    if not _authorized(request):
        return _error(401, "Missing or invalid Spectrona bearer token")

    return await call_next(request)


def gateway_auth_token() -> str:
    return config.GATEWAY_AUTH_TOKEN


def _authorized(request: Request) -> bool:
    token = gateway_auth_token()
    if not token:
        return False

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        supplied = auth[7:].strip()
        if hmac.compare_digest(supplied, token):
            return True

    if request.url.path.rstrip("/") == "/ui":
        supplied = request.query_params.get("token", "")
        if supplied and hmac.compare_digest(supplied, token):
            return True

    return False


def _validate_host_header(request: Request) -> str:
    host = _host_name(request.headers.get("host", ""))
    if not host:
        return "Missing Host header"
    if host in _ALL_INTERFACE_HOSTS:
        return "Spectrona gateway does not accept all-interface Host headers"
    if _is_allowed_host(host):
        return ""
    return "Host is not allowed for this local gateway"


def _validate_origin_header(request: Request) -> str:
    origin = request.headers.get("origin")
    if not origin:
        return ""
    parsed = urlparse(origin)
    host = _host_name(parsed.netloc)
    if not parsed.scheme or not host:
        return "Origin is invalid"
    if parsed.scheme not in {"http", "https"}:
        return "Origin scheme is not allowed"
    if _is_allowed_host(host):
        return ""
    return "Origin is not allowed for this local gateway"


def _is_allowed_host(host: str) -> bool:
    if host in _LOCAL_HOSTS:
        return True
    if host.startswith("127."):
        return True
    configured = _host_name(config.HOST)
    return bool(configured and configured not in _ALL_INTERFACE_HOSTS and host == configured)


def _host_name(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    if value.startswith("["):
        end = value.find("]")
        return value[: end + 1] if end >= 0 else value
    return value.split(":", 1)[0]


def _error(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status_code)
