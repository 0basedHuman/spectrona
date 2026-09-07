import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    secret_body = "".join(["REAL", "SECRET", "VALUE", "123456"])
    config = {
        "mcpServers": {
            "svc": {
                "command": "npx",
                "args": [
                    "-y",
                    "some-server",
                    "--api-key",
                    "sk-proj-" + secret_body,
                    "--token",
                    "ghp_" + "ABCDEFGHIJKLMNOP1234",
                ],
            }
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
    if proc.returncode != 1:
        print(f"expected exit 1, got {proc.returncode}", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 1
    if secret_body in proc.stdout or secret_body in proc.stderr:
        print("raw secret body leaked in scanner output", file=sys.stderr)
        return 1

    report = json.loads(proc.stdout)
    ids = {finding["id"] for finding in report["findings"]}
    if "SECRET_KNOWN_PREFIX" not in ids:
        print("SECRET_KNOWN_PREFIX missing", file=sys.stderr)
        return 1
    if report["summary"]["critical"] < 1:
        print("critical summary count missing", file=sys.stderr)
        return 1
    if not any("mcpServers.svc.args[3]" in finding["source"] for finding in report["findings"]):
        print("args JSON path missing from finding source", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
