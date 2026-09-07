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
PORT = int(os.getenv("SPECTRONA_TEST_POLICY_DRY_RUN_GATEWAY_PORT", "19031"))
HOME = Path(os.getenv("SPECTRONA_TEST_POLICY_DRY_RUN_HOME", f"/tmp/spectrona_policy_dry_run_{os.getpid()}"))
BASE = f"http://127.0.0.1:{PORT}"
AUTH_TOKEN = "policy-dry-run-auth-token"
RAW_SECRET = "sk-proj-abc123XYZdryrunsecret9999"


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


def _post_json(url: str, payload: dict, headers: dict = None) -> tuple[int, dict]:
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


def _get_json(url: str) -> tuple[int, dict]:
    req = Request(url, headers={"authorization": f"Bearer {AUTH_TOKEN}"})
    with urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _wait_for_gateway() -> None:
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
        "SPECTRONA_POLICY_DRY_RUN": "true",
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

        deny_status, deny = _post_json(
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
                "messages": [{"role": "user", "content": f"secret {RAW_SECRET}"}],
            },
            {"x-spectrona-client": "ollama"},
        )

        assert deny_status == 200
        assert deny["choices"][0]["message"]["role"] == "assistant"
        assert approval_status == 200
        assert approval["role"] == "assistant"
        assert redact_status == 200
        assert redact["choices"][0]["message"]["role"] == "assistant"

        raw_events = (HOME / "logs" / "audit.jsonl").read_text()
        assert "abc123XYZdryrunsecret" not in raw_events
        events = _events()
        actions = {event.get("action") for event in events}
        policy_actions = {event.get("policy_action") for event in events}
        rule_ids = {event.get("policy_rule_id") for event in events}
        assert "would_block_then_mock_response" in actions
        assert "would_require_approval_then_mock_response" in actions
        assert "would_redact_then_mock_response" in actions
        assert {"dry_run_deny", "dry_run_require_approval", "dry_run_redact"}.issubset(policy_actions)
        assert {"deny-blocked-client", "require-shell-approval", "redact-known-secrets"}.issubset(rule_ids)

        blocks_status, blocks = _get_json(f"{BASE}/events/blocks?limit=10")
        dlp_status, dlp = _get_json(f"{BASE}/events/dlp?limit=10")
        assert blocks_status == 200
        assert blocks["events"] >= 2
        assert blocks["blocked"] == 0
        assert blocks["approval_required"] == 0
        assert blocks["would_blocked"] >= 1
        assert blocks["would_approval_required"] >= 1
        assert dlp_status == 200
        assert dlp["events"] >= 1
        assert dlp["findings"] >= 1
        assert dlp["redacted_events"] == 0
        assert dlp["would_redact_events"] >= 1
        assert "abc123XYZdryrunsecret" not in json.dumps(blocks)
        assert "abc123XYZdryrunsecret" not in json.dumps(dlp)

        print("gateway policy dry-run validation passed")
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
        print(f"gateway policy dry-run validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
