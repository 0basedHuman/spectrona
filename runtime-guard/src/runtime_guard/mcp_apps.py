import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .mcp_config import WrapResult, is_wrapped_server, load_mcp_config, restore_backup, wrap_file


@dataclass(frozen=True)
class AppConfigCandidate:
    app_id: str
    label: str
    scope: str
    path: Path


@dataclass(frozen=True)
class AppMcpStatus:
    app_id: str
    label: str
    scope: str
    path: str
    exists: bool
    status: str
    servers: int = 0
    wrapped_servers: int = 0
    unwrapped_servers: int = 0
    skipped_servers: int = 0
    backup_exists: bool = False
    backup_matches_current: bool = False
    drift_detected: bool = False
    drift_reason: str = ""
    recommended_action: str = "none"
    repair_available: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "app_id": self.app_id,
            "label": self.label,
            "scope": self.scope,
            "path": self.path,
            "exists": self.exists,
            "status": self.status,
            "servers": self.servers,
            "wrapped_servers": self.wrapped_servers,
            "unwrapped_servers": self.unwrapped_servers,
            "skipped_servers": self.skipped_servers,
            "backup_exists": self.backup_exists,
            "backup_matches_current": self.backup_matches_current,
            "drift_detected": self.drift_detected,
            "drift_reason": self.drift_reason,
            "recommended_action": self.recommended_action,
            "repair_available": self.repair_available,
            "error": self.error,
        }


@dataclass(frozen=True)
class AppMcpMutationResult:
    app_id: str
    label: str
    path: str
    action: str
    changed: bool
    before_status: str
    after_status: str
    wrapped_servers: int = 0
    already_wrapped_servers: int = 0
    skipped_servers: int = 0
    backup_path: str = ""

    def to_dict(self) -> dict:
        return {
            "app_id": self.app_id,
            "label": self.label,
            "path": self.path,
            "action": self.action,
            "changed": self.changed,
            "before_status": self.before_status,
            "after_status": self.after_status,
            "wrapped_servers": self.wrapped_servers,
            "already_wrapped_servers": self.already_wrapped_servers,
            "skipped_servers": self.skipped_servers,
            "backup_path": self.backup_path,
        }


def discover_mcp_apps(repo_root: Path, home: Optional[Path] = None) -> list[AppMcpStatus]:
    root = repo_root.expanduser().resolve()
    base_home = (home or Path.home()).expanduser()
    return [_status_for(candidate) for candidate in _candidates(root, base_home)]


def supported_app_ids(repo_root: Path, home: Optional[Path] = None) -> list[str]:
    root = repo_root.expanduser().resolve()
    base_home = (home or Path.home()).expanduser()
    return [candidate.app_id for candidate in _candidates(root, base_home)]


def find_app_candidate(app_id: str, repo_root: Path, home: Optional[Path] = None) -> AppConfigCandidate:
    root = repo_root.expanduser().resolve()
    base_home = (home or Path.home()).expanduser()
    for candidate in _candidates(root, base_home):
        if candidate.app_id == app_id:
            return candidate
    supported = ", ".join(candidate.app_id for candidate in _candidates(root, base_home))
    raise ValueError(f"unsupported MCP app id: {app_id}. Supported ids: {supported}")


def protect_mcp_app(
    app_id: str,
    repo_root: Path,
    home: Optional[Path] = None,
    policy_path: Optional[Path] = None,
    audit_log: Optional[Path] = None,
    spectrona_command: str = "spectrona",
) -> AppMcpMutationResult:
    candidate = find_app_candidate(app_id, repo_root=repo_root, home=home)
    before = _status_for(candidate)
    if not before.exists:
        raise FileNotFoundError(f"MCP config not found for {candidate.label}: {candidate.path}")
    if before.status == "invalid":
        raise ValueError(before.error or f"MCP config is invalid: {candidate.path}")
    if before.status in {"protected", "empty"}:
        no_change = WrapResult(
            config={},
            wrapped=0,
            skipped=before.skipped_servers,
            already_wrapped=before.wrapped_servers,
        )
        return _mutation_result(
            candidate=candidate,
            action="protect",
            changed=False,
            before=before,
            after=before,
            wrap_result=no_change,
            backup_path=Path(str(candidate.path) + ".spectrona.bak") if before.backup_exists else None,
        )

    wrap_result, _written, backup = wrap_file(
        input_path=candidate.path,
        repo_root=repo_root.expanduser().resolve(),
        output_path=None,
        apply=True,
        spectrona_command=spectrona_command,
        policy_path=policy_path,
        audit_log=audit_log,
    )
    after = _status_for(candidate)
    return _mutation_result(
        candidate=candidate,
        action="protect",
        changed=True,
        before=before,
        after=after,
        wrap_result=wrap_result,
        backup_path=backup,
    )


def unprotect_mcp_app(
    app_id: str,
    repo_root: Path,
    home: Optional[Path] = None,
    backup_path: Optional[Path] = None,
) -> AppMcpMutationResult:
    candidate = find_app_candidate(app_id, repo_root=repo_root, home=home)
    before = _status_for(candidate)

    backup = restore_backup(candidate.path, backup_path)
    after = _status_for(candidate)
    return AppMcpMutationResult(
        app_id=candidate.app_id,
        label=candidate.label,
        path=str(candidate.path),
        action="unprotect",
        changed=True,
        before_status=before.status,
        after_status=after.status,
        backup_path=str(backup),
    )


def statuses_to_json(statuses: list[AppMcpStatus]) -> str:
    return json.dumps([status.to_dict() for status in statuses], indent=2)


def mutation_to_json(result: AppMcpMutationResult) -> str:
    return json.dumps(result.to_dict(), indent=2)


def _candidates(repo_root: Path, home: Path) -> list[AppConfigCandidate]:
    return [
        AppConfigCandidate(
            app_id="claude-code",
            label="Claude Code",
            scope="user",
            path=home / ".claude" / "mcp.json",
        ),
        AppConfigCandidate(
            app_id="claude-desktop",
            label="Claude Desktop",
            scope="user",
            path=home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        ),
        AppConfigCandidate(
            app_id="codex",
            label="Codex",
            scope="user",
            path=home / ".codex" / "mcp.json",
        ),
        AppConfigCandidate(
            app_id="vscode-user",
            label="VS Code",
            scope="user",
            path=home / "Library" / "Application Support" / "Code" / "User" / "mcp.json",
        ),
        AppConfigCandidate(
            app_id="workspace-claude",
            label="Workspace Claude",
            scope="workspace",
            path=repo_root / ".claude" / "mcp.json",
        ),
        AppConfigCandidate(
            app_id="workspace-mcp",
            label="Workspace MCP",
            scope="workspace",
            path=repo_root / ".mcp.json",
        ),
        AppConfigCandidate(
            app_id="workspace-vscode",
            label="Workspace VS Code",
            scope="workspace",
            path=repo_root / ".vscode" / "mcp.json",
        ),
    ]


def _status_for(candidate: AppConfigCandidate) -> AppMcpStatus:
    backup_path = Path(str(candidate.path) + ".spectrona.bak")
    backup_exists = backup_path.exists()
    backup_matches_current = backup_exists and _files_match(candidate.path, backup_path)
    if not candidate.path.exists():
        drift = _recommendation_for("missing", backup_exists, backup_matches_current)
        return AppMcpStatus(
            app_id=candidate.app_id,
            label=candidate.label,
            scope=candidate.scope,
            path=str(candidate.path),
            exists=False,
            status="missing",
            backup_exists=backup_exists,
            backup_matches_current=backup_matches_current,
            **drift,
        )

    try:
        data = load_mcp_config(candidate.path)
    except Exception as exc:
        drift = _recommendation_for("invalid", backup_exists, backup_matches_current)
        return AppMcpStatus(
            app_id=candidate.app_id,
            label=candidate.label,
            scope=candidate.scope,
            path=str(candidate.path),
            exists=True,
            status="invalid",
            backup_exists=backup_exists,
            backup_matches_current=backup_matches_current,
            **drift,
            error=f"could not parse MCP config: {exc}",
        )

    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        drift = _recommendation_for("invalid", backup_exists, backup_matches_current)
        return AppMcpStatus(
            app_id=candidate.app_id,
            label=candidate.label,
            scope=candidate.scope,
            path=str(candidate.path),
            exists=True,
            status="invalid",
            backup_exists=backup_exists,
            backup_matches_current=backup_matches_current,
            **drift,
            error="mcpServers must be a JSON object",
        )

    wrapped = 0
    unwrapped = 0
    skipped = 0
    for server in servers.values():
        if not isinstance(server, dict):
            skipped += 1
        elif is_wrapped_server(server):
            wrapped += 1
        else:
            unwrapped += 1

    if not servers:
        status = "empty"
    elif wrapped and unwrapped:
        status = "partial"
    elif wrapped and not unwrapped:
        status = "protected"
    else:
        status = "unprotected"

    drift = _recommendation_for(status, backup_exists, backup_matches_current)
    return AppMcpStatus(
        app_id=candidate.app_id,
        label=candidate.label,
        scope=candidate.scope,
        path=str(candidate.path),
        exists=True,
        status=status,
        servers=len(servers),
        wrapped_servers=wrapped,
        unwrapped_servers=unwrapped,
        skipped_servers=skipped,
        backup_exists=backup_exists,
        backup_matches_current=backup_matches_current,
        **drift,
    )


def _files_match(first: Path, second: Path) -> bool:
    if not first.exists() or not second.exists():
        return False
    try:
        return first.read_bytes() == second.read_bytes()
    except OSError:
        return False


def _recommendation_for(status: str, backup_exists: bool, backup_matches_current: bool) -> dict:
    drift_detected = False
    drift_reason = ""
    recommended_action = "none"

    if status == "partial":
        drift_detected = True
        drift_reason = "some MCP servers bypass Spectrona"
        recommended_action = "repair"
    elif status == "unprotected":
        if backup_exists and not backup_matches_current:
            drift_detected = True
            drift_reason = "MCP config changed after Spectrona backup and now bypasses Spectrona"
            recommended_action = "repair"
        else:
            recommended_action = "protect"
    elif status == "invalid":
        if backup_exists:
            drift_detected = True
            drift_reason = "MCP config is invalid but a Spectrona backup exists"
            recommended_action = "restore"
        else:
            recommended_action = "inspect"
    elif status == "missing" and backup_exists:
        drift_detected = True
        drift_reason = "MCP config is missing but a Spectrona backup exists"
        recommended_action = "restore"
    elif status == "empty" and backup_exists and not backup_matches_current:
        drift_detected = True
        drift_reason = "MCP config was cleared after Spectrona backup"
        recommended_action = "restore"

    return {
        "drift_detected": drift_detected,
        "drift_reason": drift_reason,
        "recommended_action": recommended_action,
        "repair_available": recommended_action in {"protect", "repair", "restore"},
    }


def _mutation_result(
    candidate: AppConfigCandidate,
    action: str,
    changed: bool,
    before: AppMcpStatus,
    after: AppMcpStatus,
    wrap_result: WrapResult,
    backup_path: Optional[Path],
) -> AppMcpMutationResult:
    return AppMcpMutationResult(
        app_id=candidate.app_id,
        label=candidate.label,
        path=str(candidate.path),
        action=action,
        changed=changed,
        before_status=before.status,
        after_status=after.status,
        wrapped_servers=wrap_result.wrapped,
        already_wrapped_servers=wrap_result.already_wrapped,
        skipped_servers=wrap_result.skipped,
        backup_path=str(backup_path) if backup_path else "",
    )
