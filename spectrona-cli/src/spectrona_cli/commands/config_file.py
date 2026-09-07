import os
import secrets
from pathlib import Path
from typing import Dict


DEFAULT_CONFIG = {
    "gateway": {
        "host": "127.0.0.1",
        "port": "8787",
        "auth_token": "",
        "mock_mode": "true",
        "policy_dry_run": "false",
        "memory_capture": "true",
        "memory_injection": "false",
        "memory_max_attachments": "5",
        "memory_stale_after_days": "30",
        "memory_raw_storage": "redacted",
        "memory_plaintext_allowed": "false",
    },
    "paths": {
        "log_dir": "~/.spectrona/logs",
        "db_path": "~/.spectrona/memory.db",
        "policy_path": "~/.spectrona/policy.yaml",
        "memory_encryption_key_path": "~/.spectrona/memory.key",
        "mcp_config_path": "",
        "repo_root": "",
    },
    "providers": {
        "openai_base_url": "https://api.openai.com/v1",
        "openai_health_path": "/models",
        "openai_api_key": "",
        "anthropic_base_url": "https://api.anthropic.com/v1",
        "anthropic_health_path": "/models",
        "anthropic_api_key": "",
        "anthropic_version": "2023-06-01",
        "local_provider": "openai-compatible",
        "local_base_url": "http://127.0.0.1:11434/v1",
        "local_health_path": "/models",
        "local_fallbacks": "",
        "local_api_key": "",
    },
}

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


def spectrona_home() -> Path:
    return Path(os.getenv("SPECTRONA_HOME", str(Path.home() / ".spectrona"))).expanduser()


def config_path() -> Path:
    override = os.getenv("SPECTRONA_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return spectrona_home() / "config.yaml"


def policy_path() -> Path:
    override = os.getenv("SPECTRONA_POLICY_PATH")
    if override:
        return Path(override).expanduser()
    return spectrona_home() / "policy.yaml"


def _quote(value: str) -> str:
    if value == "":
        return '""'
    return value


def _gateway_auth_token() -> str:
    return secrets.token_urlsafe(32)


def _chmod_user_only(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def default_config_text() -> str:
    lines = [
        "# Spectrona local configuration",
        "# Environment variables override these values at runtime.",
        "",
    ]
    for section, values in DEFAULT_CONFIG.items():
        lines.append(f"{section}:")
        for key, value in values.items():
            if section == "gateway" and key == "auth_token" and not value:
                value = _gateway_auth_token()
            lines.append(f"  {key}: {_quote(value)}")
        lines.append("")
    return "\n".join(lines)


def default_policy_text() -> str:
    return DEFAULT_POLICY_TEXT


def ensure_gateway_auth_token(path: Path = None) -> bool:
    path = path or config_path()
    if not path.exists():
        return False

    lines = path.read_text().splitlines()
    current = None
    gateway_start = None
    gateway_end = len(lines)
    has_token = False
    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped and not raw_line.startswith(" ") and stripped.endswith(":"):
            if current == "gateway" and gateway_end == len(lines):
                gateway_end = index
            current = stripped[:-1]
            if current == "gateway":
                gateway_start = index
            continue
        if current == "gateway" and raw_line.startswith("  ") and ":" in raw_line:
            key, value = raw_line.strip().split(":", 1)
            if key.strip() == "auth_token":
                has_token = bool(value.strip().strip('"').strip("'"))

    if gateway_start is None or has_token:
        _chmod_user_only(path)
        return False

    lines.insert(gateway_end, f"  auth_token: {_gateway_auth_token()}")
    path.write_text("\n".join(lines) + "\n")
    _chmod_user_only(path)
    return True


def read_config(path: Path = None) -> Dict[str, Dict[str, str]]:
    path = path or config_path()
    if not path.exists():
        return {}

    config: Dict[str, Dict[str, str]] = {}
    current = None
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            config[current] = {}
            continue
        if current and line.startswith("  ") and ":" in line:
            key, value = line.strip().split(":", 1)
            value = value.strip().strip('"').strip("'")
            config[current][key.strip()] = value
    return config
