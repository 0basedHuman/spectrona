import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    sentry_ref = "$" + "{SENTRY_TOKEN}"
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$" + "{GITHUB_TOKEN}"},
            },
            "sentry": {
                "command": "uvx",
                "args": ["mcp-server-sentry", "--auth-token", sentry_ref],
            },
        }
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(config, f)
        path = f.name

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mcp_inspector",
            "scan",
            "mcp",
            "--file",
            path,
            "--json",
        ],
        cwd=repo,
        env={"PYTHONPATH": f"{repo / 'spectrona-detection' / 'src'}:{repo / 'mcp-inspector' / 'src'}"},
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        print(f"expected review-only exit 0, got {proc.returncode}", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 1

    report = json.loads(proc.stdout)
    ids = {finding["id"] for finding in report["findings"]}
    if "MCP_NO_AUDIT_LOG" in ids:
        print("MCP_NO_AUDIT_LOG should be deleted", file=sys.stderr)
        return 1
    if sentry_ref in proc.stdout or sentry_ref in proc.stderr:
        print("environment reference leaked into package evidence", file=sys.stderr)
        return 1
    if report["summary"]["total"] > 2:
        print(f"expected <=2 findings, got {report['summary']['total']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
