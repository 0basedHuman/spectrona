import sys
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

import httpx

from .. import config


_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

_LOCAL_FALLBACK_STATUS_CODES = {502, 503, 504}


class PassthroughConfigError(RuntimeError):
    pass


def _copy_response_headers(headers: Mapping[str, str]) -> dict:
    copied = {}
    for key, value in headers.items():
        if key.lower() not in _HOP_BY_HOP_HEADERS:
            copied[key] = value
    return copied


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _openai_headers(incoming: Mapping[str, str]) -> dict:
    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise PassthroughConfigError("OpenAI passthrough requires SPECTRONA_OPENAI_API_KEY or OPENAI_API_KEY")
    return {
        "authorization": f"Bearer {api_key}",
        "content-type": incoming.get("content-type", "application/json"),
    }


def _anthropic_headers(incoming: Mapping[str, str]) -> dict:
    api_key = config.ANTHROPIC_API_KEY
    if not api_key:
        raise PassthroughConfigError("Anthropic passthrough requires SPECTRONA_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY")
    return {
        "x-api-key": api_key,
        "anthropic-version": incoming.get("anthropic-version", config.ANTHROPIC_VERSION),
        "content-type": incoming.get("content-type", "application/json"),
    }


def _local_headers(incoming: Mapping[str, str]) -> dict:
    headers = {
        "content-type": incoming.get("content-type", "application/json"),
    }
    if config.LOCAL_API_KEY:
        headers["authorization"] = f"Bearer {config.LOCAL_API_KEY}"
    return headers


async def forward_openai(path: str, body: bytes, incoming_headers: Mapping[str, str]) -> httpx.Response:
    url = _join_url(config.OPENAI_BASE_URL, path)
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await client.post(url, content=body, headers=_openai_headers(incoming_headers))


async def forward_anthropic(path: str, body: bytes, incoming_headers: Mapping[str, str]) -> httpx.Response:
    url = _join_url(config.ANTHROPIC_BASE_URL, path)
    async with httpx.AsyncClient(timeout=60.0) as client:
        return await client.post(url, content=body, headers=_anthropic_headers(incoming_headers))


async def forward_local(path: str, body: bytes, incoming_headers: Mapping[str, str]) -> httpx.Response:
    candidates = _local_forward_base_urls()
    last_error = None
    last_response = None
    async with httpx.AsyncClient(timeout=60.0) as client:
        for index, base_url in enumerate(candidates):
            try:
                response = await client.post(
                    _join_url(base_url, path),
                    content=body,
                    headers=_local_headers(incoming_headers),
                )
            except httpx.RequestError as exc:
                last_error = exc
                continue

            response.extensions["spectrona_local_base_url"] = base_url
            response.extensions["spectrona_local_fallback"] = index > 0
            response.headers["x-spectrona-local-fallback"] = "true" if index > 0 else "false"
            if response.status_code not in _LOCAL_FALLBACK_STATUS_CODES:
                return response
            last_response = response

        if last_response is not None:
            return last_response
        if last_error is not None:
            raise last_error
    raise PassthroughConfigError("local passthrough has no configured endpoint")


def response_headers(response: httpx.Response) -> dict:
    return _copy_response_headers(response.headers)


async def _check_provider(
    name: str,
    base_url: str,
    health_path: str,
    headers: dict,
    live: bool,
    requires_api_key: bool = True,
) -> dict:
    result = {
        "provider": name,
        "base_url": base_url,
        "health_path": health_path,
        "api_key_required": requires_api_key,
        "api_key_configured": bool(headers.get("authorization") or headers.get("x-api-key")),
        "live_checked": live,
        "reachable": False,
        "status": "configured",
    }
    if requires_api_key and not result["api_key_configured"]:
        result["status"] = "missing_api_key"
        return result
    if not live:
        return result

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(_join_url(base_url, health_path), headers=headers)
    except httpx.RequestError as exc:
        result["status"] = "unreachable"
        result["error"] = str(exc)
        return result

    result["reachable"] = True
    result["status_code"] = response.status_code
    if response.status_code == 200:
        result["status"] = "ok"
    elif response.status_code in (401, 403):
        result["status"] = "auth_error"
    else:
        result["status"] = "upstream_error"
    return result


async def check_provider_health(live: bool = False) -> dict:
    openai_headers = {}
    if config.OPENAI_API_KEY:
        openai_headers["authorization"] = f"Bearer {config.OPENAI_API_KEY}"

    anthropic_headers = {}
    if config.ANTHROPIC_API_KEY:
        anthropic_headers["x-api-key"] = config.ANTHROPIC_API_KEY
        anthropic_headers["anthropic-version"] = config.ANTHROPIC_VERSION

    local_headers = {}
    if config.LOCAL_API_KEY:
        local_headers["authorization"] = f"Bearer {config.LOCAL_API_KEY}"

    openai = await _check_provider(
        "openai",
        config.OPENAI_BASE_URL,
        config.OPENAI_HEALTH_PATH,
        openai_headers,
        live,
    )
    anthropic = await _check_provider(
        "anthropic",
        config.ANTHROPIC_BASE_URL,
        config.ANTHROPIC_HEALTH_PATH,
        anthropic_headers,
        live,
    )
    local = await _check_provider(
        "local",
        config.LOCAL_BASE_URL,
        config.LOCAL_HEALTH_PATH,
        local_headers,
        live,
        requires_api_key=False,
    )
    return {
        "live_checked": live,
        "providers": {
            "openai": openai,
            "anthropic": anthropic,
            "local": local,
        },
        "local_runtimes": _local_runtime_health(live),
    }


def _local_runtime_health(live: bool) -> dict:
    try:
        _ensure_cli_importable()
        from spectrona_cli.local_llms import discover_local_llms, local_llm_summary

        statuses = discover_local_llms(
            configured_base_url=config.LOCAL_BASE_URL,
            configured_provider=config.LOCAL_PROVIDER,
            configured_fallbacks=config.LOCAL_FALLBACKS,
            live=live,
        )
        return {
            "live_checked": live,
            "summary": local_llm_summary(statuses),
            "runtimes": [status.to_dict() for status in statuses],
        }
    except Exception as exc:
        return {
            "live_checked": live,
            "summary": {
                "total": 0,
                "configured": 0,
                "reachable": 0,
                "ok": 0,
                "unreachable": 0,
                "fallback": 0,
                "live_checked": live,
            },
            "runtimes": [],
            "error": _redact_text(str(exc)),
        }


def _ensure_cli_importable() -> None:
    try:
        import spectrona_cli  # noqa: F401
        return
    except ImportError:
        repo_root = Path(__file__).resolve().parents[4]
        cli_src = repo_root / "spectrona-cli" / "src"
        if cli_src.exists() and str(cli_src) not in sys.path:
            sys.path.insert(0, str(cli_src))


def _local_forward_base_urls() -> list[str]:
    bases = [_normalize_url(config.LOCAL_BASE_URL)]
    try:
        _ensure_cli_importable()
        from spectrona_cli.local_llms import local_fallback_base_urls

        fallback_bases = local_fallback_base_urls(config.LOCAL_FALLBACKS)
    except Exception:
        fallback_bases = [
            _normalize_url(item)
            for item in config.LOCAL_FALLBACKS.replace("\n", ",").split(",")
            if item.strip().startswith(("http://", "https://")) and _is_local_base_url(item)
        ]

    for base_url in fallback_bases:
        normalized = _normalize_url(base_url)
        if normalized and normalized not in bases:
            bases.append(normalized)
    return bases


def _normalize_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _is_local_base_url(value: str) -> bool:
    try:
        parsed = urlparse(_normalize_url(value))
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    if host.startswith("127."):
        return True
    if host.startswith("10.") or host.startswith("192.168."):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) >= 2 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return host.endswith(".local")


def _redact_text(value: str) -> str:
    text = str(value)
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, "~")
    for marker in ("sk-", "ghp_", "github_pat_", "xoxb-", "xoxp-"):
        idx = text.find(marker)
        while idx != -1:
            end = idx
            while end < len(text) and text[end] not in " \t\r\n'\"`":
                end += 1
            token = text[idx:end]
            if len(token) > len(marker):
                text = text.replace(token, marker + "[REDACTED_SECRET]")
            idx = text.find(marker, idx + len(marker))
    return text
