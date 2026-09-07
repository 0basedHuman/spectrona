import argparse
import sys

from . import secrets as secrets_cmd
from .commands import gateway, init, integrations, logs, mcp, policy, protect, scan, service, status


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="spectrona",
        description="Spectrona — local-first AI security control plane",
    )
    sub = parser.add_subparsers(dest="command")

    init_p = sub.add_parser("init", help="Create default Spectrona local config")
    init_p.add_argument("--force", action="store_true", help="Rewrite existing config")

    start_p = sub.add_parser("start", help="Start the local gateway in the background")
    start_p.add_argument("-f", "--foreground", action="store_true", help="Run gateway in the foreground")
    sub.add_parser("stop", help="Stop the local gateway")
    restart_p = sub.add_parser("restart", help="Restart the local gateway in the background")
    restart_p.add_argument("-f", "--foreground", action="store_true", help="Restart in the foreground")

    sub.add_parser("status", help="Show gateway and scanner status")
    secrets_p = sub.add_parser("secrets", help="Manage stored provider API keys")
    secrets_p.add_argument("secrets_args", nargs=argparse.REMAINDER)

    service_p = sub.add_parser("service", help="Manage macOS LaunchAgent service files")
    service_sub = service_p.add_subparsers(dest="service_cmd")
    service_sub.add_parser("print", help="Print LaunchAgent plist")
    service_install = service_sub.add_parser("install", help="Write LaunchAgent plist")
    service_install.add_argument("--path", help="Override plist path")
    service_load = service_sub.add_parser("load", help="Load LaunchAgent with launchctl")
    service_load.add_argument("--path", help="Override plist path")
    service_load.add_argument("--dry-run", action="store_true", help="Print launchctl command without running it")
    service_unload = service_sub.add_parser("unload", help="Unload LaunchAgent with launchctl")
    service_unload.add_argument("--path", help="Override plist path")
    service_unload.add_argument("--dry-run", action="store_true", help="Print launchctl command without running it")
    service_uninstall = service_sub.add_parser("uninstall", help="Remove LaunchAgent plist")
    service_uninstall.add_argument("--path", help="Override plist path")

    integrations_p = sub.add_parser("integrations", help="Inspect and repair app/provider integrations")
    integrations_sub = integrations_p.add_subparsers(dest="integrations_cmd")
    integrations_status = integrations_sub.add_parser("status", help="Show aggregate integration status")
    integrations_status.add_argument("--repo-root", help="Repository root for workspace MCP config discovery")
    integrations_status.add_argument("--home", help="Override home directory for app config discovery")
    integrations_status.add_argument("--live", action="store_true", help="Check local LLM runtime endpoints")
    integrations_status.add_argument("--json", action="store_true", help="Output JSON status")
    integrations_repair = integrations_sub.add_parser("repair", help="Repair actionable app/provider integrations")
    integrations_repair.add_argument("--repo-root", help="Repository root for workspace MCP config discovery")
    integrations_repair.add_argument("--home", help="Override home directory for app config discovery")
    integrations_repair.add_argument("--policy", help="Policy YAML path passed to repaired MCP proxies")
    integrations_repair.add_argument("--audit-log", help="MCP audit JSONL path passed to repaired MCP proxies")
    integrations_repair.add_argument("--spectrona-command", default="spectrona", help="Command used by MCP clients to start Spectrona")
    integrations_repair.add_argument("--confirm", action="store_true", help="Confirm integration config mutations")
    integrations_repair.add_argument("--json", action="store_true", help="Output JSON repair result")

    policy_p = sub.add_parser("policy", help="Inspect and manage local policy")
    policy_sub = policy_p.add_subparsers(dest="policy_cmd")
    policy_status = policy_sub.add_parser("status", help="Show active local policy")
    policy_status.add_argument("--path", help="Override policy path")
    policy_status.add_argument("--json", action="store_true", help="Output JSON status")
    policy_presets = policy_sub.add_parser("presets", help="List built-in policy presets")
    policy_presets.add_argument("--json", action="store_true", help="Output JSON presets")
    policy_apply = policy_sub.add_parser("apply", help="Apply a policy preset")
    policy_apply.add_argument("preset_id", help="Preset id: relaxed, balanced, or strict")
    policy_apply.add_argument("--path", help="Override policy path")
    policy_apply.add_argument("--confirm", action="store_true", help="Confirm policy file mutation")
    policy_apply.add_argument("--json", action="store_true", help="Output JSON mutation result")
    policy_backups = policy_sub.add_parser("backups", help="List policy backups")
    policy_backups.add_argument("--path", help="Override policy path")
    policy_backups.add_argument("--json", action="store_true", help="Output JSON backups")
    policy_restore = policy_sub.add_parser("restore", help="Restore a policy backup")
    policy_restore.add_argument("backup_id", help="Backup id from `spectrona policy backups`, or a backup file path")
    policy_restore.add_argument("--path", help="Override active policy path")
    policy_restore.add_argument("--confirm", action="store_true", help="Confirm policy file mutation")
    policy_restore.add_argument("--json", action="store_true", help="Output JSON mutation result")

    scan_p = sub.add_parser("scan", help="Run local security scans")
    scan_sub = scan_p.add_subparsers(dest="scan_cmd")
    mcp_p = scan_sub.add_parser("mcp", help="Scan an MCP config")
    mcp_p.add_argument("file", nargs="?", help="Path to MCP config JSON file")
    mcp_p.add_argument("--repo-root", help="Project root for filesystem boundary checks")
    mcp_p.add_argument("--json", action="store_true", help="Output JSON report")
    mcp_p.add_argument("--html", action="store_true", help="Output HTML report")
    mcp_p.add_argument("--output", help="Write JSON or HTML report to file")
    claude_scan_p = scan_sub.add_parser("claude", help="Scan Claude project/user configs")
    claude_scan_p.add_argument("file", nargs="?", help="Path to CLAUDE.md, Claude settings JSON, or a project directory")
    claude_scan_p.add_argument("--repo-root", help="Project root for default Claude config discovery")
    claude_scan_p.add_argument("--json", action="store_true", help="Output JSON report")
    claude_scan_p.add_argument("--html", action="store_true", help="Output HTML report")
    claude_scan_p.add_argument("--output", help="Write JSON or HTML report to file")
    cursor_scan_p = scan_sub.add_parser("cursor", help="Scan Cursor project/user configs")
    cursor_scan_p.add_argument("file", nargs="?", help="Path to Cursor config file or a project directory")
    cursor_scan_p.add_argument("--repo-root", help="Project root for default Cursor config discovery")
    cursor_scan_p.add_argument("--json", action="store_true", help="Output JSON report")
    cursor_scan_p.add_argument("--html", action="store_true", help="Output HTML report")
    cursor_scan_p.add_argument("--output", help="Write JSON or HTML report to file")
    repo_scan_p = scan_sub.add_parser("repo", help="Scan repository files")
    repo_scan_p.add_argument("file", nargs="?", help="Path to a repository directory or file")
    repo_scan_p.add_argument("--repo-root", help="Repository root for git-tracking checks")
    repo_scan_p.add_argument("--json", action="store_true", help="Output JSON report")
    repo_scan_p.add_argument("--html", action="store_true", help="Output HTML report")
    repo_scan_p.add_argument("--output", help="Write JSON or HTML report to file")

    gw = sub.add_parser("gateway", help="Manage the local gateway")
    gw_sub = gw.add_subparsers(dest="gw_cmd")
    gw_start = gw_sub.add_parser("start", help="Start the gateway")
    gw_start.add_argument("-d", "--background", action="store_true", help="Run gateway in the background")
    gw_sub.add_parser("stop", help="Stop a background gateway")
    gw_restart = gw_sub.add_parser("restart", help="Restart the gateway in the background")
    gw_restart.add_argument("-f", "--foreground", action="store_true", help="Restart in the foreground")
    gw_sub.add_parser("health", help="Check gateway health")

    mcp_p = sub.add_parser("mcp", help="Run MCP runtime controls")
    mcp_sub = mcp_p.add_subparsers(dest="mcp_cmd")
    mcp_proxy = mcp_sub.add_parser(
        "proxy",
        help="Run the Spectrona MCP stdio proxy",
        description="Run the Spectrona MCP stdio proxy",
    )
    mcp_proxy.add_argument("--policy", help="Policy YAML path")
    mcp_proxy.add_argument("--repo-root", help="Repository root for filesystem-risk decisions")
    mcp_proxy.add_argument("--client", help="Client/app name for policy and audit context")
    mcp_proxy.add_argument("--audit-log", help="MCP audit JSONL path")
    proxy_mode = mcp_proxy.add_mutually_exclusive_group()
    proxy_mode.add_argument("--dry-run", action="store_true", help="Audit policy decisions without blocking MCP traffic. This is the default.")
    proxy_mode.add_argument("--enforce", action="store_true", help="Explicitly allow the MCP proxy to block or redact traffic.")
    mcp_proxy.add_argument("upstream", nargs=argparse.REMAINDER, help="Optional upstream MCP server command after --")
    mcp_wrap = mcp_sub.add_parser("wrap", help="Wrap an MCP config so servers run through Spectrona")
    mcp_wrap.add_argument("file", nargs="?", help="Path to MCP config JSON file")
    mcp_wrap.add_argument("--repo-root", help="Repository root for filesystem-risk decisions")
    mcp_wrap.add_argument("--output", help="Write wrapped config to this path")
    mcp_wrap.add_argument("--apply", action="store_true", help="Rewrite the source config after creating a backup")
    mcp_wrap.add_argument("--force", action="store_true", help="Overwrite an existing --output file")
    mcp_wrap.add_argument("--policy", help="Policy YAML path passed to the MCP proxy")
    mcp_wrap.add_argument("--audit-log", help="MCP audit JSONL path passed to the MCP proxy")
    mcp_wrap.add_argument("--spectrona-command", default="spectrona", help="Command used by MCP clients to start Spectrona")
    mcp_undo = mcp_sub.add_parser("undo", help="Restore an MCP config from its Spectrona backup")
    mcp_undo.add_argument("file", help="Path to MCP config JSON file")
    mcp_undo.add_argument("--backup", help="Override backup path")
    mcp_apps = mcp_sub.add_parser("apps", help="Show detected app MCP protection status")
    mcp_apps.add_argument("--repo-root", help="Repository root for workspace MCP config discovery")
    mcp_apps.add_argument("--home", help="Override home directory for app config discovery")
    mcp_apps.add_argument("--json", action="store_true", help="Output JSON status")
    mcp_protect = mcp_sub.add_parser("protect", help="Protect a detected app MCP config")
    mcp_protect.add_argument("app_id", help="App id from `spectrona mcp apps`, for example claude-code")
    mcp_protect.add_argument("--repo-root", help="Repository root for filesystem-risk decisions")
    mcp_protect.add_argument("--home", help="Override home directory for app config discovery")
    mcp_protect.add_argument("--policy", help="Policy YAML path passed to the MCP proxy")
    mcp_protect.add_argument("--audit-log", help="MCP audit JSONL path passed to the MCP proxy")
    mcp_protect.add_argument("--spectrona-command", default="spectrona", help="Command used by MCP clients to start Spectrona")
    mcp_protect.add_argument("--json", action="store_true", help="Output JSON mutation result")
    mcp_unprotect = mcp_sub.add_parser("unprotect", help="Restore a detected app MCP config from its Spectrona backup")
    mcp_unprotect.add_argument("app_id", help="App id from `spectrona mcp apps`, for example claude-code")
    mcp_unprotect.add_argument("--repo-root", help="Repository root for workspace MCP config discovery")
    mcp_unprotect.add_argument("--home", help="Override home directory for app config discovery")
    mcp_unprotect.add_argument("--backup", help="Override backup path")
    mcp_unprotect.add_argument("--json", action="store_true", help="Output JSON mutation result")

    log_p = sub.add_parser("logs", help="View audit logs")
    log_sub = log_p.add_subparsers(dest="log_cmd")
    tail_p = log_sub.add_parser("tail", help="Tail the audit log")
    tail_p.add_argument("-n", type=int, default=20, help="Number of events (default 20)")

    protect_p = sub.add_parser("protect", help="Print setup instructions")
    protect_sub = protect_p.add_subparsers(dest="protect_cmd")
    protect_status = protect_sub.add_parser("status", help="Show Claude/Codex provider routing status")
    protect_status.add_argument("--json", action="store_true", help="Output JSON status")
    claude_p = protect_sub.add_parser("claude", help="Print Claude Code routing config")
    claude_p.add_argument("--print", action="store_true", default=True)
    claude_p.add_argument("--apply", action="store_true", help="Write reversible Claude routing env file")
    claude_p.add_argument("--undo", action="store_true", help="Remove Spectrona Claude routing block")
    claude_p.add_argument("--path", help="Target env file path")
    codex_p = protect_sub.add_parser("codex", help="Print Codex routing config")
    codex_p.add_argument("--print", action="store_true", default=True)
    codex_p.add_argument("--apply", action="store_true", help="Patch Codex config with a reversible routing block")
    codex_p.add_argument("--undo", action="store_true", help="Remove Spectrona Codex routing block")
    codex_p.add_argument("--path", help="Target Codex config path")
    vscode_p = protect_sub.add_parser("vscode", help="Print VS Code workspace routing config")
    vscode_p.add_argument("--print", action="store_true", default=True)
    vscode_p.add_argument("--apply", action="store_true", help="Patch VS Code workspace settings with reversible routing settings")
    vscode_p.add_argument("--undo", action="store_true", help="Remove Spectrona VS Code routing settings")
    vscode_p.add_argument("--path", help="Target VS Code settings.json path")

    args = parser.parse_args()

    if args.command == "init":
        sys.exit(init.run(args.force))
    elif args.command == "start":
        sys.exit(gateway.start(background=not args.foreground))
    elif args.command == "stop":
        sys.exit(gateway.stop())
    elif args.command == "restart":
        sys.exit(gateway.restart(background=not args.foreground))
    elif args.command == "status":
        status.run()
    elif args.command == "secrets":
        sys.exit(secrets_cmd.command(args.secrets_args))
    elif args.command == "service":
        if getattr(args, "service_cmd", None) == "print":
            sys.exit(service.print_plist())
        elif getattr(args, "service_cmd", None) == "install":
            sys.exit(service.install(args.path))
        elif getattr(args, "service_cmd", None) == "load":
            sys.exit(service.load(args.path, args.dry_run))
        elif getattr(args, "service_cmd", None) == "unload":
            sys.exit(service.unload(args.path, args.dry_run))
        elif getattr(args, "service_cmd", None) == "uninstall":
            sys.exit(service.uninstall(args.path))
        else:
            service_p.print_help()
    elif args.command == "integrations":
        if getattr(args, "integrations_cmd", None) == "status":
            sys.exit(integrations.status(args.repo_root, args.home, args.live, args.json))
        elif getattr(args, "integrations_cmd", None) == "repair":
            sys.exit(integrations.repair(
                repo_root=args.repo_root,
                home=args.home,
                policy_path=args.policy,
                audit_log=args.audit_log,
                spectrona_command=args.spectrona_command,
                confirm=args.confirm,
                output_json=args.json,
            ))
        else:
            integrations_p.print_help()
    elif args.command == "policy":
        if getattr(args, "policy_cmd", None) == "status":
            sys.exit(policy.status(args.path, args.json))
        elif getattr(args, "policy_cmd", None) == "presets":
            sys.exit(policy.presets(args.json))
        elif getattr(args, "policy_cmd", None) == "apply":
            sys.exit(policy.apply_preset(args.path, args.preset_id, args.confirm, args.json))
        elif getattr(args, "policy_cmd", None) == "backups":
            sys.exit(policy.backups(args.path, args.json))
        elif getattr(args, "policy_cmd", None) == "restore":
            sys.exit(policy.restore(args.path, args.backup_id, args.confirm, args.json))
        else:
            policy_p.print_help()
    elif args.command == "scan":
        if getattr(args, "scan_cmd", None) == "mcp":
            sys.exit(scan.mcp(args.file, args.repo_root, args.json, args.html, args.output))
        elif getattr(args, "scan_cmd", None) == "claude":
            sys.exit(scan.claude(args.file, args.repo_root, args.json, args.html, args.output))
        elif getattr(args, "scan_cmd", None) == "cursor":
            sys.exit(scan.cursor(args.file, args.repo_root, args.json, args.html, args.output))
        elif getattr(args, "scan_cmd", None) == "repo":
            sys.exit(scan.repo(args.file, args.repo_root, args.json, args.html, args.output))
        else:
            scan_p.print_help()
    elif args.command == "gateway":
        if getattr(args, "gw_cmd", None) == "start":
            sys.exit(gateway.start(background=args.background))
        elif getattr(args, "gw_cmd", None) == "stop":
            sys.exit(gateway.stop())
        elif getattr(args, "gw_cmd", None) == "restart":
            sys.exit(gateway.restart(background=not args.foreground))
        elif getattr(args, "gw_cmd", None) == "health":
            gateway.health()
        else:
            gw.print_help()
    elif args.command == "mcp":
        if getattr(args, "mcp_cmd", None) == "proxy":
            sys.exit(mcp.proxy(
                policy_path=args.policy,
                repo_root=args.repo_root,
                client=args.client,
                audit_log=args.audit_log,
                dry_run=args.dry_run,
                enforce=args.enforce,
                upstream=args.upstream,
            ))
        elif getattr(args, "mcp_cmd", None) == "wrap":
            sys.exit(mcp.wrap(
                file_path=args.file,
                repo_root=args.repo_root,
                output_path=args.output,
                apply=args.apply,
                force=args.force,
                policy_path=args.policy,
                audit_log=args.audit_log,
                spectrona_command=args.spectrona_command,
            ))
        elif getattr(args, "mcp_cmd", None) == "undo":
            sys.exit(mcp.undo(args.file, args.backup))
        elif getattr(args, "mcp_cmd", None) == "apps":
            sys.exit(mcp.apps(args.repo_root, args.home, args.json))
        elif getattr(args, "mcp_cmd", None) == "protect":
            sys.exit(mcp.protect_app(
                app_id=args.app_id,
                repo_root=args.repo_root,
                home=args.home,
                policy_path=args.policy,
                audit_log=args.audit_log,
                spectrona_command=args.spectrona_command,
                output_json=args.json,
            ))
        elif getattr(args, "mcp_cmd", None) == "unprotect":
            sys.exit(mcp.unprotect_app(
                app_id=args.app_id,
                repo_root=args.repo_root,
                home=args.home,
                backup_path=args.backup,
                output_json=args.json,
            ))
        else:
            mcp_p.print_help()
    elif args.command == "logs":
        if getattr(args, "log_cmd", None) == "tail":
            logs.tail(args.n)
        else:
            logs.tail()
    elif args.command == "protect":
        if getattr(args, "protect_cmd", None) == "status":
            sys.exit(protect.status(output_json=args.json))
        elif getattr(args, "protect_cmd", None) == "claude":
            sys.exit(protect.claude(
                print_only=args.print,
                apply=args.apply,
                undo=args.undo,
                path=args.path,
            ))
        elif getattr(args, "protect_cmd", None) == "codex":
            sys.exit(protect.codex(
                print_only=args.print,
                apply=args.apply,
                undo=args.undo,
                path=args.path,
            ))
        elif getattr(args, "protect_cmd", None) == "vscode":
            sys.exit(protect.vscode(
                print_only=args.print,
                apply=args.apply,
                undo=args.undo,
                path=args.path,
            ))
        else:
            protect_p.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
