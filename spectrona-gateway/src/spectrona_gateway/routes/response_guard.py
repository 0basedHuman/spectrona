import json
from dataclasses import dataclass

from .. import audit, policy


@dataclass(frozen=True)
class GuardedModelResponse:
    content: bytes
    status_code: int
    action: str
    policy_action: str
    policy_rule_id: str
    dlp_findings_count: int
    blocked: bool
    error_payload: dict


def guard_model_response(
    route: str,
    provider_type: str,
    model: str,
    client: str,
    request_decision,
    request_policy_action: str,
    request_dlp_findings_count: int,
    fallback_action: str,
    status_code: int,
    response_content: bytes,
) -> GuardedModelResponse:
    response_result = policy.evaluate_response(
        route=route,
        provider_type=provider_type,
        model=model,
        client=client,
        content_bytes=response_content,
    )
    action = _combined_action(fallback_action, response_result.policy_action)
    policy_action = _effective_policy_field(request_policy_action, response_result.policy_action)
    policy_rule_id = _effective_policy_field(request_decision.rule_id, response_result.decision.rule_id)
    total_dlp_findings = max(0, int(request_dlp_findings_count)) + response_result.dlp_findings_count

    if response_result.dlp_findings_count > 0 or response_result.decision.action != "allow":
        audit.log_event(
            route=route,
            provider_type=provider_type,
            model=model,
            estimated_input_chars=0,
            dlp_findings_count=response_result.dlp_findings_count,
            action=action,
            client=client,
            policy_action=response_result.policy_action,
            policy_rule_id=response_result.decision.rule_id,
            policy_reason=response_result.decision.reason,
        )

    if response_result.blocked:
        payload = response_result.error_payload()
        return GuardedModelResponse(
            content=json.dumps(payload).encode("utf-8"),
            status_code=403,
            action=action,
            policy_action=policy_action,
            policy_rule_id=policy_rule_id,
            dlp_findings_count=total_dlp_findings,
            blocked=True,
            error_payload=payload,
        )

    return GuardedModelResponse(
        content=response_result.content_bytes,
        status_code=status_code,
        action=action,
        policy_action=policy_action,
        policy_rule_id=policy_rule_id,
        dlp_findings_count=total_dlp_findings,
        blocked=False,
        error_payload={},
    )


def _combined_action(fallback_action: str, response_policy_action: str) -> str:
    if response_policy_action == "dry_run_deny":
        return "would_response_block_then_" + fallback_action
    if response_policy_action == "dry_run_require_approval":
        return "would_response_require_approval_then_" + fallback_action
    if response_policy_action == "dry_run_redact":
        return "would_response_redact_then_" + fallback_action
    if response_policy_action == "deny":
        return "response_blocked"
    if response_policy_action == "require_approval":
        return "response_approval_required"
    if response_policy_action == "redact":
        if fallback_action.startswith("redacted_then_"):
            return "request_and_response_redacted_then_" + fallback_action[len("redacted_then_"):]
        return "response_redacted_then_" + fallback_action
    return fallback_action


def _effective_policy_field(request_value: str, response_value: str) -> str:
    if response_value and response_value != "allow":
        return response_value
    return request_value
