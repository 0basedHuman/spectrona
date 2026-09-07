import json
from pathlib import Path

from mcp_inspector.scanner import scan_claude_config, scan_cursor_config, scan_mcp_config, scan_repo


ROOT = Path(__file__).resolve().parents[1]
MCP_EXAMPLES = ROOT / "mcp-inspector" / "examples"


def test_mcp_unsafe_fixture_reports_expected_detector_ids_without_raw_secrets():
    fixture = MCP_EXAMPLES / "unsafe-mcp-configs" / "basic-unrestricted-filesystem.json"
    findings = scan_mcp_config(str(fixture), repo_root=str(ROOT))
    ids = _ids(findings)
    evidence = json.dumps([finding.__dict__ for finding in findings])

    assert {
        "MCP_FS_OUTSIDE_REPO",
        "MCP_SHELL_UNRESTRICTED",
        "SECRET_KNOWN_PREFIX",
        "MCP_UNPINNED_PACKAGE",
        "MCP_TOOL_PROMPT_INJECTION_RISK",
        "MCP_POSTINSTALL_SCRIPT",
    }.issubset(ids)
    assert "abc123XYZsecretToken" not in evidence
    assert "Ignore previous instructions" not in evidence
    assert "curl -fsSL" not in evidence


def test_mcp_safe_fixture_has_no_high_or_critical_findings():
    fixture = MCP_EXAMPLES / "safe-mcp-configs" / "repo-only-filesystem.json"
    findings = scan_mcp_config(str(fixture), repo_root=str(ROOT))

    assert all(finding.severity not in {"critical", "high"} for finding in findings)
    assert "MCP_NO_AUDIT_LOG" not in _ids(findings)


def test_claude_unsafe_fixture_reports_expected_detector_ids_without_raw_secrets():
    fixture = MCP_EXAMPLES / "unsafe-claude-configs" / "settings-with-dangerous-permissions.json"
    findings = scan_claude_config(str(fixture), repo_root=str(ROOT))
    evidence = json.dumps([finding.__dict__ for finding in findings])

    assert {
        "CLAUDE_DANGEROUS_PERMISSION",
        "CLAUDE_HOOK_SHELL_INJECTION",
        "CLAUDE_NO_DENY_LIST",
    }.issubset(_ids(findings))
    assert "abc123XYZsecretToken" not in evidence


def test_claude_safe_fixture_has_no_claude_findings():
    fixture = MCP_EXAMPLES / "safe-claude-configs" / "settings-scoped-permissions.json"
    findings = scan_claude_config(str(fixture), repo_root=str(ROOT))

    assert findings == []


def test_cursor_unsafe_fixture_reports_expected_detector_ids_without_raw_secrets():
    fixture = MCP_EXAMPLES / "unsafe-cursor-configs" / "project"
    findings = scan_cursor_config(str(fixture), repo_root=str(ROOT))
    evidence = json.dumps([finding.__dict__ for finding in findings])

    assert {
        "CURSOR_AGENT_AUTO_RUN",
        "CURSOR_RULES_PROMPT_INJECTION",
    }.issubset(_ids(findings))
    assert "abc123XYZsecretToken" not in evidence


def test_cursor_safe_fixture_has_no_cursor_findings():
    fixture = MCP_EXAMPLES / "safe-cursor-configs" / "project"
    findings = scan_cursor_config(str(fixture), repo_root=str(ROOT))

    assert findings == []


def test_repo_unsafe_fixture_reports_expected_detector_ids_without_raw_secrets():
    fixture = MCP_EXAMPLES / "unsafe-repos" / "basic"
    findings = scan_repo(str(fixture), repo_root=str(fixture))
    evidence = json.dumps([finding.__dict__ for finding in findings])

    assert {
        "SECRET_ENV_FILE_EXPOSED",
        "SECRET_KNOWN_PREFIX",
        "SECRET_HIGH_ENTROPY_VALUE",
    }.issubset(_ids(findings))
    assert "abc123XYZsecretToken" not in evidence
    assert "abcd1234efgh5678ijkl9012mnop3456" not in evidence


def test_repo_safe_fixture_has_no_repo_secret_findings():
    fixture = MCP_EXAMPLES / "safe-repos" / "basic"
    findings = scan_repo(str(fixture), repo_root=str(fixture))

    assert findings == []


def _ids(findings):
    return {finding.id for finding in findings}
