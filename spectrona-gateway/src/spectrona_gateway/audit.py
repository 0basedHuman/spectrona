"""
Local append-only JSONL audit log.
All values are DLP-redacted before writing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .dlp import redact_text


def _log_path() -> Path:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    return config.LOG_DIR / "audit.jsonl"


def log_event(
    route: str,
    provider_type: str,
    model: str,
    estimated_input_chars: int,
    dlp_findings_count: int,
    action: str,
    client: str = "",
    policy_action: str = "",
    policy_rule_id: str = "",
    policy_reason: str = "",
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": route,
        "provider_type": provider_type,
        "model": redact_text(model),
        "estimated_input_chars": estimated_input_chars,
        "dlp_findings_count": dlp_findings_count,
        "action": action,
    }
    if client:
        event["client"] = redact_text(client)
    if policy_action:
        event["policy_action"] = policy_action
    if policy_rule_id:
        event["policy_rule_id"] = redact_text(policy_rule_id)
    if policy_reason:
        event["policy_reason"] = redact_text(policy_reason)
    with open(_log_path(), "a") as f:
        f.write(json.dumps(event) + "\n")
