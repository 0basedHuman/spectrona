import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .commands.config_file import spectrona_home


BEGIN_MARKER = "# >>> spectrona managed >>>"
END_MARKER = "# <<< spectrona managed <<<"


@dataclass(frozen=True)
class RoutingIntegrationCandidate:
    integration_id: str
    label: str
    provider: str
    kind: str
    path: Path


@dataclass(frozen=True)
class RoutingIntegrationStatus:
    integration_id: str
    label: str
    provider: str
    kind: str
    path: str
    exists: bool
    status: str
    gateway_base_url: str
    expected_base_url: str
    backup_exists: bool = False
    backup_matches_current: bool = False
    managed_block_present: bool = False
    api_key_configured: bool = False
    drift_detected: bool = False
    drift_reason: str = ""
    recommended_action: str = "none"
    repair_available: bool = False

    def to_dict(self) -> dict:
        return {
            "integration_id": self.integration_id,
            "label": self.label,
            "provider": self.provider,
            "kind": self.kind,
            "path": self.path,
            "exists": self.exists,
            "status": self.status,
            "gateway_base_url": self.gateway_base_url,
            "expected_base_url": self.expected_base_url,
            "backup_exists": self.backup_exists,
            "backup_matches_current": self.backup_matches_current,
            "managed_block_present": self.managed_block_present,
            "api_key_configured": self.api_key_configured,
            "drift_detected": self.drift_detected,
            "drift_reason": self.drift_reason,
            "recommended_action": self.recommended_action,
            "repair_available": self.repair_available,
        }


@dataclass(frozen=True)
class RoutingIntegrationMutationResult:
    integration_id: str
    label: str
    provider: str
    path: str
    action: str
    changed: bool
    before_status: str
    after_status: str
    backup_path: str = ""

    def to_dict(self) -> dict:
        return {
            "integration_id": self.integration_id,
            "label": self.label,
            "provider": self.provider,
            "path": self.path,
            "action": self.action,
            "changed": self.changed,
            "before_status": self.before_status,
            "after_status": self.after_status,
            "backup_path": self.backup_path,
        }


def gateway_base(base_url: Optional[str] = None) -> str:
    return (base_url or os.getenv("SPECTRONA_GATEWAY_BASE_URL", "http://localhost:8787")).rstrip("/")


def claude_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path).expanduser()
    override = os.getenv("SPECTRONA_CLAUDE_ENV_PATH")
    if override:
        return Path(override).expanduser()
    return spectrona_home() / "claude.env"


def codex_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path).expanduser()
    override = os.getenv("SPECTRONA_CODEX_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex" / "config.toml"


def vscode_settings_path(path: Optional[str] = None, repo_root: Optional[Path] = None) -> Path:
    if path:
        return Path(path).expanduser()
    override = os.getenv("SPECTRONA_VSCODE_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()
    root = repo_root.expanduser() if repo_root else Path.cwd()
    return root / ".vscode" / "settings.json"


def claude_block(base_url: Optional[str] = None) -> str:
    base = gateway_base(base_url)
    return "\n".join([
        BEGIN_MARKER,
        f"export ANTHROPIC_BASE_URL={base}/anthropic",
        "export ANTHROPIC_API_KEY=spectrona-local-token",
        END_MARKER,
    ])


def codex_block(base_url: Optional[str] = None) -> str:
    base = gateway_base(base_url)
    return "\n".join([
        BEGIN_MARKER,
        'model_provider = "spectrona"',
        "",
        "[model_providers.spectrona]",
        'name = "Spectrona Local Gateway"',
        f'base_url = "{base}/openai/v1"',
        'env_key = "SPECTRONA_API_KEY"',
        END_MARKER,
    ])


def vscode_settings(base_url: Optional[str] = None) -> dict:
    base = gateway_base(base_url)
    settings = {
        "spectrona.providerRouting": {
            "enabled": True,
            "managedBy": "spectrona",
            "openaiBaseUrl": f"{base}/openai/v1",
            "anthropicBaseUrl": f"{base}/anthropic",
            "apiKeyEnv": "SPECTRONA_API_KEY",
            "anthropicApiKeyEnv": "ANTHROPIC_API_KEY",
        },
    }
    env = _vscode_env_values(base)
    for setting_name in _vscode_env_setting_names():
        settings[setting_name] = dict(env)
    return settings


def discover_routing_integrations(
    claude_env_path: Optional[Path] = None,
    codex_config_path: Optional[Path] = None,
    vscode_config_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    gateway_base_url: Optional[str] = None,
) -> list[RoutingIntegrationStatus]:
    base = gateway_base(gateway_base_url)
    return [
        _status_for(candidate, base)
        for candidate in _candidates(
            claude_env_path=claude_env_path,
            codex_config_path=codex_config_path,
            vscode_config_path=vscode_config_path,
            repo_root=repo_root,
        )
    ]


def find_routing_integration(
    integration_id: str,
    claude_env_path: Optional[Path] = None,
    codex_config_path: Optional[Path] = None,
    vscode_config_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> RoutingIntegrationCandidate:
    for candidate in _candidates(
        claude_env_path=claude_env_path,
        codex_config_path=codex_config_path,
        vscode_config_path=vscode_config_path,
        repo_root=repo_root,
    ):
        if candidate.integration_id == integration_id:
            return candidate
    supported = ", ".join(candidate.integration_id for candidate in _candidates())
    raise ValueError(f"unsupported provider routing integration id: {integration_id}. Supported ids: {supported}")


def apply_routing_integration(
    integration_id: str,
    path: Optional[Path] = None,
    gateway_base_url: Optional[str] = None,
) -> RoutingIntegrationMutationResult:
    candidate = _candidate_with_path(integration_id, path)
    base = gateway_base(gateway_base_url)
    before = _status_for(candidate, base)
    if before.status != "protected":
        if candidate.integration_id == "vscode":
            _write_vscode_settings(candidate.path, base)
        else:
            _write_managed_block(candidate.path, _block_for(candidate.integration_id, base))
    after = _status_for(candidate, base)
    backup = _backup_path(candidate.path)
    return RoutingIntegrationMutationResult(
        integration_id=candidate.integration_id,
        label=candidate.label,
        provider=candidate.provider,
        path=str(candidate.path),
        action="protect",
        changed=before.status != after.status or before.drift_detected != after.drift_detected,
        before_status=before.status,
        after_status=after.status,
        backup_path=str(backup) if backup.exists() else "",
    )


def undo_routing_integration(
    integration_id: str,
    path: Optional[Path] = None,
    gateway_base_url: Optional[str] = None,
) -> RoutingIntegrationMutationResult:
    candidate = _candidate_with_path(integration_id, path)
    base = gateway_base(gateway_base_url)
    before = _status_for(candidate, base)
    if candidate.integration_id == "vscode":
        changed = _undo_vscode_settings(candidate.path, base)
    else:
        changed = _undo_managed_block(candidate.path)
    after = _status_for(candidate, base)
    backup = _backup_path(candidate.path)
    return RoutingIntegrationMutationResult(
        integration_id=candidate.integration_id,
        label=candidate.label,
        provider=candidate.provider,
        path=str(candidate.path),
        action="unprotect",
        changed=changed,
        before_status=before.status,
        after_status=after.status,
        backup_path=str(backup) if backup.exists() else "",
    )


def routing_statuses_to_json(statuses: list[RoutingIntegrationStatus]) -> str:
    return json.dumps([status.to_dict() for status in statuses], indent=2)


def routing_mutation_to_json(result: RoutingIntegrationMutationResult) -> str:
    return json.dumps(result.to_dict(), indent=2)


def _candidates(
    claude_env_path: Optional[Path] = None,
    codex_config_path: Optional[Path] = None,
    vscode_config_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> list[RoutingIntegrationCandidate]:
    return [
        RoutingIntegrationCandidate(
            integration_id="claude",
            label="Claude",
            provider="anthropic",
            kind="env",
            path=claude_env_path.expanduser() if claude_env_path else claude_path(),
        ),
        RoutingIntegrationCandidate(
            integration_id="codex",
            label="Codex",
            provider="openai",
            kind="toml",
            path=codex_config_path.expanduser() if codex_config_path else codex_path(),
        ),
        RoutingIntegrationCandidate(
            integration_id="vscode",
            label="VS Code",
            provider="openai-compatible",
            kind="json",
            path=vscode_config_path.expanduser() if vscode_config_path else vscode_settings_path(repo_root=repo_root),
        ),
    ]


def _candidate_with_path(integration_id: str, path: Optional[Path]) -> RoutingIntegrationCandidate:
    if integration_id == "claude":
        return _candidates(claude_env_path=path)[0]
    if integration_id == "codex":
        return _candidates(codex_config_path=path)[1]
    if integration_id == "vscode":
        return _candidates(vscode_config_path=path)[2]
    return find_routing_integration(integration_id)


def _status_for(candidate: RoutingIntegrationCandidate, base: str) -> RoutingIntegrationStatus:
    if candidate.integration_id == "vscode":
        return _status_for_vscode(candidate, base)

    backup = _backup_path(candidate.path)
    backup_exists = backup.exists()
    backup_matches_current = backup_exists and _files_match(candidate.path, backup)
    expected_url = _expected_base_url(candidate.integration_id, base)

    if not candidate.path.exists():
        recommendation = _recommendation_for("missing", False)
        return RoutingIntegrationStatus(
            integration_id=candidate.integration_id,
            label=candidate.label,
            provider=candidate.provider,
            kind=candidate.kind,
            path=str(candidate.path),
            exists=False,
            status="missing",
            gateway_base_url=base,
            expected_base_url=expected_url,
            backup_exists=backup_exists,
            backup_matches_current=backup_matches_current,
            **recommendation,
        )

    text = candidate.path.read_text()
    block = _managed_block(text)
    managed = block != ""
    protected = managed and _block_matches(candidate.integration_id, block, base)
    if protected:
        status = "protected"
    elif managed:
        status = "partial"
    else:
        status = "unprotected"

    recommendation = _recommendation_for(status, managed)
    return RoutingIntegrationStatus(
        integration_id=candidate.integration_id,
        label=candidate.label,
        provider=candidate.provider,
        kind=candidate.kind,
        path=str(candidate.path),
        exists=True,
        status=status,
        gateway_base_url=base,
        expected_base_url=expected_url,
        backup_exists=backup_exists,
        backup_matches_current=backup_matches_current,
        managed_block_present=managed,
        api_key_configured=_api_key_configured(candidate.integration_id, block),
        **recommendation,
    )


def _recommendation_for(status: str, managed_block_present: bool) -> dict:
    if status == "protected":
        return {
            "drift_detected": False,
            "drift_reason": "",
            "recommended_action": "none",
            "repair_available": False,
        }
    if status == "partial" and managed_block_present:
        return {
            "drift_detected": True,
            "drift_reason": "managed provider routing block does not match the current Spectrona gateway URL",
            "recommended_action": "repair",
            "repair_available": True,
        }
    return {
        "drift_detected": False,
        "drift_reason": "",
        "recommended_action": "setup",
        "repair_available": True,
    }


def _block_for(integration_id: str, base: str) -> str:
    if integration_id == "claude":
        return claude_block(base)
    if integration_id == "codex":
        return codex_block(base)
    raise ValueError(f"unsupported provider routing integration id: {integration_id}")


def _expected_base_url(integration_id: str, base: str) -> str:
    if integration_id == "claude":
        return f"{base}/anthropic"
    if integration_id == "codex":
        return f"{base}/openai/v1"
    if integration_id == "vscode":
        return f"{base}/openai/v1"
    raise ValueError(f"unsupported provider routing integration id: {integration_id}")


def _expected_lines(integration_id: str, base: str) -> set[str]:
    lines = _block_for(integration_id, base).splitlines()
    return {
        line.strip()
        for line in lines
        if line.strip() and line.strip() not in {BEGIN_MARKER, END_MARKER}
    }


def _block_matches(integration_id: str, block: str, base: str) -> bool:
    actual = {line.strip() for line in block.splitlines() if line.strip()}
    return _expected_lines(integration_id, base).issubset(actual)


def _api_key_configured(integration_id: str, block: str) -> bool:
    if integration_id == "claude":
        return "ANTHROPIC_API_KEY=" in block
    if integration_id == "codex":
        return 'env_key = "SPECTRONA_API_KEY"' in block
    if integration_id == "vscode":
        return False
    return False


def _vscode_env_values(base: str) -> dict:
    return {
        "OPENAI_BASE_URL": f"{base}/openai/v1",
        "ANTHROPIC_BASE_URL": f"{base}/anthropic",
        "SPECTRONA_API_KEY": "spectrona-local-token",
        "ANTHROPIC_API_KEY": "spectrona-local-token",
    }


def _vscode_env_setting_names() -> tuple[str, ...]:
    return (
        "terminal.integrated.env.osx",
        "terminal.integrated.env.linux",
        "terminal.integrated.env.windows",
    )


def _vscode_managed(settings: dict) -> bool:
    routing = settings.get("spectrona.providerRouting")
    return isinstance(routing, dict) and routing.get("managedBy") == "spectrona"


def _vscode_settings_match(settings: dict, base: str) -> bool:
    routing = settings.get("spectrona.providerRouting")
    if not isinstance(routing, dict):
        return False
    if routing.get("enabled") is not True:
        return False
    if routing.get("managedBy") != "spectrona":
        return False
    if routing.get("openaiBaseUrl") != f"{base}/openai/v1":
        return False
    if routing.get("anthropicBaseUrl") != f"{base}/anthropic":
        return False

    expected = _vscode_env_values(base)
    for setting_name in _vscode_env_setting_names():
        env = settings.get(setting_name)
        if not isinstance(env, dict):
            return False
        for key, value in expected.items():
            if env.get(key) != value:
                return False
    return True


def _vscode_api_key_configured(settings: dict) -> bool:
    routing = settings.get("spectrona.providerRouting")
    if not isinstance(routing, dict):
        return False
    if routing.get("apiKeyEnv") != "SPECTRONA_API_KEY":
        return False
    if routing.get("anthropicApiKeyEnv") != "ANTHROPIC_API_KEY":
        return False
    for setting_name in _vscode_env_setting_names():
        env = settings.get(setting_name)
        if isinstance(env, dict) and env.get("SPECTRONA_API_KEY") and env.get("ANTHROPIC_API_KEY"):
            return True
    return False


def _write_vscode_settings(path: Path, base: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    settings = _read_json_settings(path) if path.exists() else {}
    if not isinstance(settings, dict):
        settings = {}

    managed = vscode_settings(base)
    settings["spectrona.providerRouting"] = managed["spectrona.providerRouting"]
    for setting_name in _vscode_env_setting_names():
        env = settings.get(setting_name)
        if not isinstance(env, dict):
            env = {}
        env.update(managed[setting_name])
        settings[setting_name] = env
    _write_json_settings(path, settings)


def _undo_vscode_settings(path: Path, base: str) -> bool:
    if not path.exists():
        return False
    try:
        settings = _read_json_settings(path)
    except ValueError:
        return False
    if not isinstance(settings, dict):
        return False

    changed = False
    routing = settings.get("spectrona.providerRouting")
    managed_routing = isinstance(routing, dict) and routing.get("managedBy") == "spectrona"
    if managed_routing:
        settings.pop("spectrona.providerRouting", None)
        changed = True

    expected = _vscode_env_values(base)
    for setting_name in _vscode_env_setting_names():
        env = settings.get(setting_name)
        if not isinstance(env, dict):
            continue
        for key, value in expected.items():
            if managed_routing and key in env:
                env.pop(key, None)
                changed = True
            elif env.get(key) == value:
                env.pop(key, None)
                changed = True
        if env:
            settings[setting_name] = env
        else:
            settings.pop(setting_name, None)

    if changed:
        _write_json_settings(path, settings)
    return changed


def _read_json_settings(path: Path) -> dict:
    text = path.read_text() if path.exists() else "{}"
    stripped = text.strip()
    if not stripped:
        return {}
    for candidate in (stripped, _strip_jsonc(stripped)):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
        raise ValueError("VS Code settings must be a JSON object")
    raise ValueError("invalid VS Code settings JSON")


def _write_json_settings(path: Path, settings: dict) -> None:
    path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")


def _strip_jsonc(text: str) -> str:
    output = []
    i = 0
    in_string = False
    escaped = False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue
        if char == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if char == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        output.append(char)
        i += 1
    without_comments = "".join(output)
    return re.sub(r",\s*([}\]])", r"\1", without_comments)


def _status_for_vscode(candidate: RoutingIntegrationCandidate, base: str) -> RoutingIntegrationStatus:
    backup = _backup_path(candidate.path)
    backup_exists = backup.exists()
    backup_matches_current = backup_exists and _files_match(candidate.path, backup)
    expected_url = _expected_base_url(candidate.integration_id, base)

    if not candidate.path.exists():
        recommendation = _recommendation_for("missing", False)
        return RoutingIntegrationStatus(
            integration_id=candidate.integration_id,
            label=candidate.label,
            provider=candidate.provider,
            kind=candidate.kind,
            path=str(candidate.path),
            exists=False,
            status="missing",
            gateway_base_url=base,
            expected_base_url=expected_url,
            backup_exists=backup_exists,
            backup_matches_current=backup_matches_current,
            **recommendation,
        )

    try:
        settings = _read_json_settings(candidate.path)
    except ValueError:
        return RoutingIntegrationStatus(
            integration_id=candidate.integration_id,
            label=candidate.label,
            provider=candidate.provider,
            kind=candidate.kind,
            path=str(candidate.path),
            exists=True,
            status="invalid",
            gateway_base_url=base,
            expected_base_url=expected_url,
            backup_exists=backup_exists,
            backup_matches_current=backup_matches_current,
            recommended_action="manual_fix",
            repair_available=False,
        )

    managed = _vscode_managed(settings)
    protected = managed and _vscode_settings_match(settings, base)
    if protected:
        status = "protected"
    elif managed:
        status = "partial"
    else:
        status = "unprotected"

    recommendation = _recommendation_for(status, managed)
    return RoutingIntegrationStatus(
        integration_id=candidate.integration_id,
        label=candidate.label,
        provider=candidate.provider,
        kind=candidate.kind,
        path=str(candidate.path),
        exists=True,
        status=status,
        gateway_base_url=base,
        expected_base_url=expected_url,
        backup_exists=backup_exists,
        backup_matches_current=backup_matches_current,
        managed_block_present=managed,
        api_key_configured=_vscode_api_key_configured(settings),
        **recommendation,
    )


def _backup_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".spectrona.bak")


def _backup(path: Path) -> Path:
    backup = _backup_path(path)
    if path.exists() and not backup.exists():
        backup.write_text(path.read_text())
    return backup


def _remove_managed_block(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    output = []
    in_block = False
    removed = False
    for line in lines:
        if line.strip() == BEGIN_MARKER:
            in_block = True
            removed = True
            continue
        if line.strip() == END_MARKER:
            in_block = False
            continue
        if not in_block:
            output.append(line)
    return "\n".join(output).rstrip() + ("\n" if output else ""), removed


def _managed_block(text: str) -> str:
    lines = []
    in_block = False
    for line in text.splitlines():
        if line.strip() == BEGIN_MARKER:
            in_block = True
            continue
        if line.strip() == END_MARKER:
            return "\n".join(lines)
        if in_block:
            lines.append(line)
    return ""


def _write_managed_block(path: Path, block: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup(path)
    existing = path.read_text() if path.exists() else ""
    cleaned, _ = _remove_managed_block(existing)
    cleaned = cleaned.rstrip()
    new_text = (cleaned + "\n\n" if cleaned else "") + block.rstrip() + "\n"
    path.write_text(new_text)


def _undo_managed_block(path: Path) -> bool:
    if not path.exists():
        return False
    cleaned, removed = _remove_managed_block(path.read_text())
    if removed:
        path.write_text(cleaned)
    return removed


def _files_match(first: Path, second: Path) -> bool:
    if not first.exists() or not second.exists():
        return False
    try:
        return first.read_bytes() == second.read_bytes()
    except OSError:
        return False
