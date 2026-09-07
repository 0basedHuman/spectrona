import sys
from pathlib import Path
from typing import Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_runtime_guard_importable() -> None:
    root = _repo_root()
    for src in (
        root / "spectrona-detection" / "src",
        root / "runtime-guard" / "src",
        root / "policy-engine" / "src",
    ):
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))


def proxy(
    policy_path: Optional[str],
    repo_root: Optional[str],
    client: Optional[str],
    audit_log: Optional[str],
    dry_run: bool,
    enforce: bool,
    upstream: Optional[list],
) -> int:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_proxy import ProxyConfig, serve_stdio

    if upstream and upstream[0] == "--":
        upstream = upstream[1:]

    config = ProxyConfig.from_environment(
        policy_path=policy_path,
        repo_root=repo_root,
        client=client,
        audit_log=audit_log,
        policy_dry_run=False if enforce else True if dry_run else None,
    )
    return serve_stdio(config, upstream_command=upstream or None)


def wrap(
    file_path: Optional[str],
    repo_root: Optional[str],
    output_path: Optional[str],
    apply: bool,
    force: bool,
    policy_path: Optional[str],
    audit_log: Optional[str],
    spectrona_command: str,
) -> int:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_config import find_mcp_config, wrap_file

    root = Path(repo_root).expanduser().resolve() if repo_root else Path.cwd().resolve()
    target = Path(file_path).expanduser() if file_path else find_mcp_config(root)
    if target is None:
        print("No MCP config found. Use: spectrona mcp wrap <path> --output <wrapped-path>")
        return 0
    if not target.exists():
        print(f"Error: MCP config not found: {target}", file=sys.stderr)
        return 2
    if apply and output_path:
        print("Error: use either --apply or --output, not both.", file=sys.stderr)
        return 2
    if not apply and not output_path:
        print("Error: wrap requires --output or --apply. Refusing to print MCP config to terminal.", file=sys.stderr)
        return 2

    try:
        result, written, backup = wrap_file(
            input_path=target,
            repo_root=root,
            output_path=Path(output_path).expanduser() if output_path else None,
            apply=apply,
            force=force,
            spectrona_command=spectrona_command,
            policy_path=Path(policy_path).expanduser() if policy_path else None,
            audit_log=Path(audit_log).expanduser() if audit_log else None,
        )
    except Exception as exc:
        print(f"Error: could not wrap MCP config: {exc}", file=sys.stderr)
        return 2

    action = "Applied" if apply else "Wrote"
    print(f"{action} Spectrona MCP wrapper config: {written}")
    if backup:
        print(f"Backup: {backup}")
    print(f"Wrapped servers: {result.wrapped}")
    print(f"Already wrapped: {result.already_wrapped}")
    print(f"Skipped servers: {result.skipped}")
    return 0


def undo(file_path: str, backup_path: Optional[str]) -> int:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_config import restore_backup

    target = Path(file_path).expanduser()
    try:
        backup = restore_backup(target, Path(backup_path).expanduser() if backup_path else None)
    except Exception as exc:
        print(f"Error: could not restore MCP config backup: {exc}", file=sys.stderr)
        return 2
    print(f"Restored MCP config: {target}")
    print(f"Backup used: {backup}")
    return 0


def apps(repo_root: Optional[str], home: Optional[str], output_json: bool) -> int:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_apps import discover_mcp_apps, statuses_to_json

    root = Path(repo_root).expanduser().resolve() if repo_root else Path.cwd().resolve()
    home_path = Path(home).expanduser() if home else None
    statuses = discover_mcp_apps(repo_root=root, home=home_path)

    if output_json:
        print(statuses_to_json(statuses))
        return 0

    print("Spectrona MCP app status")
    print("─" * 72)
    for status in statuses:
        marker = _status_marker(status.status)
        print(f"{marker} {status.label:<18} {status.scope:<9} {status.status:<11} {status.servers} servers")
        print(f"    {status.path}")
        if status.exists and status.status not in {"invalid", "missing"}:
            print(
                f"    wrapped={status.wrapped_servers} "
                f"unwrapped={status.unwrapped_servers} "
                f"skipped={status.skipped_servers} "
                f"backup={'yes' if status.backup_exists else 'no'}"
            )
        elif status.error:
            print(f"    {status.error}")
        if status.drift_detected:
            print(f"    drift=yes action={status.recommended_action} reason={status.drift_reason}")
        elif status.recommended_action != "none":
            print(f"    action={status.recommended_action}")
    return 0


def protect_app(
    app_id: str,
    repo_root: Optional[str],
    home: Optional[str],
    policy_path: Optional[str],
    audit_log: Optional[str],
    spectrona_command: str,
    output_json: bool,
) -> int:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_apps import mutation_to_json, protect_mcp_app

    root = Path(repo_root).expanduser().resolve() if repo_root else Path.cwd().resolve()
    home_path = Path(home).expanduser() if home else None
    try:
        result = protect_mcp_app(
            app_id=app_id,
            repo_root=root,
            home=home_path,
            policy_path=Path(policy_path).expanduser() if policy_path else None,
            audit_log=Path(audit_log).expanduser() if audit_log else None,
            spectrona_command=spectrona_command,
        )
    except Exception as exc:
        print(f"Error: could not protect MCP app: {exc}", file=sys.stderr)
        return 2

    if output_json:
        print(mutation_to_json(result))
        return 0
    _print_mutation_result(result)
    return 0


def unprotect_app(
    app_id: str,
    repo_root: Optional[str],
    home: Optional[str],
    backup_path: Optional[str],
    output_json: bool,
) -> int:
    _ensure_runtime_guard_importable()
    from runtime_guard.mcp_apps import mutation_to_json, unprotect_mcp_app

    root = Path(repo_root).expanduser().resolve() if repo_root else Path.cwd().resolve()
    home_path = Path(home).expanduser() if home else None
    try:
        result = unprotect_mcp_app(
            app_id=app_id,
            repo_root=root,
            home=home_path,
            backup_path=Path(backup_path).expanduser() if backup_path else None,
        )
    except Exception as exc:
        print(f"Error: could not unprotect MCP app: {exc}", file=sys.stderr)
        return 2

    if output_json:
        print(mutation_to_json(result))
        return 0
    _print_mutation_result(result)
    return 0


def _status_marker(status: str) -> str:
    if status == "protected":
        return "[ok]"
    if status in {"unprotected", "partial"}:
        return "[!]"
    if status == "invalid":
        return "[x]"
    return "[-]"


def _print_mutation_result(result) -> None:
    verb = "Protected" if result.action == "protect" else "Unprotected"
    if not result.changed and result.action == "protect":
        verb = "Already protected"
    print(f"{verb} MCP app: {result.label}")
    print(f"Path: {result.path}")
    print(f"Status: {result.before_status} -> {result.after_status}")
    if result.backup_path:
        print(f"Backup: {result.backup_path}")
    print(f"Changed: {'yes' if result.changed else 'no'}")
    print(f"Wrapped servers: {result.wrapped_servers}")
    print(f"Already wrapped: {result.already_wrapped_servers}")
    print(f"Skipped servers: {result.skipped_servers}")
