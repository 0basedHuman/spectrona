#!/usr/bin/env python3
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = ROOT / "spectrona-cli" / "src"
HOME = Path(os.getenv("SPECTRONA_TEST_HOME", f"/tmp/spectrona_gateway_lifecycle_{os.getpid()}"))


def _free_port() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return str(sock.getsockname()[1])


PORT = os.getenv("SPECTRONA_TEST_PORT", _free_port())
BASE = f"http://127.0.0.1:{PORT}"
AUTH_TOKEN = "lifecycle-auth-token"


def _env():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(CLI_SRC)
    env["SPECTRONA_HOME"] = str(HOME)
    return env


def _run(args, check=True):
    proc = subprocess.run(
        [sys.executable, "-m", "spectrona_cli", *args],
        env=_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"{args} failed: stdout={proc.stdout!r} stderr={proc.stderr!r}")
    return proc


def _write_config():
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / "config.yaml").write_text(
        "\n".join([
            "gateway:",
            "  host: 127.0.0.1",
            f"  port: {PORT}",
            f"  auth_token: {AUTH_TOKEN}",
            "  mock_mode: true",
            "paths:",
            f"  log_dir: {HOME / 'logs'}",
            f"  db_path: {HOME / 'memory.db'}",
            "providers:",
            "  openai_base_url: https://api.openai.com/v1",
            '  openai_api_key: ""',
            "  anthropic_base_url: https://api.anthropic.com/v1",
            '  anthropic_api_key: ""',
            "  anthropic_version: 2023-06-01",
            "",
        ])
    )


def _wait_for_health():
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with urlopen(f"{BASE}/health", timeout=1) as resp:
                if resp.status == 200:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("gateway did not become healthy")


def main() -> int:
    try:
        _run(["init"])
        _write_config()

        start = _run(["start"])
        if "pid:" not in start.stdout:
            raise RuntimeError(f"start did not print pid: {start.stdout!r}")
        _wait_for_health()

        health = _run(["gateway", "health"])
        if "ok" not in health.stdout:
            raise RuntimeError(f"health output missing ok: {health.stdout!r}")

        restart = _run(["restart"])
        if "Starting Spectrona gateway" not in restart.stdout:
            raise RuntimeError(f"restart output unexpected: {restart.stdout!r}")
        _wait_for_health()

        stop = _run(["stop"])
        if "Stopped Spectrona gateway" not in stop.stdout and "not running" not in stop.stdout:
            raise RuntimeError(f"stop output unexpected: {stop.stdout!r}")

        pid_file = HOME / "gateway.pid"
        if pid_file.exists():
            raise RuntimeError("pid file still exists after stop")

        print("gateway lifecycle validation passed")
        return 0
    finally:
        _run(["gateway", "stop"], check=False)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"gateway lifecycle validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
