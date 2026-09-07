"""
Public scanning API.

The CLI (cli.py) and the future FastAPI gateway both call this module.
Only this module imports detectors directly — callers get a flat Finding list.
"""

import os
from typing import Optional

from .models import Finding
from .parsers.claude_parser import parse_claude_target
from .parsers.cursor_parser import parse_cursor_target
from .parsers.mcp_parser import parse_mcp_config
from .parsers.repo_parser import parse_repo_target
from .detectors import (
    claude_detector,
    cursor_detector,
    fs_detector,
    package_detector,
    postinstall_detector,
    prompt_injection_detector,
    repo_detector,
    secrets_detector,
    shell_detector,
)


def scan_mcp_config(file_path: str, repo_root: Optional[str] = None) -> list[Finding]:
    """Scan a single MCP config file and return all findings."""
    if repo_root is None:
        repo_root = os.getcwd()

    servers = parse_mcp_config(file_path)
    findings: list[Finding] = []
    findings.extend(fs_detector.detect(servers, repo_root, file_path))
    findings.extend(secrets_detector.detect(servers, file_path))
    findings.extend(shell_detector.detect(servers, file_path))
    findings.extend(package_detector.detect(servers, file_path))
    findings.extend(prompt_injection_detector.detect(servers, file_path))
    findings.extend(postinstall_detector.detect(servers, file_path))
    return findings


def scan_claude_config(file_path: Optional[str] = None, repo_root: Optional[str] = None) -> list[Finding]:
    """Scan Claude project/user config files and return all findings."""
    if repo_root is None:
        repo_root = os.getcwd()

    files = parse_claude_target(file_path, repo_root)
    return claude_detector.detect(files)


def scan_cursor_config(file_path: Optional[str] = None, repo_root: Optional[str] = None) -> list[Finding]:
    """Scan Cursor project/user config files and return all findings."""
    if repo_root is None:
        repo_root = os.getcwd()

    files = parse_cursor_target(file_path, repo_root)
    return cursor_detector.detect(files)


def scan_repo(file_path: Optional[str] = None, repo_root: Optional[str] = None) -> list[Finding]:
    """Scan repository files for repo-level secret risks."""
    if repo_root is None:
        repo_root = os.getcwd()

    scan = parse_repo_target(file_path, repo_root)
    return repo_detector.detect(scan)
