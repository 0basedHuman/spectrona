import json
from math import ceil
from typing import Dict


def estimate_tokens_from_chars(chars: int) -> int:
    if chars <= 0:
        return 0
    return max(1, ceil(chars / 4))


def usage_from_response(
    provider_type: str,
    request_chars: int,
    response_content: bytes,
    estimate_when_missing: bool = True,
) -> Dict[str, int]:
    data = _decode_json(response_content)
    usage = data.get("usage", {}) if isinstance(data, dict) else {}

    if provider_type in {"openai", "local"}:
        request_tokens = _int_value(usage.get("prompt_tokens"))
        response_tokens = _int_value(usage.get("completion_tokens"))
        total_tokens = _int_value(usage.get("total_tokens"))
    elif provider_type == "anthropic":
        request_tokens = _int_value(usage.get("input_tokens"))
        response_tokens = _int_value(usage.get("output_tokens"))
        total_tokens = request_tokens + response_tokens
    else:
        request_tokens = 0
        response_tokens = 0
        total_tokens = 0

    if total_tokens > 0:
        if request_tokens == 0 and response_tokens == 0:
            request_tokens = min(total_tokens, estimate_tokens_from_chars(request_chars))
            response_tokens = max(0, total_tokens - request_tokens)
        return {
            "request_tokens": request_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total_tokens,
        }

    if not estimate_when_missing:
        return {"request_tokens": 0, "response_tokens": 0, "total_tokens": 0}

    request_tokens = estimate_tokens_from_chars(request_chars)
    response_tokens = estimate_tokens_from_chars(len(response_content))
    return {
        "request_tokens": request_tokens,
        "response_tokens": response_tokens,
        "total_tokens": request_tokens + response_tokens,
    }


def zero_usage() -> Dict[str, int]:
    return {"request_tokens": 0, "response_tokens": 0, "total_tokens": 0}


def _decode_json(content: bytes) -> dict:
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _int_value(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0
