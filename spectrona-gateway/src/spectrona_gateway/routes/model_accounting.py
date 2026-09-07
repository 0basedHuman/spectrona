import time

from ..events.store import record_model_event
from ..events.tokens import usage_from_response, zero_usage


def elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def record_call_event(
    route: str,
    provider_type: str,
    model: str,
    client: str,
    project_path: str,
    action: str,
    policy_action: str,
    policy_rule_id: str,
    dlp_findings_count: int,
    estimated_input_chars: int,
    forwarded_input_chars: int,
    status_code: int,
    response_content: bytes,
    started_at: float,
) -> None:
    if status_code >= 400:
        usage = zero_usage()
    else:
        usage = usage_from_response(
            provider_type=provider_type,
            request_chars=forwarded_input_chars,
            response_content=response_content,
            estimate_when_missing=True,
        )

    record_model_event(
        route=route,
        provider_type=provider_type,
        model=model,
        client=client,
        project_path=project_path,
        action=action,
        policy_action=policy_action,
        policy_rule_id=policy_rule_id,
        dlp_findings_count=dlp_findings_count,
        estimated_input_chars=estimated_input_chars,
        request_tokens=usage["request_tokens"],
        response_tokens=usage["response_tokens"],
        total_tokens=usage["total_tokens"],
        latency_ms=elapsed_ms(started_at),
        status_code=status_code,
    )
