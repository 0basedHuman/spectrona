#!/usr/bin/env python3
"""Validate runtime memory capture, redacted retrieval, injection, and events."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
from typing import Optional, Tuple, Union


PROJECT_PATH = "/validate/runtime-memory"
RAW_SECRET = "sk-proj-abc123XYZmemorysecret9999"
RAW_SECRET_FRAGMENT = "abc123XYZmemorysecret"
AUTH_TOKEN = "memory-runtime-auth-token"


class FakeOpenAIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {}

        with self.server.lock:
            self.server.calls.append({
                "path": self.path,
                "headers": dict(self.headers),
                "body": body,
            })

        content = "fake openai runtime memory response"
        if body.get("model") == "gpt-runtime-memory-first":
            content = "remember: summarize validation failures with route and policy context"

        self._send_json({
            "id": "chatcmpl-runtime-memory",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "unknown"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
        })

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    gateway_port = _free_port()
    upstream_port = _free_port()

    upstream = ThreadingHTTPServer(("127.0.0.1", upstream_port), FakeOpenAIHandler)
    upstream.calls = []
    upstream.lock = Lock()
    upstream_thread = Thread(target=upstream.serve_forever, daemon=True)
    upstream_thread.start()

    tempdir = tempfile.TemporaryDirectory(prefix="spectrona_runtime_memory_")
    db_path = Path(tempdir.name) / "memory.db"
    gateway = _start_gateway(root, gateway_port, upstream_port, tempdir.name, db_path)

    try:
        _wait_for_gateway(gateway, gateway_port)

        first_status, _ = _post_json(
            f"http://127.0.0.1:{gateway_port}/openai/v1/chat/completions",
            {
                "model": "gpt-runtime-memory-first",
                "messages": [{
                    "role": "user",
                    "content": f"remember: prefer concise runtime summaries and token {RAW_SECRET}",
                }],
            },
            headers=_runtime_headers(),
        )
        assert first_status == 200, first_status

        assert len(upstream.calls) == 1, upstream.calls
        first_body_text = json.dumps(upstream.calls[0]["body"])
        assert "Spectrona memory context" not in first_body_text
        assert RAW_SECRET_FRAGMENT not in first_body_text
        assert "sk-proj-[REDACTED_SECRET]" in first_body_text

        request_item = _memory_item(gateway_port, q="concise", memory_type="user_preference")
        request_content = request_item["content"]
        assert "prefer concise runtime summaries" in request_content
        assert RAW_SECRET_FRAGMENT not in request_content
        assert "REDACTED_SECRET" in request_content

        response_item = _memory_item(gateway_port, q="validation", memory_type="session_summary")
        assert "route and policy context" in response_item["content"]

        stale_status, stale_payload = _post_json(
            f"http://127.0.0.1:{gateway_port}/memory/items",
            {
                "project_path": PROJECT_PATH,
                "source_tool": "codex",
                "memory_type": "user_preference",
                "content": "prefer verbose stale runtime summaries",
                "importance_score": 0.9,
                "tags": ["runtime"],
            },
        )
        assert stale_status == 201, stale_payload
        _make_item_old(db_path, stale_payload["id"], days=60)
        stale_item = _memory_item(gateway_port, q="verbose", memory_type="user_preference")
        assert stale_item["stale"] is True
        assert stale_item["stale_reason"] == "older_than_30_days"

        second_status, _ = _post_json(
            f"http://127.0.0.1:{gateway_port}/openai/v1/chat/completions",
            {
                "model": "gpt-runtime-memory-second",
                "messages": [{
                    "role": "user",
                    "content": "How should runtime summaries be written?",
                }],
            },
            headers=_runtime_headers(),
        )
        assert second_status == 200, second_status

        assert len(upstream.calls) == 2, upstream.calls
        second_body = upstream.calls[1]["body"]
        second_body_text = json.dumps(second_body)
        assert RAW_SECRET_FRAGMENT not in second_body_text
        assert "Spectrona memory context" in second_body_text
        assert "prefer concise runtime summaries" in second_body_text
        assert "prefer verbose stale runtime summaries" not in second_body_text
        assert "REDACTED_SECRET" in second_body_text
        assert second_body["messages"][0]["role"] == "system"

        events_status, events = _get_json(
            f"http://127.0.0.1:{gateway_port}/memory/events?"
            + urllib.parse.urlencode({"item_id": request_item["id"], "limit": 20})
        )
        assert events_status == 200, events
        attached = [event for event in events if event["event_type"] == "attached"]
        assert attached, events
        assert attached[0]["details"]["route"] == "/openai/v1/chat/completions"
        assert attached[0]["details"]["client"] == "codex"
        assert RAW_SECRET_FRAGMENT not in json.dumps(events)

        return 0
    finally:
        _stop_process(gateway)
        upstream.shutdown()
        upstream.server_close()
        tempdir.cleanup()


def _start_gateway(root: Path, port: int, upstream_port: int, tempdir: str, db_path: Path) -> subprocess.Popen:
    pythonpath = os.pathsep.join([
        str(root / "spectrona-detection" / "src"),
        str(root / "spectrona-gateway" / "src"),
        str(root / "policy-engine" / "src"),
        str(root / "spectrona-cli" / "src"),
        str(root / "mcp-inspector" / "src"),
        str(root / "runtime-guard" / "src"),
    ])
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": pythonpath + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
        "SPECTRONA_HOME": str(Path(tempdir) / "home"),
        "SPECTRONA_LOG_DIR": str(Path(tempdir) / "logs"),
        "SPECTRONA_DB_PATH": str(db_path),
        "SPECTRONA_PORT": str(port),
        "SPECTRONA_GATEWAY_AUTH_TOKEN": AUTH_TOKEN,
        "SPECTRONA_MOCK_MODE": "false",
        "SPECTRONA_OPENAI_BASE_URL": f"http://127.0.0.1:{upstream_port}/v1",
        "SPECTRONA_OPENAI_API_KEY": "test-openai-key",
        "SPECTRONA_MEMORY_CAPTURE": "true",
        "SPECTRONA_MEMORY_INJECTION": "false",
        "SPECTRONA_MEMORY_MAX_ATTACHMENTS": "5",
        "SPECTRONA_MEMORY_STALE_AFTER_DAYS": "30",
    })
    return subprocess.Popen(
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
        cwd=str(root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for_gateway(process: subprocess.Popen, port: int) -> None:
    health_url = f"http://127.0.0.1:{port}/health"
    for _ in range(40):
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError(f"gateway exited early with {process.returncode}: {output}")
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("gateway did not become healthy")


def _post_json(url: str, payload: dict, headers: Optional[dict] = None) -> Tuple[int, Union[dict, list]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "authorization": f"Bearer {AUTH_TOKEN}",
            "content-type": "application/json",
            **(headers or {}),
        },
    )
    return _open_json(request)


def _get_json(url: str) -> Tuple[int, Union[dict, list]]:
    return _open_json(
        urllib.request.Request(url, method="GET", headers={"authorization": f"Bearer {AUTH_TOKEN}"})
    )


def _open_json(request: urllib.request.Request) -> Tuple[int, Union[dict, list]]:
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw}
        return exc.code, payload


def _memory_item(port: int, q: str, memory_type: str) -> dict:
    query = urllib.parse.urlencode({
        "project_path": PROJECT_PATH,
        "q": q,
        "memory_type": memory_type,
        "source_tool": "codex",
        "limit": 10,
    })
    status, items = _get_json(f"http://127.0.0.1:{port}/memory/items?{query}")
    assert status == 200, items
    assert isinstance(items, list), items
    assert items, (q, memory_type, items)
    return items[0]


def _runtime_headers() -> dict:
    return {
        "x-spectrona-client": "codex",
        "x-spectrona-project-path": PROJECT_PATH,
        "x-spectrona-memory-injection": "true",
    }


def _make_item_old(db_path: Path, item_id: str, days: int) -> None:
    import sqlite3
    from datetime import datetime, timedelta, timezone

    old = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE memory_items SET updated_at = ? WHERE id = ?",
            (old, item_id),
        )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"memory runtime validation failed: {exc}", file=sys.stderr)
        raise
