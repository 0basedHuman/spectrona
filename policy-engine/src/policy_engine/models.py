from dataclasses import dataclass, field
from typing import Any, Dict, List


ACTIONS = {"allow", "deny", "redact", "require_approval"}


@dataclass(frozen=True)
class PolicyContext:
    route: str
    provider_type: str
    model: str = "unknown"
    client: str = "unknown"
    dlp_findings_count: int = 0
    filesystem_risk: bool = False
    shell_risk: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class Decision:
    action: str
    rule_id: str = "default"
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.action in {"allow", "redact"}


@dataclass(frozen=True)
class PolicyRule:
    id: str
    action: str
    match: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class Policy:
    default_action: str = "allow"
    rules: List[PolicyRule] = field(default_factory=list)
