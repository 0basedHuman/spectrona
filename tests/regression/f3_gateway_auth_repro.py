#!/usr/bin/env python3
"""Regression for F3: gateway routes require local bearer auth."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH_TOKEN = "".join(["r3", "-", "gateway", "-", "auth", "-", "token"])


def main() -> int:
    port = _free_port()
    config_dir = Path(tempfile.mkdtemp(prefix="spectrona_f3_auth_"))
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        "\n".join([
            "gateway:",
            "  host: 127.0.0.1",
            f"  port: {port}",
            f"  auth_token: {AUTH_TOKEN}",
            "  mock_mode: true",
            "paths:",
            f"  log_dir: {config_dir / 'logs'}",
            f"  db_path: {config_dir / 'memory.db'}",
            "",
        ])
    )

    env = os.environ.copy()
    env.update({
        "PYTHONPATH": os.pathsep.join([
            str(ROOT / "spectrona-gateway" / "src"),
            str(ROOT / "policy-engine" / "src"),
        ]),
        "SPECTRONA_CONFIG_PATH": str(config_path),
        "SPECTRONA_HOME": str(config_dir),
        "SPECTRONA_LOG_DIR": str(config_dir / "logs"),
        "SPECTRONA_DB_PATH": str(config_dir / "memory.db"),
        "SPECTRONA_PORT": str(port),
        "SPECTRONA_GATEWAY_AUTH_TOKEN": AUTH_TOKEN,
        "SPECTRONA_MOCK_MODE": "true",
    })
    gateway = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "spectrona_gateway.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base)
        assert _get(f"{base}/health")[0] == 200

        payload = {"confirm": True}
        unauth_status, unauth = _post(f"{base}/policy/presets/relaxed/apply", payload)
        assert unauth_status == 401, unauth

        auth_status, auth_body = _post(
            f"{base}/policy/presets/relaxed/apply",
            payload,
            headers={"authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert auth_status == 200, auth_body

        host_status, host_body = _post(
            f"{base}/policy/presets/relaxed/apply",
            payload,
            headers={"authorization": f"Bearer {AUTH_TOKEN}", "host": "0.0.0.0"},
        )
        assert host_status == 400, host_body

        origin_status, origin_body = _post(
            f"{base}/policy/presets/relaxed/apply",
            payload,
            headers={
                "authorization": f"Bearer {AUTH_TOKEN}",
                "origin": "https://example.invalid",
            },
        )
        assert origin_status == 403, origin_body

        print("f3 gateway auth regression passed")
        return 0
    finally:
        gateway.terminate()
        try:
            gateway.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gateway.kill()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base: str) -> None:
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            status, _ = _get(f"{base}/health")
            if status == 200:
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("gateway did not become healthy")


def _get(url: str) -> tuple[int, dict]:
    return _open(urllib.request.Request(url))


def _post(url: str, payload: dict, headers: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", **(headers or {})},
        method="POST",
    )
    return _open(request)


def _open(request: urllib.request.Request) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw}


if __name__ == "__main__":
    raise SystemExit(main())
