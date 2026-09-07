import os
import sys
from pathlib import Path
from typing import Optional


_LOCAL_SEARCH = [".claude/mcp.json", ".mcp.json", "mcp.json"]
_GLOBAL_SEARCH = [Path.home() / ".claude" / "mcp.json"]
_CLAUDE_SEARCH = ["CLAUDE.md", ".claude/settings.json", ".claude/settings.local.json"]
_CURSOR_SEARCH = [".cursor/settings.json", ".cursorrules", ".cursor/rules", ".cursor/mcp.json"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _ensure_inspector_importable() -> None:
    detection_src = _repo_root() / "spectrona-detection" / "src"
    inspector_src = _repo_root() / "mcp-inspector" / "src"
    if str(detection_src) not in sys.path:
        sys.path.insert(0, str(detection_src))
    if str(inspector_src) not in sys.path:
        sys.path.insert(0, str(inspector_src))


def _find_mcp_config(repo_root: Path) -> Optional[Path]:
    for rel in _LOCAL_SEARCH:
        path = repo_root / rel
        if path.exists():
            return path
    for path in _GLOBAL_SEARCH:
        if path.exists():
            return path
    return None


def mcp(
    file_path: Optional[str],
    repo_root: Optional[str],
    output_json: bool,
    output_html: bool = False,
    output_path: Optional[str] = None,
) -> int:
    _ensure_inspector_importable()

    from mcp_inspector.scanner import scan_mcp_config

    root = Path(repo_root).resolve() if repo_root else Path(os.getcwd()).resolve()
    if file_path:
        config_path = Path(file_path)
        if not config_path.exists():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            return 2
    else:
        config_path = _find_mcp_config(root)
        if config_path is None:
            print("No MCP config found. Searched: " + ", ".join(_LOCAL_SEARCH), file=sys.stderr)
            print("Use: spectrona scan mcp <path-to-mcp-json>", file=sys.stderr)
            return 0

    try:
        findings = scan_mcp_config(str(config_path), str(root))
    except Exception as exc:
        print(f"Error: could not scan {config_path}: {exc}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, str(config_path), output_json, output_html, output_path)
    if output_result is not None:
        return output_result

    return 1 if any(f.severity in ("critical", "high") for f in findings) else 0


def claude(
    file_path: Optional[str],
    repo_root: Optional[str],
    output_json: bool,
    output_html: bool = False,
    output_path: Optional[str] = None,
) -> int:
    _ensure_inspector_importable()

    from mcp_inspector.parsers.claude_parser import discover_claude_files
    from mcp_inspector.scanner import scan_claude_config

    root = Path(repo_root).resolve() if repo_root else Path(os.getcwd()).resolve()
    if file_path:
        config_path = Path(file_path).expanduser()
        if not config_path.exists():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            return 2
        if config_path.is_dir() and not discover_claude_files(str(config_path), include_global=False):
            print(f"No Claude config found under: {config_path}", file=sys.stderr)
            return 0
        scan_target = str(config_path)
        scan_arg = str(config_path)
    else:
        found = discover_claude_files(str(root))
        if not found:
            print("No Claude config found. Searched: " + ", ".join(_CLAUDE_SEARCH), file=sys.stderr)
            print("Use: spectrona scan claude <CLAUDE.md-or-settings-path>", file=sys.stderr)
            return 0
        scan_target = "claude:" + ", ".join(found)
        scan_arg = None

    try:
        findings = scan_claude_config(scan_arg, str(root))
    except Exception as exc:
        print(f"Error: could not scan {scan_target}: {exc}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, scan_target, output_json, output_html, output_path)
    if output_result is not None:
        return output_result

    return 1 if any(f.severity in ("critical", "high") for f in findings) else 0


def cursor(
    file_path: Optional[str],
    repo_root: Optional[str],
    output_json: bool,
    output_html: bool = False,
    output_path: Optional[str] = None,
) -> int:
    _ensure_inspector_importable()

    from mcp_inspector.parsers.cursor_parser import discover_cursor_files
    from mcp_inspector.scanner import scan_cursor_config

    root = Path(repo_root).resolve() if repo_root else Path(os.getcwd()).resolve()
    if file_path:
        config_path = Path(file_path).expanduser()
        if not config_path.exists():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            return 2
        if config_path.is_dir() and not discover_cursor_files(str(config_path), include_global=False):
            print(f"No Cursor config found under: {config_path}", file=sys.stderr)
            return 0
        scan_target = str(config_path)
        scan_arg = str(config_path)
    else:
        found = discover_cursor_files(str(root))
        if not found:
            print("No Cursor config found. Searched: " + ", ".join(_CURSOR_SEARCH), file=sys.stderr)
            print("Use: spectrona scan cursor <cursor-config-or-project-path>", file=sys.stderr)
            return 0
        scan_target = "cursor:" + ", ".join(found)
        scan_arg = None

    try:
        findings = scan_cursor_config(scan_arg, str(root))
    except Exception as exc:
        print(f"Error: could not scan {scan_target}: {exc}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, scan_target, output_json, output_html, output_path)
    if output_result is not None:
        return output_result

    return 1 if any(f.severity in ("critical", "high") for f in findings) else 0


def repo(
    file_path: Optional[str],
    repo_root: Optional[str],
    output_json: bool,
    output_html: bool = False,
    output_path: Optional[str] = None,
) -> int:
    _ensure_inspector_importable()

    from mcp_inspector.scanner import scan_repo

    root = Path(repo_root).resolve() if repo_root else Path(os.getcwd()).resolve()
    target_path = Path(file_path).expanduser() if file_path else root
    if not target_path.exists():
        print(f"Error: path not found: {target_path}", file=sys.stderr)
        return 2

    scan_target = str(target_path)
    try:
        findings = scan_repo(scan_target, str(root))
    except Exception as exc:
        print(f"Error: could not scan {scan_target}: {exc}", file=sys.stderr)
        return 2

    output_result = _emit_report(findings, scan_target, output_json, output_html, output_path)
    if output_result is not None:
        return output_result

    return 1 if any(f.severity in ("critical", "high") for f in findings) else 0


def _emit_report(
    findings: list,
    scan_target: str,
    output_json: bool,
    output_html: bool,
    output_path: Optional[str],
) -> Optional[int]:
    from mcp_inspector.reporters import html_reporter, json_reporter
    from mcp_inspector.reporters import terminal as term_reporter

    if output_json and output_html:
        print("Error: use either --json or --html, not both.", file=sys.stderr)
        return 2

    report = json_reporter.generate(findings, scan_target)
    if output_html:
        if output_path:
            html_reporter.write_html(report, output_path)
        else:
            html_reporter.print_html(report)
    elif output_json:
        if output_path:
            json_reporter.write_json(report, output_path)
        else:
            json_reporter.print_json(report)
    else:
        term_reporter.print_report(findings, scan_target)
    return None
