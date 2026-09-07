from dataclasses import dataclass

from .defaults import DEFAULT_POLICY_TEXT


@dataclass(frozen=True)
class PolicyPreset:
    id: str
    label: str
    description: str
    text: str


RELAXED_POLICY_TEXT = """# Spectrona local runtime policy
# Preset: relaxed

version: 1
default_action: allow

rules:
  - id: redact-known-secrets
    action: redact
    enabled: true
    reason: Redact known secret values before provider forwarding.
    match:
      dlp_findings_min: 1

  - id: observe-shell-risk
    action: deny
    enabled: false
    reason: Disabled in relaxed mode. Shell-risk actions are observed only.
    match:
      shell_risk: true

  - id: observe-filesystem-risk
    action: deny
    enabled: false
    reason: Disabled in relaxed mode. Filesystem-risk actions are observed only.
    match:
      filesystem_risk: true
"""


STRICT_POLICY_TEXT = """# Spectrona local runtime policy
# Preset: strict

version: 1
default_action: allow

rules:
  - id: approval-multiple-secrets
    action: require_approval
    enabled: true
    reason: Require approval when a request or response contains multiple DLP findings.
    match:
      dlp_findings_min: 2

  - id: redact-known-secrets
    action: redact
    enabled: true
    reason: Redact known secret values before provider forwarding.
    match:
      dlp_findings_min: 1

  - id: deny-shell-risk
    action: deny
    enabled: true
    reason: Block shell-risk actions by default.
    match:
      shell_risk: true

  - id: deny-filesystem-risk
    action: deny
    enabled: true
    reason: Block filesystem-risk actions outside approved project roots.
    match:
      filesystem_risk: true

  - id: approval-unknown-client
    action: require_approval
    enabled: true
    reason: Require approval for unclassified clients.
    match:
      client: unknown
"""


_PRESETS = {
    "relaxed": PolicyPreset(
        id="relaxed",
        label="Relaxed",
        description="Redacts secrets while observing shell and filesystem risk.",
        text=RELAXED_POLICY_TEXT,
    ),
    "balanced": PolicyPreset(
        id="balanced",
        label="Balanced",
        description="Redacts secrets and blocks shell or filesystem risk by default.",
        text=DEFAULT_POLICY_TEXT,
    ),
    "strict": PolicyPreset(
        id="strict",
        label="Strict",
        description="Adds approval checks for multiple secrets and unknown clients.",
        text=STRICT_POLICY_TEXT,
    ),
}


def list_policy_presets() -> list[PolicyPreset]:
    return list(_PRESETS.values())


def get_policy_preset(preset_id: str) -> PolicyPreset:
    try:
        return _PRESETS[preset_id]
    except KeyError as exc:
        raise ValueError(f"Unknown policy preset: {preset_id}") from exc
