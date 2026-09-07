import re
from dataclasses import dataclass
from typing import Any, Iterator, Optional


REDACTION = "[REDACTED_SECRET]"


@dataclass(frozen=True)
class SecretRule:
    id: str
    pattern: re.Pattern
    prefix_group: Optional[int] = None


@dataclass(frozen=True)
class SecretMatch:
    rule_id: str
    prefix: str
    start: int
    end: int


_TOKEN_CHARS = r"[A-Za-z0-9_\-./=+]"


_RULES = [
    SecretRule("openai_project_key", re.compile(r"(sk-proj-)" + _TOKEN_CHARS + r"{8,}"), 1),
    SecretRule("stripe_key", re.compile(r"(sk_(?:live|test)_)[A-Za-z0-9]{16,}"), 1),
    SecretRule("openai_key", re.compile(r"(sk-)" + _TOKEN_CHARS + r"{16,}"), 1),
    SecretRule("github_token", re.compile(r"(gh[ps]_)" + _TOKEN_CHARS + r"{16,}"), 1),
    SecretRule("github_pat", re.compile(r"(github_pat_)" + _TOKEN_CHARS + r"{16,}"), 1),
    SecretRule("gitlab_pat", re.compile(r"(glpat-)[A-Za-z0-9_\-]{16,}"), 1),
    SecretRule("google_api_key", re.compile(r"(AIza)[A-Za-z0-9_\-]{20,}"), 1),
    SecretRule("sendgrid_api_key", re.compile(r"(SG\.)[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), 1),
    SecretRule("huggingface_token", re.compile(r"(hf_)[A-Za-z0-9]{16,}"), 1),
    SecretRule("aws_access_key_id", re.compile(r"\b((?:AKIA|ASIA))[A-Z0-9]{16}\b"), 1),
    SecretRule(
        "aws_secret_access_key",
        re.compile(r"(?<![A-Za-z0-9/+=])(?=[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=]))(?=[A-Za-z0-9/+=]*[a-z])(?=[A-Za-z0-9/+=]*[A-Z])(?=[A-Za-z0-9/+=]*\d)(?=[A-Za-z0-9/+=]*/)[A-Za-z0-9/+=]{40}"),
    ),
    SecretRule("private_key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    SecretRule("postgres_url", re.compile(r"postgres(?:ql)?://[^:\s/@]+:[^@\s]+@[^/\s]+/\S+")),
    SecretRule("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{10,}\b")),
    SecretRule("npm_token", re.compile(r"(npm_)" + _TOKEN_CHARS + r"{16,}"), 1),
    SecretRule("slack_token", re.compile(r"(xox[bp]-)" + _TOKEN_CHARS + r"{16,}"), 1),
]


def iter_secret_matches(text: str) -> Iterator[SecretMatch]:
    """Yield non-overlapping secret matches without exposing matched values."""
    occupied: list[tuple[int, int]] = []
    for rule in _RULES:
        for match in rule.pattern.finditer(text):
            start, end = match.span()
            if any(start < used_end and used_start < end for used_start, used_end in occupied):
                continue
            occupied.append((start, end))
            prefix = match.group(rule.prefix_group) if rule.prefix_group else ""
            yield SecretMatch(rule.id, prefix, start, end)


def scan_text(text: str) -> list[str]:
    return [match.prefix or match.rule_id for match in iter_secret_matches(text)]


def findings_count(text: str) -> int:
    return sum(1 for _ in iter_secret_matches(text))


def redact_text(text: str) -> str:
    matches = list(iter_secret_matches(text))
    if not matches:
        return text
    parts: list[str] = []
    cursor = 0
    for match in matches:
        parts.append(text[cursor:match.start])
        parts.append((match.prefix or "") + REDACTION)
        cursor = match.end
    parts.append(text[cursor:])
    return "".join(parts)


def redact_json(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_json(item) for key, item in value.items()}
    return value
