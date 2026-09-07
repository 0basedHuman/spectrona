#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
GATEWAY_SRC = ROOT / "spectrona-gateway" / "src"
POLICY_SRC = ROOT / "policy-engine" / "src"
DETECTION_SRC = ROOT / "spectrona-detection" / "src"
PORT = int(os.getenv("SPECTRONA_TEST_POLICY_GATEWAY_PORT", "19021"))
HOME = Path(os.getenv("SPECTRONA_TEST_POLICY_HOME", f"/tmp/spectrona_policy_gateway_{os.getpid()}"))
BASE = f"http://127.0.0.1:{PORT}"
AUTH_TOKEN = "policy-gateway-auth-token"


POLICY_TEXT = """version: 1
default_action: allow

rules:
  - id: deny-blocked-client
    action: deny
    enabled: true
    reason: Test policy denies blocked-client.
    match:
      client: blocked-client

  - id: require-shell-approval
    action: require_approval
    enabled: true
    reason: Test policy requires approval for shell risk.
    match:
      shell_risk: true

  - id: redact-known-secrets
    action: redact
    enabled: true
    reason: Test policy redacts known secrets.
    match:
      dlp_findings_min: 1
"""


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
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


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


def _write_policy() -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / "logs").mkdir(parents=True, exist_ok=True)
    policy_path = HOME / "policy.yaml"
    policy_path.write_text(POLICY_TEXT)
    return policy_path


def _events() -> list:
    audit_log = HOME / "logs" / "audit.jsonl"
    return [json.loads(line) for line in audit_log.read_text().splitlines() if line.strip()]


def main() -> int:
    policy_path = _write_policy()
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": os.pathsep.join([str(DETECTION_SRC), str(GATEWAY_SRC), str(POLICY_SRC)]),
        "SPECTRONA_HOME": str(HOME),
        "SPECTRONA_LOG_DIR": str(HOME / "logs"),
        "SPECTRONA_DB_PATH": str(HOME / "memory.db"),
        "SPECTRONA_POLICY_PATH": str(policy_path),
        "SPECTRONA_MOCK_MODE": "true",
        "SPECTRONA_PORT": str(PORT),
        "SPECTRONA_GATEWAY_AUTH_TOKEN": AUTH_TOKEN,
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

        allowed_status, allowed = _post_json(
            f"{BASE}/openai/v1/chat/completions",
            {"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}]},
            {"x-spectrona-client": "codex"},
        )
        denied_status, denied = _post_json(
            f"{BASE}/openai/v1/chat/completions",
            {"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}]},
            {"x-spectrona-client": "blocked-client"},
        )
        approval_status, approval = _post_json(
            f"{BASE}/anthropic/v1/messages",
            {"model": "claude-test", "messages": [{"role": "user", "content": "hello"}]},
            {"x-spectrona-shell-risk": "true"},
        )
        redact_status, redact = _post_json(
            f"{BASE}/local/v1/chat/completions",
            {
                "model": "local-test",
                "messages": [{"role": "user", "content": "secret sk-proj-abc123XYZsecrettoken9999"}],
            },
            {"x-spectrona-client": "ollama"},
        )

        assert allowed_status == 200
        assert allowed["choices"][0]["message"]["role"] == "assistant"
        assert denied_status == 403
        assert denied["error"]["type"] == "policy_denied"
        assert denied["error"]["policy_action"] == "deny"
        assert denied["error"]["policy_rule_id"] == "deny-blocked-client"
        assert approval_status == 403
        assert approval["error"]["type"] == "policy_approval_required"
        assert approval["error"]["policy_action"] == "require_approval"
        assert redact_status == 200
        assert redact["choices"][0]["message"]["role"] == "assistant"

        raw_events = (HOME / "logs" / "audit.jsonl").read_text()
        assert "abc123XYZsecrettoken" not in raw_events
        events = _events()
        actions = {event.get("action") for event in events}
        policy_actions = {event.get("policy_action") for event in events}
        rule_ids = {event.get("policy_rule_id") for event in events}
        assert "blocked" in actions
        assert "approval_required" in actions
        assert "redacted_then_mock_response" in actions
        assert {"allow", "deny", "require_approval", "redact"}.issubset(policy_actions)
        assert {"deny-blocked-client", "require-shell-approval", "redact-known-secrets"}.issubset(rule_ids)

        blocks_status, blocks = _get_json(f"{BASE}/events/blocks?limit=10")
        dlp_status, dlp = _get_json(f"{BASE}/events/dlp?limit=10")
        assert blocks_status == 200
        assert blocks["events"] >= 2
        assert blocks["blocked"] >= 1
        assert blocks["approval_required"] >= 1
        assert {"deny-blocked-client", "require-shell-approval"}.issubset(
            {item["key"] for item in blocks["by_rule"]}
        )
        assert any(event["policy_action"] == "require_approval" for event in blocks["recent"])
        assert dlp_status == 200
        assert dlp["events"] >= 1
        assert dlp["findings"] >= 1
        assert dlp["redacted_events"] >= 1
        assert any(event["policy_action"] == "redact" for event in dlp["recent"])
        assert "abc123XYZsecrettoken" not in json.dumps(blocks)
        assert "abc123XYZsecrettoken" not in json.dumps(dlp)

        print("gateway policy validation passed")
        return 0
    finally:
        gateway.terminate()
        try:
            gateway.wait(timeout=5)
        except subprocess.TimeoutExpired:
            gateway.kill()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"gateway policy validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
