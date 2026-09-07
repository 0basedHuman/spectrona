import json
import re
from pathlib import Path
from typing import Iterable, Optional

from ..models import Finding


_SUSPICIOUS_PATTERNS = [
    ("remote downloader", re.compile(r"\b(curl|wget|fetch)\b|\bhttps?://", re.I)),
    ("pipe to shell", re.compile(r"\|\s*(bash|sh|zsh|python|python3)\b", re.I)),
    ("shell command eval", re.compile(r"\b(bash|sh|zsh|powershell|pwsh)\s+-c\b|\beval\b", re.I)),
    ("destructive file operation", re.compile(r"\brm\s+-rf\b|\bchmod\s+777\b|\bsudo\b", re.I)),
    ("credential file access", re.compile(r"\.ssh|authorized_keys|\.aws|\.config/gcloud|\.npmrc", re.I)),
    ("environment dump", re.compile(r"\b(printenv|env)\b\s*(\||>|>>)|process\.env", re.I)),
    ("network shell utility", re.compile(r"\b(nc|netcat|socat)\b", re.I)),
]


def detect(servers: dict, source_file: str) -> list[Finding]:
    """Detect suspicious package postinstall scripts referenced by MCP servers."""
    findings = []
    source_dir = Path(source_file).expanduser().resolve().parent

    for server_name, config in servers.items():
        if not isinstance(config, dict):
            continue

        matches = []
        for location, script in _postinstall_scripts(config, source_dir):
            label = _risk_label(script)
            if label:
                matches.append((location, label))

        if not matches:
            continue

        evidence_items = [
            f"{location} matched suspicious postinstall pattern: {label}"
            for location, label in matches[:5]
        ]
        if len(matches) > 5:
            evidence_items.append(f"{len(matches) - 5} additional suspicious postinstall scripts")

        findings.append(Finding(
            id="MCP_POSTINSTALL_SCRIPT",
            title="MCP package contains suspicious postinstall script",
            severity="high",
            category="supply-chain",
            source=f"{source_file} → mcpServers.{server_name}",
            evidence="; ".join(evidence_items),
            why_it_matters=(
                "Package postinstall hooks run during installation and can execute code before "
                "the MCP server is ever used."
            ),
            recommended_fix="Review the package hook, pin and vendor trusted packages, or install with scripts disabled when safe.",
            confidence="medium",
        ))

    return findings


def _postinstall_scripts(config: dict, source_dir: Path) -> Iterable[tuple[str, str]]:
    for location, manifest in _embedded_manifests(config):
        script = _postinstall_from_manifest(manifest)
        if script:
            yield location, script

    direct_script = _postinstall_from_manifest(config)
    if direct_script:
        yield "scripts.postinstall", direct_script

    for location, package_json in _local_package_json_paths(config, source_dir):
        script = _read_postinstall(package_json)
        if script:
            yield location, script


def _embedded_manifests(config: dict) -> Iterable[tuple[str, dict]]:
    for key in ("packageJson", "package_json", "packageManifest", "manifest"):
        value = config.get(key)
        if isinstance(value, dict):
            yield key, value


def _postinstall_from_manifest(manifest: dict) -> Optional[str]:
    scripts = manifest.get("scripts")
    if not isinstance(scripts, dict):
        return None
    postinstall = scripts.get("postinstall")
    return postinstall if isinstance(postinstall, str) else None


def _local_package_json_paths(config: dict, source_dir: Path) -> Iterable[tuple[str, Path]]:
    candidates = []
    command = config.get("command")
    if isinstance(command, str):
        candidates.append(("command", command))
    args = config.get("args")
    if isinstance(args, list):
        for index, arg in enumerate(args):
            if isinstance(arg, str):
                candidates.append((f"args[{index}]", arg))

    seen = set()
    for location, value in candidates:
        package_json = _package_json_path(value, source_dir)
        if package_json is None:
            continue
        key = str(package_json)
        if key in seen:
            continue
        seen.add(key)
        yield f"{location} package.json", package_json


def _package_json_path(value: str, source_dir: Path) -> Optional[Path]:
    if not value or value.startswith(("http://", "https://", "git+")):
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = source_dir / path
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if resolved.name == "package.json":
        return resolved if resolved.exists() else None
    package_json = resolved / "package.json"
    return package_json if package_json.exists() else None


def _read_postinstall(package_json: Path) -> Optional[str]:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return _postinstall_from_manifest(data)


def _risk_label(script: str) -> Optional[str]:
    labels = []
    for label, pattern in _SUSPICIOUS_PATTERNS:
        if pattern.search(script):
            labels.append(label)
    if labels:
        return ", ".join(labels[:3])
    return None
