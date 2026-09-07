#!/usr/bin/env python3
"""Regression for F2/R5/R7: proxy defaults advisory and English is not shell risk."""

import tempfile
from pathlib import Path

from runtime_guard.mcp_proxy import ProxyConfig, handle_message


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spectrona_f2_proxy_") as tmp_name:
        tmp = Path(tmp_name)
        repo = tmp / "repo"
        repo.mkdir()

        calls = []
        cfg = ProxyConfig(
            policy_path=None,
            repo_root=repo,
            client="codex",
            audit_log=tmp / "logs" / "audit.jsonl",
        )
        assert cfg.policy_dry_run is True
        response = handle_message(
            _call("write_file", {"path": "n.md", "content": "In a nutshell, the executive team approved it."}),
            cfg,
            _upstream(calls),
        )
        assert response["result"]["isError"] is False
        assert calls, "dry-run proxy should forward the tool call"

        enforced_calls = []
        enforced = ProxyConfig(
            policy_path=None,
            repo_root=repo,
            client="codex",
            audit_log=tmp / "logs" / "audit-enforced.jsonl",
            policy_dry_run=False,
        )
        english = handle_message(
            _call("write_file", {"path": "n.md", "content": "In a nutshell, the executive team approved it."}),
            enforced,
            _upstream(enforced_calls),
        )
        assert english["result"]["isError"] is False
        assert enforced_calls, "fixed detector should forward ordinary English even in enforcement mode"

        enforced_calls.clear()
        blocked = handle_message(
            _call("run_shell", {"command": "pwd"}),
            enforced,
            _upstream(enforced_calls),
        )
        assert blocked["error"]["code"] == -32041
        assert not enforced_calls, "explicit enforcement should still block real shell tools"

    print("f2 proxy dry-run regression passed")
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
