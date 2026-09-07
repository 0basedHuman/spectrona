#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from runtime_guard.mcp_proxy import ProxyConfig, handle_message


RAW_SECRET = "sk-proj-abc123XYZsecrettoken9999"
RAW_OUTPUT_SECRET = "sk-proj-abc123XYZoutputtoken9999"


def _config(tmp: Path, policy_text: str = None, dry_run: bool = True) -> ProxyConfig:
    policy_path = None
    if policy_text is not None:
        policy_path = tmp / "policy.yaml"
        policy_path.write_text(policy_text)
    repo = tmp / "repo"
    repo.mkdir(exist_ok=True)
    (repo / "safe.txt").write_text("safe")
    return ProxyConfig(
        policy_path=policy_path,
        repo_root=repo,
        client="claude",
        audit_log=tmp / "logs" / "mcp_audit.jsonl",
        policy_dry_run=dry_run,
    )


def _call(tool_name: str, arguments: dict, request_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _upstream(calls: list):
    def handler(message: dict) -> dict:
        calls.append(message)
        text = (
            f"upstream leaked {RAW_OUTPUT_SECRET}"
            if message["params"]["name"] == "leaky_tool"
            else f"upstream called {message['params']['name']}"
        )
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            },
        }
    return handler


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spectrona_mcp_proxy_") as tmp_name:
        tmp = Path(tmp_name)
        cfg = _config(tmp)
        assert cfg.policy_dry_run is True

        init = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, cfg)
        assert init["result"]["serverInfo"]["name"] == "spectrona-mcp-proxy"

        calls = []
        safe = handle_message(_call("safe_echo", {"text": "hello"}), cfg, _upstream(calls))
        assert safe["result"]["isError"] is False
        assert calls and calls[0]["params"]["name"] == "safe_echo"

        calls.clear()
        safe_path = str(cfg.repo_root / "safe.txt")
        safe_fs = handle_message(_call("filesystem.read_file", {"path": safe_path}), cfg, _upstream(calls))
        assert safe_fs["result"]["isError"] is False
        assert calls and calls[0]["params"]["arguments"]["path"] == safe_path

        calls.clear()
        shell = handle_message(_call("run_shell", {"command": "rm -rf /tmp/spectrona-test"}), cfg, _upstream(calls))
        assert shell["result"]["isError"] is False
        assert calls and calls[-1]["params"]["name"] == "run_shell"

        calls.clear()
        english = handle_message(
            _call("write_file", {"path": "n.md", "content": "In a nutshell, the executive team approved it."}),
            cfg,
            _upstream(calls),
        )
        assert english["result"]["isError"] is False
        assert calls and calls[-1]["params"]["name"] == "write_file"

        calls.clear()
        enforced_cfg = _config(tmp, dry_run=False)
        shell = handle_message(_call("run_shell", {"command": "rm -rf /tmp/spectrona-test"}), enforced_cfg, _upstream(calls))
        assert shell["error"]["code"] == -32041
        assert shell["error"]["data"]["policy_action"] == "deny"
        assert shell["error"]["data"]["shell_risk"] is True
        assert not calls

        fs = handle_message(_call("filesystem.read_file", {"path": "/etc/passwd"}), enforced_cfg, _upstream(calls))
        assert fs["error"]["code"] == -32041
        assert fs["error"]["data"]["filesystem_risk"] is True

        approval_policy = """version: 1
default_action: allow
rules:
  - id: approve-shell
    action: require_approval
    enabled: true
    reason: Shell tools need review.
    match:
      shell_risk: true
"""
        approval = handle_message(_call("terminal.exec", {"command": "pwd"}), _config(tmp, approval_policy, dry_run=False), _upstream(calls))
        assert approval["error"]["code"] == -32042
        assert approval["error"]["data"]["policy_action"] == "require_approval"

        redact_policy = """version: 1
default_action: allow
rules:
  - id: redact-mcp-secret
    action: redact
    enabled: true
    reason: Redact MCP tool input secrets.
    match:
      dlp_findings_min: 1
"""
        calls.clear()
        redacted = handle_message(_call("safe_echo", {"text": f"token {RAW_SECRET}"}), _config(tmp, redact_policy, dry_run=False), _upstream(calls))
        assert redacted["result"]["isError"] is False
        assert RAW_SECRET not in json.dumps(calls)
        assert "[REDACTED_SECRET]" in json.dumps(calls)

        calls.clear()
        output_redacted = handle_message(_call("leaky_tool", {"text": "hello"}), _config(tmp, redact_policy, dry_run=False), _upstream(calls))
        output_text = json.dumps(output_redacted)
        assert output_redacted["result"]["isError"] is False
        assert RAW_OUTPUT_SECRET not in output_text
        assert "sk-proj-[REDACTED_SECRET]" in output_text
        assert RAW_OUTPUT_SECRET not in json.dumps(calls)

        calls.clear()
        dry_run_cfg = _config(tmp, dry_run=True)
        dry_shell = handle_message(_call("run_shell", {"command": "pwd"}), dry_run_cfg, _upstream(calls))
        assert dry_shell["result"]["isError"] is False
        assert calls and calls[-1]["params"]["name"] == "run_shell"

        calls.clear()
        dry_input = handle_message(_call("safe_echo", {"text": f"token {RAW_SECRET}"}), dry_run_cfg, _upstream(calls))
        assert dry_input["result"]["isError"] is False
        assert RAW_SECRET in json.dumps(calls)

        calls.clear()
        dry_output = handle_message(_call("leaky_tool", {"text": "hello"}), dry_run_cfg, _upstream(calls))
        dry_output_text = json.dumps(dry_output)
        assert dry_output["result"]["isError"] is False
        assert RAW_OUTPUT_SECRET in dry_output_text

        audit_text = (tmp / "logs" / "mcp_audit.jsonl").read_text()
        assert RAW_SECRET not in audit_text
        assert RAW_OUTPUT_SECRET not in audit_text
        audit_events = [json.loads(line) for line in audit_text.splitlines() if line.strip()]
        actions = {event["action"] for event in audit_events}
        assert {
            "passthrough",
            "blocked",
            "approval_required",
            "redacted_then_passthrough",
            "response_redacted_then_passthrough",
            "would_block_then_passthrough",
            "would_redact_then_passthrough",
            "would_response_redact_then_passthrough",
        }.issubset(actions)
        policy_actions = {event["policy_action"] for event in audit_events}
        assert {"dry_run_deny", "dry_run_redact"}.issubset(policy_actions)
        assert any(
            event["action"] == "response_redacted_then_passthrough" and event["dlp_findings_count"] == 1
            for event in audit_events
        )
        assert any(
            event["action"] == "would_response_redact_then_passthrough" and event["dlp_findings_count"] == 1
            for event in audit_events
        )
        assert all("params" not in event and "arguments" not in event for event in audit_events)

    print("mcp proxy validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
