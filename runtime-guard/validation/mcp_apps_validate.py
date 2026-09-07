#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from runtime_guard.mcp_apps import discover_mcp_apps, statuses_to_json


UNWRAPPED = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "env": {"OPENAI_API_KEY": "sk-proj-abc123XYZsecretTokenWithHighEntropy9999"},
        }
    }
}

WRAPPED = {
    "mcpServers": {
        "filesystem": {
            "command": "spectrona",
            "args": ["mcp", "proxy", "--client", "mcp:filesystem", "--", "npx", "-y", "server"],
            "env": {},
        }
    }
}

PARTIAL = {
    "mcpServers": {
        "wrapped": {
            "command": "spectrona",
            "args": ["mcp", "proxy", "--client", "mcp:wrapped", "--", "npx", "-y", "server"],
        },
        "plain": {
            "command": "npx",
            "args": ["-y", "plain-server"],
        },
    }
}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spectrona_mcp_apps_") as tmp_name:
        tmp = Path(tmp_name)
        home = tmp / "home"
        repo = tmp / "repo"
        home.mkdir()
        repo.mkdir()

        _write(home / ".claude" / "mcp.json", UNWRAPPED)
        _write(home / ".codex" / "mcp.json", WRAPPED)
        _write(repo / ".vscode" / "mcp.json", PARTIAL)
        invalid = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        invalid.parent.mkdir(parents=True)
        invalid.write_text("{not json")

        statuses = discover_mcp_apps(repo_root=repo, home=home)
        by_id = {status.app_id: status for status in statuses}

        assert by_id["claude-code"].status == "unprotected"
        assert by_id["claude-code"].servers == 1
        assert by_id["claude-code"].unwrapped_servers == 1
        assert by_id["claude-code"].drift_detected is False
        assert by_id["claude-code"].recommended_action == "protect"
        assert by_id["claude-code"].repair_available is True
        assert by_id["codex"].status == "protected"
        assert by_id["codex"].wrapped_servers == 1
        assert by_id["codex"].drift_detected is False
        assert by_id["codex"].recommended_action == "none"
        assert by_id["workspace-vscode"].status == "partial"
        assert by_id["workspace-vscode"].wrapped_servers == 1
        assert by_id["workspace-vscode"].unwrapped_servers == 1
        assert by_id["workspace-vscode"].drift_detected is True
        assert by_id["workspace-vscode"].recommended_action == "repair"
        assert by_id["workspace-vscode"].repair_available is True
        assert by_id["claude-desktop"].status == "invalid"
        assert by_id["claude-desktop"].drift_detected is False
        assert by_id["claude-desktop"].recommended_action == "inspect"
        assert by_id["workspace-mcp"].status == "missing"
        assert by_id["workspace-mcp"].recommended_action == "none"

        output = statuses_to_json(statuses)
        assert "abc123XYZsecretToken" not in output
        parsed = json.loads(output)
        assert any(item["app_id"] == "claude-code" for item in parsed)
        assert any(item["drift_detected"] is True for item in parsed)

    print("mcp app discovery validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
