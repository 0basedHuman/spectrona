from typing import Any, Iterator

from ..models import Finding

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


def is_known_secret_value(value: str) -> bool:
    return any(iter_secret_matches(value))


def _redacted_evidence(path: str, matched_prefix: str) -> str:
    if matched_prefix:
        return f"{path} matched known secret prefix {matched_prefix!r}"
    return f"{path} matched known secret structure"


def _walk_values(value: Any, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, nested in value.items():
            key_path = f"{path}.{key}" if path else str(key)
            yield from _walk_values(nested, key_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk_values(nested, f"{path}[{index}]")


def detect(servers: dict, source_file: str) -> list:
    """Detect SECRET_KNOWN_PREFIX findings anywhere in MCP server configs."""
    findings = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        server_path = f"mcpServers.{name}"
        for path, value in _walk_values(config, server_path):
            for match in iter_secret_matches(value):
                findings.append(Finding(
                    id="SECRET_KNOWN_PREFIX",
                    title="Known secret prefix found in MCP server config",
                    severity="critical",
                    category="secrets",
                    source=f"{source_file} → {path}",
                    evidence=_redacted_evidence(path, match.prefix),
                    why_it_matters=(
                        "Plaintext credentials in MCP config may be committed to git, "
                        "visible in process lists, or accessible to other local processes."
                    ),
                    recommended_fix=(
                        "Remove plaintext secrets from MCP config. "
                        "Use environment variable references (e.g. ${MY_KEY}), "
                        "a local secrets manager, or runtime injection."
                    ),
                    confidence="high",
                ))
                break
    return findings
