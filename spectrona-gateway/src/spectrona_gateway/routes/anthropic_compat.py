import json
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from .. import audit, config, policy
from ..dlp import findings_count
from ..memory.runtime import capture_response_memory, prepare_request_memory
from ..providers import passthrough
from .model_accounting import record_call_event
from .response_guard import guard_model_response

router = APIRouter()

_MOCK_RESPONSE = {
    "id": "msg_spectrona_mock",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "[Mock response from Spectrona gateway]"}],
    "model": "claude-sonnet-4-6",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 10},
}


@router.post("/messages")
async def messages(request: Request):
    started_at = time.monotonic()
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8", errors="replace")

    dlp_hits = findings_count(body_str)
    try:
        body = json.loads(body_str)
        model = body.get("model", "unknown")
    except Exception:
        model = "unknown"
    project_path = request.headers.get("x-spectrona-project-path") or request.headers.get("x-spectrona-repo-root") or str(config.REPO_ROOT)

    policy_result = policy.evaluate_request(
        route="/anthropic/v1/messages",
        provider_type="anthropic",
        model=model,
        body_bytes=body_bytes,
        body_str=body_str,
        headers=request.headers,
        dlp_findings_count=dlp_hits,
    )

    audit.log_event(
        route="/anthropic/v1/messages",
        provider_type="anthropic",
        model=model,
        estimated_input_chars=len(body_str),
        dlp_findings_count=dlp_hits,
        action=policy_result.audit_action("mock_response" if config.MOCK_MODE else "passthrough"),
        client=policy_result.client,
        policy_action=policy_result.policy_action,
        policy_rule_id=policy_result.decision.rule_id,
        policy_reason=policy_result.decision.reason,
    )

    action = policy_result.audit_action("mock_response" if config.MOCK_MODE else "passthrough")

    if policy_result.blocked:
        record_call_event(
            route="/anthropic/v1/messages",
            provider_type="anthropic",
            model=model,
            client=policy_result.client,
            project_path=project_path,
            action=action,
            policy_action=policy_result.policy_action,
            policy_rule_id=policy_result.decision.rule_id,
            dlp_findings_count=dlp_hits,
            estimated_input_chars=len(body_str),
            forwarded_input_chars=len(policy_result.body_str),
            status_code=403,
            response_content=b"",
            started_at=started_at,
        )
        return JSONResponse(policy_result.error_payload(), status_code=403)

    memory_result = prepare_request_memory(
        route="/anthropic/v1/messages",
        provider_type="anthropic",
        model=model,
        client=policy_result.client,
        body_bytes=policy_result.body_bytes,
        body_str=policy_result.body_str,
        headers=request.headers,
    )
    body_bytes = memory_result.body_bytes

    if config.MOCK_MODE:
        response = dict(_MOCK_RESPONSE)
        response["model"] = model
        guarded = guard_model_response(
            route="/anthropic/v1/messages",
            provider_type="anthropic",
            model=model,
            client=policy_result.client,
            request_decision=policy_result.decision,
            request_policy_action=policy_result.policy_action,
            request_dlp_findings_count=dlp_hits,
            fallback_action=action,
            status_code=200,
            response_content=json.dumps(response).encode("utf-8"),
        )
        record_call_event(
            route="/anthropic/v1/messages",
            provider_type="anthropic",
            model=model,
            client=policy_result.client,
            project_path=project_path,
            action=guarded.action,
            policy_action=guarded.policy_action,
            policy_rule_id=guarded.policy_rule_id,
            dlp_findings_count=guarded.dlp_findings_count,
            estimated_input_chars=len(body_str),
            forwarded_input_chars=len(memory_result.body_str),
            status_code=guarded.status_code,
            response_content=guarded.content,
            started_at=started_at,
        )
        if guarded.blocked:
            return JSONResponse(guarded.error_payload, status_code=guarded.status_code)
        capture_response_memory(
            route="/anthropic/v1/messages",
            provider_type="anthropic",
            model=model,
            client=policy_result.client,
            headers=request.headers,
            response_content=guarded.content,
        )
        return Response(content=guarded.content, status_code=guarded.status_code, media_type="application/json")

    try:
        upstream = await passthrough.forward_anthropic(
            "messages",
            body_bytes,
            request.headers,
        )
    except passthrough.PassthroughConfigError as exc:
        record_call_event(
            route="/anthropic/v1/messages",
            provider_type="anthropic",
            model=model,
            client=policy_result.client,
            project_path=project_path,
            action="upstream_config_error",
            policy_action=policy_result.policy_action,
            policy_rule_id=policy_result.decision.rule_id,
            dlp_findings_count=dlp_hits,
            estimated_input_chars=len(body_str),
            forwarded_input_chars=len(memory_result.body_str),
            status_code=503,
            response_content=b"",
            started_at=started_at,
        )
        return JSONResponse({"error": str(exc)}, status_code=503)
    except httpx.RequestError as exc:
        record_call_event(
            route="/anthropic/v1/messages",
            provider_type="anthropic",
            model=model,
            client=policy_result.client,
            project_path=project_path,
            action="upstream_request_error",
            policy_action=policy_result.policy_action,
            policy_rule_id=policy_result.decision.rule_id,
            dlp_findings_count=dlp_hits,
            estimated_input_chars=len(body_str),
            forwarded_input_chars=len(memory_result.body_str),
            status_code=502,
            response_content=b"",
            started_at=started_at,
        )
        return JSONResponse({"error": f"Anthropic upstream request failed: {exc}"}, status_code=502)

    guarded = guard_model_response(
        route="/anthropic/v1/messages",
        provider_type="anthropic",
        model=model,
        client=policy_result.client,
        request_decision=policy_result.decision,
        request_policy_action=policy_result.policy_action,
        request_dlp_findings_count=dlp_hits,
        fallback_action=action,
        status_code=upstream.status_code,
        response_content=upstream.content,
    )

    record_call_event(
        route="/anthropic/v1/messages",
        provider_type="anthropic",
        model=model,
        client=policy_result.client,
        project_path=project_path,
        action=guarded.action,
        policy_action=guarded.policy_action,
        policy_rule_id=guarded.policy_rule_id,
        dlp_findings_count=guarded.dlp_findings_count,
        estimated_input_chars=len(body_str),
        forwarded_input_chars=len(memory_result.body_str),
        status_code=guarded.status_code,
        response_content=guarded.content,
        started_at=started_at,
    )

    if guarded.blocked:
        return JSONResponse(guarded.error_payload, status_code=guarded.status_code)

    capture_response_memory(
        route="/anthropic/v1/messages",
        provider_type="anthropic",
        model=model,
        client=policy_result.client,
        headers=request.headers,
        response_content=guarded.content,
    )

    return Response(
        content=guarded.content,
        status_code=guarded.status_code,
        headers=passthrough.response_headers(upstream),
        media_type=upstream.headers.get("content-type", "application/json"),
    )
