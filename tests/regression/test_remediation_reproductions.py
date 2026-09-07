import json
import importlib
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from mcp_inspector.scanner import scan_mcp_config
from policy_engine import load_policy_text
from runtime_guard.mcp_proxy import (
    ProxyConfig,
    _detect_filesystem_risk,
    _detect_shell_risk,
    _forward_to_upstream,
    handle_message,
)
from spectrona_gateway.dlp import findings_count


ROOT = Path(__file__).resolve().parents[2]


def test_f1_args_secret_reproduction_script_passes():
    from tests.regression import f1_args_secret_repro

    assert f1_args_secret_repro.main() == 0


def test_f1_args_secret_detector_reports_json_path_without_raw_value(tmp_path):
    secret_body = "".join(["REAL", "SECRET", "VALUE", "123456"])
    config = {
        "mcpServers": {
            "svc": {
                "command": "npx",
                "args": ["-y", "some-server", "--api-key", "sk-proj-" + secret_body],
            }
        }
    }
    path = _write_json(tmp_path / "f1.json", config)

    findings = scan_mcp_config(path, repo_root=tmp_path)
    secret_findings = [finding for finding in findings if finding.id == "SECRET_KNOWN_PREFIX"]

    assert secret_findings
    assert any("mcpServers.svc.args[3]" in finding.source for finding in secret_findings)
    assert secret_body not in json.dumps([finding.__dict__ for finding in findings])


def test_f2_proxy_defaults_to_dry_run_reproduction_script_passes():
    from tests.regression import f2_proxy_dry_run_repro

    assert f2_proxy_dry_run_repro.main() == 0


def test_f2_direct_shell_risk_reproduction_expected_fixed_behavior():
    cases = [
        ("write_file", {"path": "n.md", "content": "In a nutshell, the executive team approved it."}),
        ("write_file", {"path": "n.md", "content": "We shall execute the plan."}),
        ("write_file", {"path": "n.md", "content": "Seashells by the seashore"}),
        ("save", {"command": "anything at all"}),
    ]
    assert [_detect_shell_risk(tool, args) for tool, args in cases] == [False, False, False, False]
    assert _detect_shell_risk("run_shell", {"command": "pwd"}) is True
    assert _detect_shell_risk(
        "save",
        {"command": "bash -lc pwd"},
        {"type": "object", "properties": {"command": {"type": "string", "description": "Shell command to execute"}}},
    ) is True


def test_r7_filesystem_risk_uses_path_keys_not_free_text(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    assert _detect_filesystem_risk("write_file", {"content": "/etc/passwd is mentioned in prose"}, repo) is False
    assert _detect_filesystem_risk("write_file", {"path": "/etc/passwd", "content": "ok"}, repo) is True


def test_f3_gateway_auth_reproduction_in_process(tmp_path, monkeypatch):
    token = "pytest-gateway-auth-token"
    monkeypatch.setenv("SPECTRONA_HOME", str(tmp_path))
    monkeypatch.setenv("SPECTRONA_GATEWAY_AUTH_TOKEN", token)
    monkeypatch.setenv("SPECTRONA_POLICY_PATH", str(tmp_path / "policy.yaml"))
    monkeypatch.setenv("SPECTRONA_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("SPECTRONA_DB_PATH", str(tmp_path / "memory.db"))
    monkeypatch.setenv("SPECTRONA_MOCK_MODE", "true")

    import spectrona_gateway.config as gateway_config
    import spectrona_gateway.auth as gateway_auth
    import spectrona_gateway.app as gateway_app
    from fastapi.testclient import TestClient

    importlib.reload(gateway_config)
    importlib.reload(gateway_auth)
    importlib.reload(gateway_app)

    client = TestClient(gateway_app.create_app(), base_url="http://127.0.0.1")
    payload = {"confirm": True}

    assert client.get("/health").status_code == 200
    assert client.post("/policy/presets/relaxed/apply", json=payload).status_code == 401
    assert client.post(
        "/policy/presets/relaxed/apply",
        json=payload,
        headers={"authorization": "Bearer " + token},
    ).status_code == 200
    assert client.post(
        "/policy/presets/relaxed/apply",
        json=payload,
        headers={"authorization": "Bearer " + token, "host": "0.0.0.0"},
    ).status_code == 400
    assert client.post(
        "/policy/presets/relaxed/apply",
        json=payload,
        headers={"authorization": "Bearer " + token, "origin": "https://example.invalid"},
    ).status_code == 403


@pytest.mark.known_open
@pytest.mark.xfail(strict=True, reason="R10 owns JSON-RPC notification passthrough and pending-request transport")
def test_f4_notification_desync_reproduction_expected_fixed_behavior(tmp_path):
    server = tmp_path / "server.py"
    server.write_text(
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    if not line.strip():\n"
        "        continue\n"
        "    m = json.loads(line)\n"
        "    if m.get('method') == 'tools/list':\n"
        "        print(json.dumps({'jsonrpc':'2.0','method':'notifications/message','params':{'level':'info','data':'listing'}}), flush=True)\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{'tools':[{'name':'read_file'}]}}), flush=True)\n"
    )
    upstream = subprocess.Popen(
        [sys.executable, str(server)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        response = _forward_to_upstream(upstream, {"jsonrpc": "2.0", "id": 7, "method": "tools/list"})
    finally:
        upstream.terminate()
        try:
            upstream.wait(timeout=3)
        except subprocess.TimeoutExpired:
            upstream.kill()

    assert response == {"jsonrpc": "2.0", "id": 7, "result": {"tools": [{"name": "read_file"}]}}


def test_f5_gateway_dlp_credential_formats_expected_fixed_behavior():
    samples = {
        "stripe": "sk_live_51H8xYzAbCdEfGhIjKlMnOp",
        "google": "AIzaSyD-1234567890abcdefghijklmnop",
        "sendgrid": "SG.AbCdEfGh1234.IjKlMnOpQrStUvWxYz567890",
        "hf": "hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234",
        "rsa": "-----BEGIN RSA PRIVATE KEY-----MIIEowIBAAKC",
        "pg": "postgres://admin:SuperSecret123@db.internal:5432/prod",
        "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r",
        "aws": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "gitlab": "glpat-AbCdEfGhIjKlMnOpQrSt",
    }
    misses = [name for name, sample in samples.items() if findings_count(sample) == 0]
    assert misses == []


def test_f5_gateway_dlp_benign_corpus_has_zero_findings():
    benign = {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "git_sha": "0123456789abcdef0123456789abcdef01234567",
        "lock_hash": "sha512-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/==",
        "base64_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=",
        "text": "This harmless note mentions shells, shall, and command in normal prose.",
    }
    assert {name: findings_count(sample) for name, sample in benign.items()} == {name: 0 for name in benign}


def test_f6_policy_schema_reproduction_script_passes():
    from tests.regression import f6_policy_schema_repro

    assert f6_policy_schema_repro.main() == 0


def test_f6_policy_schema_rejects_bad_rules_at_load_time():
    with pytest.raises(ValueError, match="non-empty match"):
        load_policy_text("version: 1\ndefault_action: allow\nrules:\n  - id: t\n    action: deny\n")
    with pytest.raises(ValueError, match="Unknown match key"):
        load_policy_text(
            "version: 1\n"
            "default_action: allow\n"
            "rules:\n"
            "  - id: s\n"
            "    action: deny\n"
            "    match:\n"
            "      shel_risk: true\n"
        )


def test_f7_noise_reproduction_script_passes():
    from tests.regression import f7_noise_repro

    assert f7_noise_repro.main() == 0


def test_f7_correct_mcp_config_has_only_actionable_package_finding(tmp_path):
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
    path = _write_json(tmp_path / "f7.json", config)

    findings = scan_mcp_config(path, repo_root=tmp_path)
    ids = [finding.id for finding in findings]
    evidence = json.dumps([finding.__dict__ for finding in findings])

    assert "MCP_NO_AUDIT_LOG" not in ids
    assert sentry_ref not in evidence
    assert len(findings) <= 2


def test_r5_default_dry_run_forwards_known_false_positive(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    calls = []
    cfg = ProxyConfig(
        policy_path=None,
        repo_root=repo,
        client="pytest",
        audit_log=tmp_path / "audit.jsonl",
    )

    response = handle_message(
        _call("write_file", {"path": "n.md", "content": "In a nutshell, the executive team approved it."}),
        cfg,
        _upstream(calls),
    )

    assert cfg.policy_dry_run is True
    assert response["result"]["isError"] is False
    assert calls and calls[0]["params"]["name"] == "write_file"


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data))
    return path


def _call(tool_name: str, arguments: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _upstream(calls: list):
    def handler(message: dict) -> dict:
        calls.append(message)
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"content": [{"type": "text", "text": "ok"}], "isError": False},
        }

    return handler
