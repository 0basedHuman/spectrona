#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from runtime_guard.mcp_apps import (
    discover_mcp_apps,
    mutation_to_json,
    protect_mcp_app,
    unprotect_mcp_app,
)


RAW_SECRET = "sk-proj-abc123XYZsecretTokenWithHighEntropy9999"

UNWRAPPED = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            "env": {"OPENAI_API_KEY": RAW_SECRET},
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

PROTECTED_NO_BACKUP = {
    "mcpServers": {
        "safe": {
            "command": "spectrona",
            "args": ["mcp", "proxy", "--client", "mcp:safe", "--", "npx", "-y", "safe-server"],
        }
    }
}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _status(repo: Path, home: Path, app_id: str) -> str:
    return _status_item(repo, home, app_id).status


def _status_item(repo: Path, home: Path, app_id: str):
    by_id = {status.app_id: status for status in discover_mcp_apps(repo_root=repo, home=home)}
    return by_id[app_id]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spectrona_mcp_app_protect_") as tmp_name:
        tmp = Path(tmp_name)
        home = tmp / "home"
        repo = tmp / "repo"
        home.mkdir()
        repo.mkdir()

        claude_config = home / ".claude" / "mcp.json"
        _write(claude_config, UNWRAPPED)

        protected = protect_mcp_app("claude-code", repo_root=repo, home=home)
        assert protected.changed is True
        assert protected.before_status == "unprotected"
        assert protected.after_status == "protected"
        assert protected.wrapped_servers == 1
        assert Path(protected.backup_path).exists()
        assert _status(repo, home, "claude-code") == "protected"

        applied_config = json.loads(claude_config.read_text())
        filesystem = applied_config["mcpServers"]["filesystem"]
        assert filesystem["command"] == "spectrona"
        assert filesystem["args"][:2] == ["mcp", "proxy"]
        assert "--enforce" not in filesystem["args"]
        assert "--dry-run" not in filesystem["args"]
        assert "--" in filesystem["args"]
        assert filesystem["args"][filesystem["args"].index("--") + 1] == "npx"

        output = mutation_to_json(protected)
        assert RAW_SECRET not in output

        second = protect_mcp_app("claude-code", repo_root=repo, home=home)
        assert second.changed is False
        assert second.before_status == "protected"
        assert second.after_status == "protected"

        unprotected = unprotect_mcp_app("claude-code", repo_root=repo, home=home)
        assert unprotected.changed is True
        assert unprotected.before_status == "protected"
        assert unprotected.after_status == "unprotected"
        restored_config = json.loads(claude_config.read_text())
        assert restored_config["mcpServers"]["filesystem"]["command"] == "npx"
        restored_status = _status_item(repo, home, "claude-code")
        assert restored_status.backup_exists is True
        assert restored_status.backup_matches_current is True
        assert restored_status.drift_detected is False
        assert restored_status.recommended_action == "protect"

        claude_config.unlink()
        missing_status = _status_item(repo, home, "claude-code")
        assert missing_status.status == "missing"
        assert missing_status.backup_exists is True
        assert missing_status.drift_detected is True
        assert missing_status.recommended_action == "restore"
        restored_missing = unprotect_mcp_app("claude-code", repo_root=repo, home=home)
        assert restored_missing.before_status == "missing"
        assert restored_missing.after_status == "unprotected"
        assert claude_config.exists()

        partial_config = repo / ".vscode" / "mcp.json"
        _write(partial_config, PARTIAL)
        partial_status = _status_item(repo, home, "workspace-vscode")
        assert partial_status.drift_detected is True
        assert partial_status.recommended_action == "repair"
        repaired = protect_mcp_app("workspace-vscode", repo_root=repo, home=home)
        assert repaired.before_status == "partial"
        assert repaired.after_status == "protected"
        assert repaired.wrapped_servers == 1
        assert repaired.already_wrapped_servers == 1
        repaired_status = _status_item(repo, home, "workspace-vscode")
        assert repaired_status.drift_detected is False
        assert repaired_status.recommended_action == "none"

        codex_config = home / ".codex" / "mcp.json"
        _write(codex_config, PROTECTED_NO_BACKUP)
        missing_backup_error = ""
        try:
            unprotect_mcp_app("codex", repo_root=repo, home=home)
        except FileNotFoundError as exc:
            missing_backup_error = str(exc)
        assert "backup not found" in missing_backup_error

    print("mcp app protect validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
