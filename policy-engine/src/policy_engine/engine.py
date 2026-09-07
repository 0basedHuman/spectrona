from fnmatch import fnmatch
from typing import Any

from .models import ACTIONS, Decision, Policy, PolicyContext, PolicyRule


class PolicyEngine:
    def __init__(self, policy: Policy):
        if policy.default_action not in ACTIONS:
            raise ValueError(f"Unsupported default policy action: {policy.default_action}")
        self.policy = policy

    def evaluate(self, context: PolicyContext) -> Decision:
        for rule in self.policy.rules:
            if not rule.enabled:
                continue
            if rule.action not in ACTIONS:
                raise ValueError(f"Unsupported policy action: {rule.action}")
            if self._matches(rule, context):
                return Decision(action=rule.action, rule_id=rule.id, reason=rule.reason)
        return Decision(action=self.policy.default_action, rule_id="default", reason="No policy rule matched.")

    def _matches(self, rule: PolicyRule, context: PolicyContext) -> bool:
        for key, expected in rule.match.items():
            if not self._match_value(key, expected, context):
                return False
        return True

    def _match_value(self, key: str, expected: Any, context: PolicyContext) -> bool:
        if key in {"route", "provider_type", "model", "client", "app"}:
            actual = getattr(context, "client" if key == "app" else key)
            return _match_string(actual, expected)
        if key == "dlp_findings_min":
            return context.dlp_findings_count >= int(expected)
        if key == "dlp_findings_count":
            return context.dlp_findings_count == int(expected)
        if key == "filesystem_risk":
            return context.filesystem_risk is _to_bool(expected)
        if key == "shell_risk":
            return context.shell_risk is _to_bool(expected)
        return False


def _match_string(actual: str, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_match_string(actual, item) for item in expected)
    expected_text = str(expected)
    return fnmatch(actual, expected_text)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
