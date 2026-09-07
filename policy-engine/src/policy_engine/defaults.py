DEFAULT_POLICY_TEXT = """# Spectrona local runtime policy
# This file is evaluated locally by the Spectrona gateway and future MCP proxy.

version: 1
default_action: allow

rules:
  - id: redact-known-secrets
    action: redact
    enabled: true
    reason: Redact known secret values before provider forwarding.
    match:
      dlp_findings_min: 1

  - id: deny-shell-risk
    action: deny
    enabled: true
    reason: Block shell-risk actions until explicit MCP approvals exist.
    match:
      shell_risk: true

  - id: deny-filesystem-risk
    action: deny
    enabled: true
    reason: Block filesystem-risk actions until project allowlists exist.
    match:
      filesystem_risk: true

  - id: approval-example-high-dlp
    action: require_approval
    enabled: false
    reason: Example only. Require approval when many DLP findings appear.
    match:
      dlp_findings_min: 3
"""
