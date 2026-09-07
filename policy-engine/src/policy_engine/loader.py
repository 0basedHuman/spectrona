import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .defaults import DEFAULT_POLICY_TEXT
from .models import ACTIONS, Policy, PolicyRule


TOP_LEVEL_KEYS = {"version", "default_action", "rules"}
RULE_KEYS = {"id", "action", "enabled", "reason", "match"}
MATCH_KEYS = {
    "route",
    "provider_type",
    "model",
    "client",
    "app",
    "dlp_findings_min",
    "dlp_findings_count",
    "filesystem_risk",
    "shell_risk",
}
STRING_MATCH_KEYS = {"route", "provider_type", "model", "client", "app"}
INTEGER_MATCH_KEYS = {"dlp_findings_min", "dlp_findings_count"}
BOOLEAN_MATCH_KEYS = {"filesystem_risk", "shell_risk"}


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].rstrip()


def _parse_value(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_value(part.strip()) for part in inner.split(",")]
    try:
        return int(value)
    except ValueError:
        return value


def _parse_key_value(line: str) -> tuple[str, Any]:
    key, value = line.split(":", 1)
    return key.strip(), _parse_value(value)


def _parse_rules_yaml(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"rules": []}
    current_rule: Optional[Dict[str, Any]] = None
    section = None

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line)
        if not line.strip():
            continue

        stripped = line.strip()
        if stripped == "rules:":
            section = "rules"
            continue

        if section != "rules":
            if ":" in stripped:
                key, value = _parse_key_value(stripped)
                data[key] = value
            continue

        if stripped.startswith("- "):
            current_rule = {"match": {}}
            data["rules"].append(current_rule)
            item = stripped[2:].strip()
            if item and ":" in item:
                key, value = _parse_key_value(item)
                current_rule[key] = value
            continue

        if current_rule is None or ":" not in stripped:
            continue

        indent = len(line) - len(line.lstrip(" "))
        if stripped == "match:":
            current_rule.setdefault("match", {})
            continue

        key, value = _parse_key_value(stripped)
        if indent >= 6:
            current_rule.setdefault("match", {})[key] = value
        else:
            current_rule[key] = value

    return data


def _rule_from_dict(raw: Dict[str, Any], index: int) -> PolicyRule:
    _validate_rule(raw, index)
    action = str(raw.get("action", "allow"))
    if action not in ACTIONS:
        raise ValueError(f"Unsupported policy action: {action}")
    return PolicyRule(
        id=str(raw.get("id", f"rule-{index}")),
        action=action,
        enabled=bool(raw.get("enabled", True)),
        reason=str(raw.get("reason", "")),
        match=dict(raw.get("match", {})),
    )


def _policy_from_dict(raw: Dict[str, Any]) -> Policy:
    _validate_policy_dict(raw)
    default_action = str(raw.get("default_action", "allow"))
    if default_action not in ACTIONS:
        raise ValueError(f"Unsupported default policy action: {default_action}")
    rules: List[PolicyRule] = []
    for index, item in enumerate(raw.get("rules", []), start=1):
        if isinstance(item, dict):
            rules.append(_rule_from_dict(item, index))
        else:
            raise ValueError(f"Policy rule {index} must be an object")
    return Policy(default_action=default_action, rules=rules)


def _validate_policy_dict(raw: Dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise ValueError("Policy must be an object")
    unknown = sorted(set(raw) - TOP_LEVEL_KEYS)
    if unknown:
        raise ValueError(f"Unknown policy field: {', '.join(unknown)}")
    if "version" in raw and str(raw["version"]) != "1":
        raise ValueError(f"Unsupported policy version: {raw['version']}")
    rules = raw.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("Policy rules must be a list")


def _validate_rule(raw: Dict[str, Any], index: int) -> None:
    unknown = sorted(set(raw) - RULE_KEYS)
    if unknown:
        raise ValueError(f"Unknown field in policy rule {index}: {', '.join(unknown)}")
    rule_id = str(raw.get("id", f"rule-{index}"))
    if not rule_id.strip():
        raise ValueError(f"Policy rule {index} id must not be empty")
    action = str(raw.get("action", "allow"))
    if action not in ACTIONS:
        raise ValueError(f"Unsupported policy action: {action}")
    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"Policy rule {rule_id} enabled must be true or false")
    match = raw.get("match")
    if not isinstance(match, dict) or not match:
        raise ValueError(f"Policy rule {rule_id} must define a non-empty match object")
    _validate_match(rule_id, match)


def _validate_match(rule_id: str, match: Dict[str, Any]) -> None:
    unknown = sorted(set(match) - MATCH_KEYS)
    if unknown:
        raise ValueError(f"Unknown match key in policy rule {rule_id}: {', '.join(unknown)}")
    for key, value in match.items():
        if key in STRING_MATCH_KEYS:
            _validate_string_match(rule_id, key, value)
        elif key in INTEGER_MATCH_KEYS:
            _validate_integer_match(rule_id, key, value)
        elif key in BOOLEAN_MATCH_KEYS:
            _validate_boolean_match(rule_id, key, value)


def _validate_string_match(rule_id: str, key: str, value: Any) -> None:
    if isinstance(value, list):
        if not value:
            raise ValueError(f"Policy rule {rule_id} match {key} list must not be empty")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Policy rule {rule_id} match {key} list values must be non-empty strings")
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Policy rule {rule_id} match {key} must be a non-empty string")


def _validate_integer_match(rule_id: str, key: str, value: Any) -> None:
    if isinstance(value, bool):
        raise ValueError(f"Policy rule {rule_id} match {key} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Policy rule {rule_id} match {key} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"Policy rule {rule_id} match {key} must be non-negative")


def _validate_boolean_match(rule_id: str, key: str, value: Any) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"Policy rule {rule_id} match {key} must be true or false")


def load_policy_text(text: str) -> Policy:
    stripped = text.strip()
    if not stripped:
        return _policy_from_dict({})
    if stripped.startswith("{"):
        return _policy_from_dict(json.loads(stripped))
    return _policy_from_dict(_parse_rules_yaml(stripped))


def load_policy(path: Optional[Union[str, Path]] = None) -> Policy:
    if path is None:
        return load_policy_text(DEFAULT_POLICY_TEXT)
    policy_path = Path(path).expanduser()
    if not policy_path.exists():
        return load_policy_text(DEFAULT_POLICY_TEXT)
    return load_policy_text(policy_path.read_text())
