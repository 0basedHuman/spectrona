import re
from typing import Iterable, Optional

from ..models import Finding
from ..parsers.claude_parser import ClaudeConfigFile


MAX_CLAUDE_MD_BYTES = 50 * 1024

_SECRET_RE = re.compile(
    r"(sk-proj-|sk-|ghp_|ghs_|github_pat_|AKIA|ASIA|npm_|xoxb-|xoxp-)"
    r"[A-Za-z0-9_\-]{4,}"
)


def detect(files: Iterable[ClaudeConfigFile]) -> list[Finding]:
    """Detect Claude config risks defined in claude-risk-rules.yaml."""
    findings: list[Finding] = []
    for item in files:
        if item.kind == "instructions":
            findings.extend(_detect_huge_context(item))
        elif item.kind == "settings" and item.data is not None:
            findings.extend(_detect_dangerous_permissions(item))
            findings.extend(_detect_missing_deny_list(item))
            findings.extend(_detect_hook_shell_injection(item))
    return findings


def _detect_huge_context(item: ClaudeConfigFile) -> list[Finding]:
    if item.size_bytes <= MAX_CLAUDE_MD_BYTES:
        return []
    return [Finding(
        id="CLAUDE_HUGE_CONTEXT",
        title="CLAUDE.md is excessively large (context pollution risk)",
        severity="medium",
        category="context-pollution",
        source=item.path,
        evidence=f"file_size_bytes={item.size_bytes}; threshold_bytes={MAX_CLAUDE_MD_BYTES}",
        why_it_matters=(
            "Large Claude instruction files are loaded into sessions, increasing token cost "
            "and crowding out task-specific context."
        ),
        recommended_fix="Split persistent guidance into focused files and import only what each project needs.",
        confidence="high",
    )]


def _detect_dangerous_permissions(item: ClaudeConfigFile) -> list[Finding]:
    matches = []
    for path, value in _iter_allow_entries(item.data or {}):
        signal = _dangerous_permission_signal(value)
        if signal:
            matches.append((path, value, signal))

    if not matches:
        return []

    evidence_items = [
        f"{path}: {_short(_redact(value))} ({signal})"
        for path, value, signal in matches[:5]
    ]
    if len(matches) > 5:
        evidence_items.append(f"{len(matches) - 5} additional dangerous allow entries")

    return [Finding(
        id="CLAUDE_DANGEROUS_PERMISSION",
        title="Claude settings grant dangerous auto-approved permission",
        severity="high",
        category="permissions",
        source=f"{item.path} → permissions",
        evidence="; ".join(evidence_items),
        why_it_matters=(
            "Auto-approved dangerous permissions let prompt-injected instructions perform "
            "destructive shell or filesystem operations without a user approval step."
        ),
        recommended_fix="Remove broad allow entries and keep dangerous shell/filesystem tools behind explicit approval.",
        confidence="high",
    )]


def _detect_missing_deny_list(item: ClaudeConfigFile) -> list[Finding]:
    if _has_deny_list(item.data or {}):
        return []
    return [Finding(
        id="CLAUDE_NO_DENY_LIST",
        title="Claude settings have no deny list configured",
        severity="low",
        category="permissions",
        source=item.path,
        evidence="no denyTools or permissions.deny entries found",
        why_it_matters=(
            "A deny list gives a local backstop for high-risk operations even when tools or "
            "project instructions change."
        ),
        recommended_fix="Add deny rules for destructive shell commands and sensitive filesystem paths.",
        confidence="low",
    )]


def _detect_hook_shell_injection(item: ClaudeConfigFile) -> list[Finding]:
    hooks = (item.data or {}).get("hooks")
    if hooks is None:
        return []

    matches = []
    for path, command in _iter_hook_commands(hooks, "hooks"):
        signal = _hook_shell_signal(command)
        if signal:
            matches.append((path, command, signal))

    findings = []
    for path, command, signal in matches:
        findings.append(Finding(
            id="CLAUDE_HOOK_SHELL_INJECTION",
            title="Claude hook command contains shell injection risk",
            severity="high",
            category="hooks",
            source=f"{item.path} → {path}",
            evidence=f"{signal}; command={_short(_redact(command))}",
            why_it_matters=(
                "Claude hooks run outside the model. If a hook sends untrusted tool output "
                "through a shell, prompt-injected content can become local code execution."
            ),
            recommended_fix="Avoid shell pipelines in hooks, quote variables, and pass untrusted data as arguments or stdin.",
            confidence="medium",
        ))
    return findings


def _iter_allow_entries(data: dict) -> Iterable[tuple[str, str]]:
    for key in ("allowedTools", "allowTools"):
        if key in data:
            yield from _iter_strings(data[key], key)

    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        for key in ("allow", "allowedTools", "allowTools"):
            if key in permissions:
                yield from _iter_strings(permissions[key], f"permissions.{key}")


def _iter_strings(value, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, f"{path}.{key}")


def _dangerous_permission_signal(value: str) -> Optional[str]:
    lower = value.lower().strip()
    compact = re.sub(r"\s+", " ", lower)

    if lower in {"*", "bash", "shell", "sh", "zsh"}:
        return "broad tool allow"
    if "bash(*)" in compact or "shell(*)" in compact or compact.startswith("bash:*"):
        return "broad shell auto-approval"
    if _broad_file_permission(compact):
        return "broad filesystem write auto-approval"

    risky_patterns = [
        ("rm -rf", "recursive delete command"),
        ("git push --force", "force-push command"),
        ("sudo ", "sudo command"),
        ("chmod 777", "world-writable chmod command"),
        ("dd if=", "raw disk write/read command"),
    ]
    for pattern, signal in risky_patterns:
        if pattern in compact:
            return signal

    if ("curl " in compact or "wget " in compact) and any(shell in compact for shell in ("| sh", "| bash", "| zsh")):
        return "remote script piped to shell"
    return None


def _broad_file_permission(value: str) -> bool:
    for tool in ("write", "edit", "multiedit", "notebookedit"):
        if value.startswith(f"{tool}(*)") or value.startswith(f"{tool}:*"):
            return True
    return False


def _has_deny_list(data: dict) -> bool:
    for key in ("denyTools", "deniedTools"):
        if _has_nonempty_value(data.get(key)):
            return True

    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        for key in ("deny", "denyTools", "deniedTools"):
            if _has_nonempty_value(permissions.get(key)):
                return True
    return False


def _has_nonempty_value(value) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return False


def _iter_hook_commands(value, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key == "command" and isinstance(item, str):
                yield child_path, item
            else:
                yield from _iter_hook_commands(item, child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_hook_commands(item, f"{path}[{index}]")


def _hook_shell_signal(command: str) -> Optional[str]:
    lower = command.lower()
    if "$" in command and any(token in command for token in ("|", ";", "&&", "||", "`", "$(")):
        return "variable interpolation combined with shell metacharacters"
    if "eval " in lower or "bash -c" in lower or "sh -c" in lower or "zsh -c" in lower:
        return "explicit shell evaluation"
    if "|" in command and any(shell in lower for shell in (" sh", " bash", " zsh", "python", "node")):
        return "pipeline in hook command"
    return None


def _redact(text: str) -> str:
    return _SECRET_RE.sub(lambda match: match.group(1) + "[REDACTED]", text)


def _short(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
