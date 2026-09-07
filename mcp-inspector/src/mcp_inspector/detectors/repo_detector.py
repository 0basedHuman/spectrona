import fnmatch
import math
import re
from collections import defaultdict
from typing import Optional

from ..models import Finding
from ..parsers.repo_parser import RepoFile, RepoScan

try:
    from spectrona_detection.secrets import iter_secret_matches
except ImportError:  # pragma: no cover - exercised by component-only CLI shims
    import sys
    from pathlib import Path

    for parent in Path(__file__).resolve().parents:
        shared_src = parent / "spectrona-detection" / "src"
        if shared_src.exists():
            sys.path.insert(0, str(shared_src))
            break
    from spectrona_detection.secrets import iter_secret_matches
_TOKEN_RE = re.compile(r"[A-Za-z0-9_+/@.-]{20,}")
_ENTROPY_THRESHOLD = 4.5
_MIN_ENTROPY_TOKEN_LENGTH = 20


def detect(scan: RepoScan) -> list[Finding]:
    """Detect repo-level secret risks defined in secrets-risk-rules.yaml."""
    findings: list[Finding] = []
    secret_hits_by_file: dict[str, set[str]] = defaultdict(set)

    findings.extend(_detect_exposed_env_files(scan))

    for item in scan.files:
        known_prefix_findings = _detect_known_prefixes(item)
        entropy_findings = _detect_high_entropy(item)
        findings.extend(known_prefix_findings)
        findings.extend(entropy_findings)
        if known_prefix_findings:
            secret_hits_by_file[item.relative_path].add("SECRET_KNOWN_PREFIX")
        if entropy_findings:
            secret_hits_by_file[item.relative_path].add("SECRET_HIGH_ENTROPY_VALUE")

    findings.extend(_detect_secret_in_git_history(scan, secret_hits_by_file))
    return findings


def _detect_exposed_env_files(scan: RepoScan) -> list[Finding]:
    findings = []
    for item in scan.files:
        if not _is_env_file(item.relative_path):
            continue
        if _is_gitignored(item.relative_path, scan.gitignore_patterns):
            continue
        findings.append(Finding(
            id="SECRET_ENV_FILE_EXPOSED",
            title=".env file is not in .gitignore",
            severity="high",
            category="secrets",
            source=item.path,
            evidence=f"{item.relative_path} exists and is not covered by .gitignore",
            why_it_matters=(
                "Environment files often contain credentials. If they are not ignored, "
                "they may be committed or exposed by tooling."
            ),
            recommended_fix="Add .env* to .gitignore and rotate any credentials that may have been committed.",
            confidence="high",
        ))
    return findings


def _detect_known_prefixes(item: RepoFile) -> list[Finding]:
    matches = []
    for line_no, line in enumerate(item.text.splitlines(), start=1):
        prefix = _line_known_prefix(line)
        if prefix:
            matches.append((line_no, prefix))

    if not matches:
        return []

    evidence_items = [f"line {line_no} matched known secret prefix {prefix!r}" for line_no, prefix in matches[:5]]
    if len(matches) > 5:
        evidence_items.append(f"{len(matches) - 5} additional prefix matches")

    return [Finding(
        id="SECRET_KNOWN_PREFIX",
        title="Value matches known secret prefix pattern",
        severity="critical",
        category="secrets",
        source=item.path,
        evidence="; ".join(evidence_items),
        why_it_matters=(
            "Known credential prefixes are strong signals that plaintext secrets are present "
            "inside repository files."
        ),
        recommended_fix="Revoke the credential, remove it from the repo, and store it in environment variables or a secrets manager.",
        confidence="high",
    )]


def _detect_high_entropy(item: RepoFile) -> list[Finding]:
    matches = []
    for line_no, line in enumerate(item.text.splitlines(), start=1):
        for token in _TOKEN_RE.findall(line):
            if not _candidate_token(token):
                continue
            entropy = _entropy(token)
            if entropy > _ENTROPY_THRESHOLD:
                matches.append((line_no, len(token), entropy))
                break

    if not matches:
        return []

    evidence_items = [
        f"line {line_no} contains high-entropy token metadata length={length} entropy={entropy:.2f}"
        for line_no, length, entropy in matches[:5]
    ]
    if len(matches) > 5:
        evidence_items.append(f"{len(matches) - 5} additional high-entropy lines")

    return [Finding(
        id="SECRET_HIGH_ENTROPY_VALUE",
        title="High-entropy string found in config (possible secret)",
        severity="high",
        category="secrets",
        source=item.path,
        evidence="; ".join(evidence_items),
        why_it_matters=(
            "Long random-looking strings in repository files are often API keys, tokens, "
            "passwords, or session secrets."
        ),
        recommended_fix="Move secrets to environment variables or a secrets manager, then rotate any exposed value.",
        confidence="medium",
    )]


def _detect_secret_in_git_history(scan: RepoScan, secret_hits_by_file: dict[str, set[str]]) -> list[Finding]:
    findings = []
    for relative_path, ids in sorted(secret_hits_by_file.items()):
        if relative_path not in scan.git_tracked_files:
            continue
        findings.append(Finding(
            id="SECRET_IN_GIT_HISTORY",
            title="Secret-like value may be committed in git history",
            severity="high",
            category="secrets",
            source=f"{scan.repo_root}/{relative_path}",
            evidence=f"git-tracked file contains secret-like findings: {', '.join(sorted(ids))}",
            why_it_matters=(
                "Secrets in tracked files may persist in local or remote git history even after "
                "the current file is edited."
            ),
            recommended_fix="Rotate the secret and purge it from git history with git-filter-repo or BFG if it was committed.",
            confidence="medium",
        ))
    return findings


def _line_known_prefix(line: str) -> Optional[str]:
    match = next(iter_secret_matches(line), None)
    return (match.prefix or match.rule_id) if match else None


def _candidate_token(token: str) -> bool:
    if len(token) < _MIN_ENTROPY_TOKEN_LENGTH:
        return False
    if token.startswith(("http://", "https://", "file://")):
        return False
    if "/" in token and token.count("/") >= 2:
        return False
    if not any(ch.isdigit() for ch in token):
        return False
    if not any(ch.isalpha() for ch in token):
        return False
    return True


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    total = len(value)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _is_env_file(relative_path: str) -> bool:
    name = relative_path.rsplit("/", 1)[-1]
    return name == ".env" or name in {".env.local", ".env.production", ".env.development", ".env.test"}


def _is_gitignored(relative_path: str, patterns: list[str]) -> bool:
    name = relative_path.rsplit("/", 1)[-1]
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if normalized.startswith("/"):
            normalized = normalized[1:]
        if normalized == ".env*" and name.startswith(".env"):
            return True
        if fnmatch.fnmatch(relative_path, normalized) or fnmatch.fnmatch(name, normalized):
            return True
    return False
