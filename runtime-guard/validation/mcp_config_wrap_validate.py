#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from runtime_guard.mcp_config import find_mcp_config, restore_backup, wrap_file, wrap_mcp_config


FIXTURE = Path(__file__).resolve().parents[2] / "mcp-inspector" / "examples" / "unsafe-mcp-configs" / "basic-unrestricted-filesystem.json"
RAW_SECRET = "sk-proj-abc123XYZsecretTokenWithHighEntropy9999"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spectrona_mcp_wrap_") as tmp_name:
        tmp = Path(tmp_name)
        repo = tmp / "repo"
        repo.mkdir()
        input_path = tmp / "mcp.json"
        input_path.write_text(FIXTURE.read_text())
        output_path = tmp / "wrapped.json"

        data = json.loads(input_path.read_text())
        result = wrap_mcp_config(data, repo_root=repo, spectrona_command="spectrona")
        assert result.wrapped == 2
        assert result.skipped == 0
        assert result.already_wrapped == 0
        filesystem = result.config["mcpServers"]["filesystem"]
        assert filesystem["command"] == "spectrona"
        assert filesystem["args"][:6] == ["mcp", "proxy", "--client", "mcp:filesystem", "--repo-root", str(repo)]
        assert "--enforce" not in filesystem["args"]
        assert "--dry-run" not in filesystem["args"]
        assert "--" in filesystem["args"]
        separator = filesystem["args"].index("--")
        assert filesystem["args"][separator + 1] == "npx"
        assert "@modelcontextprotocol/server-filesystem" in filesystem["args"]

        second = wrap_mcp_config(result.config, repo_root=repo, spectrona_command="spectrona")
        assert second.wrapped == 0
        assert second.already_wrapped == 2

        file_result, written, backup = wrap_file(
            input_path=input_path,
            repo_root=repo,
            output_path=output_path,
            spectrona_command="spectrona",
        )
        assert file_result.wrapped == 2
        assert written == output_path
        assert backup is None
        written_config = json.loads(output_path.read_text())
        assert written_config["mcpServers"]["shell-runner"]["command"] == "spectrona"
        assert RAW_SECRET in output_path.read_text()

        apply_result, applied, backup = wrap_file(
            input_path=input_path,
            repo_root=repo,
            output_path=None,
            apply=True,
            spectrona_command="spectrona",
        )
        assert apply_result.wrapped == 2
        assert applied == input_path
        assert backup == Path(str(input_path) + ".spectrona.bak")
        assert backup.exists()
        applied_config = json.loads(input_path.read_text())
        assert applied_config["mcpServers"]["filesystem"]["command"] == "spectrona"

        restored = restore_backup(input_path)
        assert restored == backup
        restored_config = json.loads(input_path.read_text())
        assert restored_config["mcpServers"]["filesystem"]["command"] == "npx"

        nested = repo / ".claude"
        nested.mkdir()
        discovered = nested / "mcp.json"
        discovered.write_text(FIXTURE.read_text())
        assert find_mcp_config(repo) == discovered

    print("mcp config wrapping validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
