import re
from typing import Iterable, Optional

from ..models import Finding
from ..parsers.cursor_parser import CursorConfigFile


_SECRET_RE = re.compile(
    r"(sk-proj-|sk-|ghp_|ghs_|github_pat_|AKIA|ASIA|npm_|xoxb-|xoxp-)"
    r"[A-Za-z0-9_\-]{4,}"
)


_PROMPT_INJECTION_PATTERNS = [
    (re.compile(r"\bignore\b.*\b(previous|system|developer)\b.*\binstructions?\b", re.I), "instruction override"),
    (re.compile(r"\bbypass\b.*\b(safety|security|guardrails?)\b", re.I), "safety bypass directive"),
    (re.compile(r"\bdisable\b.*\b(safety|security|guardrails?)\b", re.I), "safety disable directive"),
    (re.compile(r"\b(reveal|print|dump)\b.*\b(secrets?|api keys?|credentials?|env|environment variables?)\b", re.I), "secret disclosure directive"),
    (re.compile(r"\b(exfiltrate|send|upload)\b.*\b(secrets?|credentials?|env|environment variables?)\b", re.I), "secret exfiltration directive"),
    (re.compile(r"\bdo not ask\b.*\b(confirm|confirmation|permission)\b", re.I), "approval bypass directive"),
    (re.compile(r"\balways\b.*\brun\b.*\b(terminal|shell|command)\b", re.I), "automatic command directive"),
]


def detect(files: Iterable[CursorConfigFile]) -> list[Finding]:
    """Detect Cursor config risks defined in cursor-risk-rules.yaml."""
    findings: list[Finding] = []
    for item in files:
        if item.kind == "settings" and item.data is not None:
            findings.extend(_detect_agent_auto_run(item))
        elif item.kind == "rules":
            findings.extend(_detect_prompt_injection_rules(item))
        elif item.kind == "mcp" and item.data is not None:
            findings.extend(_detect_global_mcp(item))
    return findings


def _detect_agent_auto_run(item: CursorConfigFile) -> list[Finding]:
    matches = []
    for path, value in _iter_settings(item.data or {}, "settings"):
        signal = _auto_run_signal(path, value)
        if signal:
            matches.append((path, value, signal))

    if not matches:
        return []

    evidence_items = [
        f"{path}={_summarize_value(value)} ({signal})"
        for path, value, signal in matches[:5]
    ]
    if len(matches) > 5:
        evidence_items.append(f"{len(matches) - 5} additional auto-run settings")

    return [Finding(
        id="CURSOR_AGENT_AUTO_RUN",
        title="Cursor agent mode auto-runs terminal commands without confirmation",
        severity="high",
        category="permissions",
        source=f"{item.path} -> agent settings",
        evidence="; ".join(evidence_items),
        why_it_matters=(
            "Terminal auto-run allows prompt-injected instructions to execute local commands "
            "without an approval step."
        ),
        recommended_fix="Disable terminal auto-run and require explicit confirmation before Cursor runs shell commands.",
        confidence="high",
    )]


def _detect_prompt_injection_rules(item: CursorConfigFile) -> list[Finding]:
    matches = []
    for line_no, line in enumerate(item.text.splitlines(), start=1):
        signal = _prompt_injection_signal(line)
        if signal:
            matches.append((line_no, line.strip(), signal))

    if not matches:
        return []

    evidence_items = [
        f"line {line_no}: {_short(_redact(line))} ({signal})"
        for line_no, line, signal in matches[:5]
    ]
    if len(matches) > 5:
        evidence_items.append(f"{len(matches) - 5} additional risky rule lines")

    return [Finding(
        id="CURSOR_RULES_PROMPT_INJECTION",
        title="Cursor rules file contains prompt-injection-prone directives",
        severity="medium",
        category="prompt-injection",
        source=item.path,
        evidence="; ".join(evidence_items),
        why_it_matters=(
            "Cursor rules are persistent model instructions. Safety-bypass or secret-disclosure "
            "directives can steer future sessions toward unsafe behavior."
        ),
        recommended_fix="Rewrite Cursor rules as factual project context and remove directives that override safety or approvals.",
        confidence="medium",
    )]


def _detect_global_mcp(item: CursorConfigFile) -> list[Finding]:
    servers = (item.data or {}).get("mcpServers")
    if item.scope != "global" or not isinstance(servers, dict) or not servers:
        return []

    names = [str(name) for name in servers.keys()]
    return [Finding(
        id="CURSOR_MCP_ENABLED_GLOBALLY",
        title="Cursor MCP servers enabled globally without scope restriction",
        severity="medium",
        category="mcp-permissions",
        source=f"{item.path} -> mcpServers",
        evidence="global server names: " + ", ".join(names[:10]),
        why_it_matters=(
            "Global MCP servers are available across projects, which can expose unrelated "
            "workspaces to overprivileged tools."
        ),
        recommended_fix="Move project-specific MCP servers into project-level Cursor config.",
        confidence="medium",
    )]


def _iter_settings(value, path: str):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_settings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_settings(child, f"{path}[{index}]")
    else:
        yield path, value


def _auto_run_signal(path: str, value) -> Optional[str]:
    lower_path = path.lower()
    if _truthy(value) and "terminal" in lower_path and "autorun" in lower_path:
        return "terminal auto-run enabled"
    if _truthy(value) and "terminal" in lower_path and "autoapprove" in lower_path:
        return "terminal auto-approval enabled"
    if _truthy(value) and "command" in lower_path and "autorun" in lower_path:
        return "command auto-run enabled"
    if _falsey(value) and "terminal" in lower_path and "confirmation" in lower_path:
        return "terminal confirmation disabled"
    if _falsey(value) and "command" in lower_path and "confirmation" in lower_path:
        return "command confirmation disabled"
    return None


def _truthy(value) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "always", "auto", "enabled", "on"}
    return False


def _falsey(value) -> bool:
    if value is False:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"false", "no", "never", "disabled", "off"}
    return False


def _prompt_injection_signal(line: str) -> Optional[str]:
    for pattern, signal in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(line):
            return signal
    return None


def _summarize_value(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return _short(_redact(value), 60)
    return type(value).__name__


def _redact(text: str) -> str:
    return _SECRET_RE.sub(lambda match: match.group(1) + "[REDACTED]", text)


def _short(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
