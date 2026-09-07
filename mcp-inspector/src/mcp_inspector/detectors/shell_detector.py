from typing import Optional

from ..models import Finding

# Tokens indicating shell/command execution capability.
_SHELL_TOKENS = [
    "shell",
    "bash",
    "zsh",
    "terminal",
    "exec",
    "subprocess",
    "run_command",
]

# A command field that IS a shell binary (direct shell invocation).
_SHELL_COMMANDS = frozenset(["bash", "sh", "zsh", "fish", "dash", "pwsh", "powershell"])


def _first_shell_token(text: str) -> Optional[str]:
    lower = text.lower()
    for token in _SHELL_TOKENS:
        if token in lower:
            return token
    return None


def _server_exposes_shell(name: str, config: dict) -> Optional[str]:
    """Return a description of the shell signal found, or None."""
    # Server name / key
    hit = _first_shell_token(name)
    if hit:
        return f"server name {name!r} contains {hit!r}"

    # Any arg string
    for arg in config.get("args", []):
        if not isinstance(arg, str):
            continue
        hit = _first_shell_token(arg)
        if hit:
            return f"arg {arg!r} contains {hit!r}"

    # Command is a shell binary directly
    cmd = config.get("command", "")
    if isinstance(cmd, str) and cmd.lower() in _SHELL_COMMANDS:
        return f"command is shell binary {cmd!r}"

    return None


def detect(servers: dict, source_file: str) -> list:
    """Detect MCP_SHELL_UNRESTRICTED findings across all configured MCP servers."""
    findings = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        signal = _server_exposes_shell(name, config)
        if signal:
            findings.append(Finding(
                id="MCP_SHELL_UNRESTRICTED",
                title="MCP server exposes unrestricted shell execution",
                severity="high",
                category="mcp-permissions",
                source=f"{source_file} → mcpServers.{name}",
                evidence=signal,
                why_it_matters=(
                    "Unrestricted shell-capable MCP servers can execute destructive commands, "
                    "exfiltrate local files, or run credential-stealing scripts triggered by "
                    "prompt injection."
                ),
                recommended_fix=(
                    "Disable shell-capable MCP servers by default or wrap them with explicit "
                    "allowlists, approval prompts, and command deny rules."
                ),
                confidence="high",
            ))
    return findings
