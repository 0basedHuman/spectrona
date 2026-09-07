#!/usr/bin/env python3
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
GATEWAY_SRC = ROOT / "spectrona-gateway" / "src"
CLI_SRC = ROOT / "spectrona-cli" / "src"
POLICY_SRC = ROOT / "policy-engine" / "src"
INSPECTOR_SRC = ROOT / "mcp-inspector" / "src"
RUNTIME_GUARD_SRC = ROOT / "runtime-guard" / "src"
TEST_DB = Path(f"/tmp/spectrona_local_fallback_events_{os.getpid()}.db")
TEST_HOME = Path(f"/tmp/spectrona_local_fallback_home_{os.getpid()}")
AUTH_TOKEN = "local-fallback-auth-token"


class FallbackRuntime(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body)
        FallbackRuntime.calls.append({"path": self.path, "body": payload})

        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return

        data = json.dumps({
            "id": "chatcmpl_local_fallback",
            "object": "chat.completion",
            "model": payload.get("model", "unknown"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "fake fallback local passthrough"},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps({"object": "list", "data": [{"id": "fallback-test"}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "authorization": f"Bearer {AUTH_TOKEN}",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=5) as resp:
        headers = {key.lower(): value for key, value in dict(resp.headers).items()}
        return resp.status, headers, json.loads(resp.read().decode("utf-8"))


def _get_json(url):
    req = Request(url, headers={"authorization": f"Bearer {AUTH_TOKEN}"})
    with urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _wait_for_gateway(base: str):
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with urlopen(f"{base}/health", timeout=1) as resp:
                if resp.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("gateway did not become healthy")


def main() -> int:
    gateway_port = _free_port()
    primary_port = _free_port()
    fallback = ThreadingHTTPServer(("127.0.0.1", 0), FallbackRuntime)
    fallback_thread = Thread(target=fallback.serve_forever, daemon=True)
    fallback_thread.start()

    base = f"http://127.0.0.1:{gateway_port}"
    fallback_base = f"http://127.0.0.1:{fallback.server_port}/v1"
    primary_base = f"http://127.0.0.1:{primary_port}/v1"

    env = os.environ.copy()
    env.update({
        "PYTHONPATH": os.pathsep.join([
            str(ROOT / "spectrona-detection" / "src"),
            str(GATEWAY_SRC),
            str(CLI_SRC),
            str(POLICY_SRC),
            str(INSPECTOR_SRC),
            str(RUNTIME_GUARD_SRC),
        ]),
        "SPECTRONA_MOCK_MODE": "false",
        "SPECTRONA_PORT": str(gateway_port),
        "SPECTRONA_GATEWAY_AUTH_TOKEN": AUTH_TOKEN,
        "SPECTRONA_HOME": str(TEST_HOME),
        "SPECTRONA_LOG_DIR": str(TEST_HOME / "logs"),
        "SPECTRONA_DB_PATH": str(TEST_DB),
        "SPECTRONA_LOCAL_PROVIDER": "openai-compatible",
        "SPECTRONA_LOCAL_BASE_URL": primary_base,
        "SPECTRONA_LOCAL_HEALTH_PATH": "/models",
        "SPECTRONA_LOCAL_FALLBACKS": "lm-studio",
        "SPECTRONA_LM_STUDIO_BASE_URL": fallback_base,
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
            str(gateway_port),
            "--log-level",
            "error",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_gateway(base)

        status, headers, response = _post_json(
            f"{base}/local/v1/chat/completions",
            {"model": "fallback-test", "messages": [{"role": "user", "content": "hello"}]},
        )
        assert status == 200
        assert headers["x-spectrona-local-fallback"] == "true"
        assert response["choices"][0]["message"]["content"] == "fake fallback local passthrough"
        assert len(FallbackRuntime.calls) == 1
        assert FallbackRuntime.calls[0]["body"]["model"] == "fallback-test"

        provider_status, provider_resp = _get_json(f"{base}/providers/health")
        assert provider_status == 200
        runtimes = {item["runtime_id"]: item for item in provider_resp["local_runtimes"]["runtimes"]}
        assert runtimes["lm-studio"]["fallback_config"] is True
        assert runtimes["lm-studio"]["status"] == "fallback"
        assert provider_resp["local_runtimes"]["summary"]["fallback"] == 1

        events_status, events_resp = _get_json(f"{base}/events/recent?limit=5")
        assert events_status == 200
        assert any(event["action"] == "fallback_passthrough" for event in events_resp)

        usage_status, usage_resp = _get_json(f"{base}/events/token-usage")
        assert usage_status == 200
        assert usage_resp["total_tokens"] == 5

        print("local fallback validation passed")
        return 0
    finally:
        gateway.terminate()
        try:
            gateway.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gateway.kill()
        fallback.shutdown()
        TEST_DB.unlink(missing_ok=True)
        shutil.rmtree(TEST_HOME, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"local fallback validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
