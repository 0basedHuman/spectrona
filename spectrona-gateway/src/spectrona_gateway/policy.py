from dataclasses import dataclass
from typing import Mapping

from policy_engine import Decision, PolicyContext, PolicyEngine, load_policy

from . import config
from .dlp import findings_count, redact_text


@dataclass(frozen=True)
class GatewayPolicyResult:
    decision: Decision
    client: str
    body_bytes: bytes
    body_str: str
    dry_run: bool = False

    @property
    def blocked(self) -> bool:
        return not self.dry_run and self.decision.action in {"deny", "require_approval"}

    @property
    def policy_action(self) -> str:
        if self.dry_run and self.decision.action != "allow":
            return "dry_run_" + self.decision.action
        return self.decision.action

    def audit_action(self, fallback: str) -> str:
        if self.dry_run:
            if self.decision.action == "deny":
                return "would_block_then_" + fallback
            if self.decision.action == "require_approval":
                return "would_require_approval_then_" + fallback
            if self.decision.action == "redact":
                return "would_redact_then_" + fallback
            return fallback
        if self.decision.action == "deny":
            return "blocked"
        if self.decision.action == "require_approval":
            return "approval_required"
        if self.decision.action == "redact":
            return "redacted_then_" + fallback
        return fallback

    def error_payload(self) -> dict:
        if self.decision.action == "require_approval":
            error_type = "policy_approval_required"
            message = "Spectrona policy requires approval before this request can continue."
        else:
            error_type = "policy_denied"
            message = "Spectrona policy blocked this request."
        return {
            "error": {
                "type": error_type,
                "message": message,
                "policy_action": self.decision.action,
                "policy_rule_id": redact_text(self.decision.rule_id),
                "policy_reason": redact_text(self.decision.reason),
            }
        }


@dataclass(frozen=True)
class GatewayResponsePolicyResult:
    decision: Decision
    client: str
    content_bytes: bytes
    content_str: str
    dlp_findings_count: int
    dry_run: bool = False

    @property
    def blocked(self) -> bool:
        return not self.dry_run and self.decision.action in {"deny", "require_approval"}

    @property
    def policy_action(self) -> str:
        if self.dry_run and self.decision.action != "allow":
            return "dry_run_" + self.decision.action
        return self.decision.action

    def error_payload(self) -> dict:
        if self.decision.action == "require_approval":
            error_type = "policy_response_approval_required"
            message = "Spectrona policy requires approval before this response can be returned."
        else:
            error_type = "policy_response_denied"
            message = "Spectrona policy blocked this response."
        return {
            "error": {
                "type": error_type,
                "message": message,
                "policy_action": self.decision.action,
                "policy_rule_id": redact_text(self.decision.rule_id),
                "policy_reason": redact_text(self.decision.reason),
            }
        }


def evaluate_request(
    route: str,
    provider_type: str,
    model: str,
    body_bytes: bytes,
    body_str: str,
    headers: Mapping[str, str],
    dlp_findings_count: int,
) -> GatewayPolicyResult:
    client = _client(headers)
    context = PolicyContext(
        route=route,
        provider_type=provider_type,
        model=model,
        client=client,
        dlp_findings_count=dlp_findings_count,
        filesystem_risk=_header_bool(headers, "x-spectrona-filesystem-risk"),
        shell_risk=_header_bool(headers, "x-spectrona-shell-risk"),
    )

    try:
        decision = PolicyEngine(load_policy(config.POLICY_PATH)).evaluate(context)
    except Exception as exc:
        decision = Decision(
            action="deny",
            rule_id="policy-load-error",
            reason=f"Policy could not be loaded: {exc}",
        )

    dry_run = config.POLICY_DRY_RUN
    if decision.action == "redact" and not dry_run:
        redacted = redact_text(body_str)
        return GatewayPolicyResult(
            decision=decision,
            client=client,
            body_bytes=redacted.encode("utf-8"),
            body_str=redacted,
            dry_run=False,
        )

    return GatewayPolicyResult(
        decision=decision,
        client=client,
        body_bytes=body_bytes,
        body_str=body_str,
        dry_run=dry_run,
    )


def evaluate_response(
    route: str,
    provider_type: str,
    model: str,
    client: str,
    content_bytes: bytes,
) -> GatewayResponsePolicyResult:
    content_str = content_bytes.decode("utf-8", errors="replace")
    dlp_hits = findings_count(content_str)
    context = PolicyContext(
        route=route,
        provider_type=provider_type,
        model=model,
        client=client,
        dlp_findings_count=dlp_hits,
        filesystem_risk=False,
        shell_risk=False,
    )

    try:
        decision = PolicyEngine(load_policy(config.POLICY_PATH)).evaluate(context)
    except Exception as exc:
        decision = Decision(
            action="deny",
            rule_id="policy-load-error",
            reason=f"Policy could not be loaded: {exc}",
        )

    dry_run = config.POLICY_DRY_RUN
    if decision.action == "redact" and not dry_run:
        redacted = redact_text(content_str)
        return GatewayResponsePolicyResult(
            decision=decision,
            client=client,
            content_bytes=redacted.encode("utf-8"),
            content_str=redacted,
            dlp_findings_count=dlp_hits,
            dry_run=False,
        )

    return GatewayResponsePolicyResult(
        decision=decision,
        client=client,
        content_bytes=content_bytes,
        content_str=content_str,
        dlp_findings_count=dlp_hits,
        dry_run=dry_run,
    )


def _client(headers: Mapping[str, str]) -> str:
    return (
        headers.get("x-spectrona-client")
        or headers.get("x-client-name")
        or headers.get("user-agent")
        or "unknown"
    )


def _header_bool(headers: Mapping[str, str], name: str) -> bool:
    return headers.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
