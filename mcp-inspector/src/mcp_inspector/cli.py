import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from .parsers.claude_parser import discover_claude_files
from .parsers.cursor_parser import discover_cursor_files
from .scanner import scan_claude_config, scan_cursor_config, scan_mcp_config, scan_repo
from .reporters import html_reporter, json_reporter
from .reporters import terminal as term_reporter

_LOCAL_SEARCH = [".claude/mcp.json", ".mcp.json", "mcp.json"]
_GLOBAL_SEARCH = [Path.home() / ".claude" / "mcp.json"]


def _find_mcp_config(repo_root: Path) -> Optional[Path]:
    for rel in _LOCAL_SEARCH:
        p = repo_root / rel
        if p.exists():
            return p
    for p in _GLOBAL_SEARCH:
        if p.exists():
            return p
    return None


def _run_mcp_scan(args) -> int:
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(os.getcwd())

    if args.file:
        config_path = Path(args.file)
        if not config_path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 2
    else:
        config_path = _find_mcp_config(repo_root)
        if config_path is None:
            print(
                "No MCP config found. Searched: " + ", ".join(_LOCAL_SEARCH),
                file=sys.stderr,
            )
            print("Use --file to specify a config path.", file=sys.stderr)
            return 0

    try:
        findings = scan_mcp_config(str(config_path), str(repo_root))
    except Exception as e:
        print(f"Error: could not parse {config_path}: {e}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, str(config_path), args)
    if output_result is not None:
        return output_result

    has_critical_or_high = any(f.severity in ("critical", "high") for f in findings)
    return 1 if has_critical_or_high else 0


def _run_claude_scan(args) -> int:
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(os.getcwd())

    if args.file:
        config_path = Path(args.file).expanduser()
        if not config_path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 2
        if config_path.is_dir() and not discover_claude_files(str(config_path), include_global=False):
            print(f"No Claude config found under: {config_path}", file=sys.stderr)
            return 0
        scan_target = str(config_path)
        file_arg = str(config_path)
    else:
        found = discover_claude_files(str(repo_root))
        if not found:
            searched = ", ".join(["CLAUDE.md", ".claude/settings.json", ".claude/settings.local.json"])
            print(f"No Claude config found. Searched: {searched}", file=sys.stderr)
            print("Use --file to specify a CLAUDE.md or Claude settings path.", file=sys.stderr)
            return 0
        scan_target = "claude:" + ", ".join(found)
        file_arg = None

    try:
        findings = scan_claude_config(file_arg, str(repo_root))
    except Exception as e:
        print(f"Error: could not parse {scan_target}: {e}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, scan_target, args)
    if output_result is not None:
        return output_result

    has_critical_or_high = any(f.severity in ("critical", "high") for f in findings)
    return 1 if has_critical_or_high else 0


def _run_cursor_scan(args) -> int:
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(os.getcwd())

    if args.file:
        config_path = Path(args.file).expanduser()
        if not config_path.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 2
        if config_path.is_dir() and not discover_cursor_files(str(config_path), include_global=False):
            print(f"No Cursor config found under: {config_path}", file=sys.stderr)
            return 0
        scan_target = str(config_path)
        file_arg = str(config_path)
    else:
        found = discover_cursor_files(str(repo_root))
        if not found:
            searched = ", ".join([".cursor/settings.json", ".cursorrules", ".cursor/rules", ".cursor/mcp.json"])
            print(f"No Cursor config found. Searched: {searched}", file=sys.stderr)
            print("Use --file to specify a Cursor config path.", file=sys.stderr)
            return 0
        scan_target = "cursor:" + ", ".join(found)
        file_arg = None

    try:
        findings = scan_cursor_config(file_arg, str(repo_root))
    except Exception as e:
        print(f"Error: could not parse {scan_target}: {e}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, scan_target, args)
    if output_result is not None:
        return output_result

    has_critical_or_high = any(f.severity in ("critical", "high") for f in findings)
    return 1 if has_critical_or_high else 0


def _run_repo_scan(args) -> int:
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(os.getcwd())
    target_path = Path(args.file).expanduser() if args.file else repo_root
    if not target_path.exists():
        print(f"Error: path not found: {target_path}", file=sys.stderr)
        return 2

    scan_target = str(target_path)
    try:
        findings = scan_repo(str(target_path), str(repo_root))
    except Exception as e:
        print(f"Error: could not scan {scan_target}: {e}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, scan_target, args)
    if output_result is not None:
        return output_result

    has_critical_or_high = any(f.severity in ("critical", "high") for f in findings)
    return 1 if has_critical_or_high else 0


def _run_scan(args) -> int:
    if getattr(args, "scan_target", None) == "claude":
        return _run_claude_scan(args)
    if getattr(args, "scan_target", None) == "cursor":
        return _run_cursor_scan(args)
    if getattr(args, "scan_target", None) == "repo":
        return _run_repo_scan(args)
    return _run_mcp_scan(args)


def _emit_report(findings: list, scan_target: str, args) -> Optional[int]:
    use_json = getattr(args, "json", False) or getattr(args, "json_flag", False)
    use_html = getattr(args, "html", False)
    if use_json and use_html:
        print("Error: use either --json or --html, not both.", file=sys.stderr)
        return 2

    report = json_reporter.generate(findings, scan_target)
    output_path = getattr(args, "output", None)
    if use_html:
        if output_path:
            html_reporter.write_html(report, output_path)
        else:
            html_reporter.print_html(report)
    elif use_json:
        if output_path:
            json_reporter.write_json(report, output_path)
        else:
            json_reporter.print_json(report)
    else:
        term_reporter.print_report(findings, scan_target)
    return None


def _add_scan_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", metavar="PATH", help="Path to config file or scan directory")
    p.add_argument("--repo-root", metavar="PATH", help="Project root (default: cwd)")
    p.add_argument("--json", dest="json", action="store_true", help="Output JSON report")
    p.add_argument("--html", action="store_true", help="Output HTML report")
    p.add_argument("--output", metavar="PATH", help="Write JSON or HTML report to file")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mcp-inspector",
        description="Local-first MCP security scanner",
    )
    sub = parser.add_subparsers(dest="command")

    # mcp-inspector scan [mcp] [flags]
    scan_p = sub.add_parser("scan", help="Scan configs for security issues")
    _add_scan_flags(scan_p)
    scan_sub = scan_p.add_subparsers(dest="scan_target")
    mcp_p = scan_sub.add_parser("mcp", help="Scan MCP server configs")
    _add_scan_flags(mcp_p)
    claude_p = scan_sub.add_parser("claude", help="Scan Claude project/user configs")
    _add_scan_flags(claude_p)
    cursor_p = scan_sub.add_parser("cursor", help="Scan Cursor project/user configs")
    _add_scan_flags(cursor_p)
    repo_p = scan_sub.add_parser("repo", help="Scan repository files")
    _add_scan_flags(repo_p)

    # mcp-inspector report --json [flags]
    report_p = sub.add_parser("report", help="Generate report (default: JSON)")
    _add_scan_flags(report_p)

    args = parser.parse_args()

    if args.command in ("scan", "report"):
        # For bare `scan` without subcommand, scan_target is None — still runs MCP scan
        sys.exit(_run_scan(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
