#!/usr/bin/env python3
import json
import os
import shutil
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
POLICY_SRC = ROOT / "policy-engine" / "src"
DETECTION_SRC = ROOT / "spectrona-detection" / "src"
PORT = int(os.getenv("SPECTRONA_TEST_GATEWAY_PORT", "19011"))
UPSTREAM_PORT = int(os.getenv("SPECTRONA_TEST_UPSTREAM_PORT", "19012"))
BASE = f"http://127.0.0.1:{PORT}"
UPSTREAM_BASE = f"http://127.0.0.1:{UPSTREAM_PORT}/v1"
AUTH_TOKEN = "passthrough-gateway-auth-token"
TEST_DB = Path(f"/tmp/spectrona_passthrough_events_{os.getpid()}.db")
TEST_HOME = Path(f"/tmp/spectrona_passthrough_home_{os.getpid()}")


class FakeUpstream(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body)
        FakeUpstream.calls.append({
            "path": self.path,
            "authorization": self.headers.get("authorization"),
            "x_api_key": self.headers.get("x-api-key"),
            "anthropic_version": self.headers.get("anthropic-version"),
            "body": payload,
        })

        if self.path == "/v1/chat/completions":
            if payload.get("model") == "local-test":
                content = "fake local passthrough"
            elif payload.get("model") == "gpt-response-secret-test":
                content = "response leaked sk-proj-abc123XYZresponse9999"
            else:
                content = "fake openai passthrough"
            usage = (
                {"prompt_tokens": 5, "completion_tokens": 6, "total_tokens": 11}
                if payload.get("model") == "local-test"
                else {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}
            )
            response = {
                "id": "chatcmpl_fake_upstream",
                "object": "chat.completion",
                "model": payload.get("model", "unknown"),
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": usage,
            }
        elif self.path == "/v1/messages":
            response = {
                "id": "msg_fake_upstream",
                "type": "message",
                "role": "assistant",
                "model": payload.get("model", "unknown"),
                "content": [{"type": "text", "text": "fake anthropic passthrough"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 6, "output_tokens": 7},
            }
        else:
            self.send_response(404)
            self.end_headers()
            return

        data = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        FakeUpstream.calls.append({
            "path": self.path,
            "authorization": self.headers.get("authorization"),
            "x_api_key": self.headers.get("x-api-key"),
            "anthropic_version": self.headers.get("anthropic-version"),
            "body": None,
        })
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return

        data = json.dumps({"object": "list", "data": []}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _post_json(url, payload, headers=None):
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "authorization": f"Bearer {AUTH_TOKEN}",
            "content-type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    with urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _get_json(url):
    req = Request(url, headers={"authorization": f"Bearer {AUTH_TOKEN}"})
    with urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _wait_for_gateway():
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with urlopen(f"{BASE}/health", timeout=1) as resp:
                if resp.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError("gateway did not become healthy")


def main() -> int:
    upstream = ThreadingHTTPServer(("127.0.0.1", UPSTREAM_PORT), FakeUpstream)
    upstream_thread = Thread(target=upstream.serve_forever, daemon=True)
    upstream_thread.start()

    env = os.environ.copy()
    env.update({
        "PYTHONPATH": os.pathsep.join([str(DETECTION_SRC), str(GATEWAY_SRC), str(POLICY_SRC)]),
        "SPECTRONA_MOCK_MODE": "false",
        "SPECTRONA_PORT": str(PORT),
        "SPECTRONA_GATEWAY_AUTH_TOKEN": AUTH_TOKEN,
        "SPECTRONA_HOME": str(TEST_HOME),
        "SPECTRONA_LOG_DIR": str(TEST_HOME / "logs"),
        "SPECTRONA_DB_PATH": str(TEST_DB),
        "SPECTRONA_OPENAI_BASE_URL": UPSTREAM_BASE,
        "SPECTRONA_OPENAI_API_KEY": "test-openai-key",
        "SPECTRONA_ANTHROPIC_BASE_URL": UPSTREAM_BASE,
        "SPECTRONA_ANTHROPIC_API_KEY": "test-anthropic-key",
        "SPECTRONA_ANTHROPIC_VERSION": "2023-06-01",
        "SPECTRONA_LOCAL_PROVIDER": "openai-compatible",
        "SPECTRONA_LOCAL_BASE_URL": UPSTREAM_BASE,
        "SPECTRONA_LOCAL_HEALTH_PATH": "/models",
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
            str(PORT),
            "--log-level",
            "error",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_gateway()

        openai_status, openai_resp = _post_json(
            f"{BASE}/openai/v1/chat/completions",
            {"model": "gpt-test", "messages": [{"role": "user", "content": "hello"}]},
        )
        secret_status, secret_resp = _post_json(
            f"{BASE}/openai/v1/chat/completions",
            {
                "model": "gpt-secret-test",
                "messages": [{"role": "user", "content": "key sk-proj-abc123XYZsecrettoken9999"}],
            },
        )
        response_secret_status, response_secret_resp = _post_json(
            f"{BASE}/openai/v1/chat/completions",
            {
                "model": "gpt-response-secret-test",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        anthropic_status, anthropic_resp = _post_json(
            f"{BASE}/anthropic/v1/messages",
            {"model": "claude-test", "messages": [{"role": "user", "content": "hello"}]},
        )
        local_status, local_resp = _post_json(
            f"{BASE}/local/v1/chat/completions",
            {"model": "local-test", "messages": [{"role": "user", "content": "hello"}]},
        )

        assert openai_status == 200
        assert secret_status == 200
        assert response_secret_status == 200
        assert anthropic_status == 200
        assert local_status == 200
        assert openai_resp["choices"][0]["message"]["content"] == "fake openai passthrough"
        assert secret_resp["choices"][0]["message"]["content"] == "fake openai passthrough"
        assert response_secret_resp["choices"][0]["message"]["content"] == "response leaked sk-proj-[REDACTED_SECRET]"
        assert "abc123XYZresponse9999" not in json.dumps(response_secret_resp)
        assert anthropic_resp["content"][0]["text"] == "fake anthropic passthrough"
        assert local_resp["choices"][0]["message"]["content"] == "fake local passthrough"

        paths = [call["path"] for call in FakeUpstream.calls]
        assert "/v1/chat/completions" in paths
        assert "/v1/messages" in paths

        openai_call = next(
            call for call in FakeUpstream.calls
            if call["path"] == "/v1/chat/completions" and call["body"].get("model") == "gpt-test"
        )
        secret_call = next(
            call for call in FakeUpstream.calls
            if call["path"] == "/v1/chat/completions" and call["body"].get("model") == "gpt-secret-test"
        )
        local_call = next(
            call for call in FakeUpstream.calls
            if call["path"] == "/v1/chat/completions" and call["body"].get("model") == "local-test"
        )
        anthropic_call = next(call for call in FakeUpstream.calls if call["path"] == "/v1/messages")
        assert openai_call["authorization"] == "Bearer test-openai-key"
        secret_body = json.dumps(secret_call["body"])
        assert "abc123XYZsecrettoken" not in secret_body
        assert "sk-proj-[REDACTED_SECRET]" in secret_body
        assert local_call["authorization"] is None
        assert anthropic_call["x_api_key"] == "test-anthropic-key"
        assert anthropic_call["anthropic_version"] == "2023-06-01"

        provider_status, provider_resp = _get_json(f"{BASE}/providers/health?live=true")
        assert provider_status == 200
        assert provider_resp["live_checked"] is True
        assert provider_resp["providers"]["openai"]["status"] == "ok"
        assert provider_resp["providers"]["anthropic"]["status"] == "ok"
        assert provider_resp["providers"]["local"]["status"] == "ok"
        assert provider_resp["providers"]["openai"]["reachable"] is True
        assert provider_resp["providers"]["anthropic"]["reachable"] is True
        assert provider_resp["providers"]["local"]["reachable"] is True
        assert provider_resp["providers"]["local"]["api_key_required"] is False

        usage_status, usage_resp = _get_json(f"{BASE}/events/token-usage")
        assert usage_status == 200
        assert usage_resp["total_tokens"] == 45
        providers = {item["key"]: item for item in usage_resp["by_provider"]}
        assert providers["openai"]["total_tokens"] == 21
        assert providers["anthropic"]["total_tokens"] == 13
        assert providers["local"]["total_tokens"] == 11

        events_status, events_resp = _get_json(f"{BASE}/events/recent?limit=10")
        assert events_status == 200
        assert len(events_resp) >= 5
        raw_events = json.dumps(events_resp)
        assert "abc123XYZsecrettoken" not in raw_events
        assert "abc123XYZresponse9999" not in raw_events
        assert any(event["action"] == "response_redacted_then_passthrough" for event in events_resp)

        dlp_status, dlp_resp = _get_json(f"{BASE}/events/dlp?limit=10")
        assert dlp_status == 200
        assert dlp_resp["events"] >= 2
        assert dlp_resp["findings"] >= 2
        assert any(event["action"] == "response_redacted_then_passthrough" for event in dlp_resp["recent"])
        assert "abc123XYZresponse9999" not in json.dumps(dlp_resp)

        audit_log = TEST_HOME / "logs" / "audit.jsonl"
        audit_text = audit_log.read_text()
        assert "abc123XYZsecrettoken" not in audit_text
        assert "abc123XYZresponse9999" not in audit_text

        print("passthrough validation passed")
        return 0
    finally:
        gateway.terminate()
        try:
            gateway.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gateway.kill()
        upstream.shutdown()
        TEST_DB.unlink(missing_ok=True)
        shutil.rmtree(TEST_HOME, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"passthrough validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
