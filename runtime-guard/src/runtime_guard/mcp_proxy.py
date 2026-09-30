import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from policy_engine import Decision, PolicyContext, PolicyEngine, load_policy

from .redaction import findings_count, redact_json, redact_text


_SHELL_TOOL_NAMES = {
    "bash",
    "exec",
    "execute",
    "execute_command",
    "powershell",
    "pwsh",
    "run_command",
    "run_shell",
    "shell",
    "sh",
    "subprocess",
    "terminal",
    "terminal_exec",
    "zsh",
}
_COMMAND_KEYS = {"command", "cmd", "shell", "executable", "script"}
_SHELL_COMMANDS = {"bash", "sh", "zsh", "fish", "dash", "pwsh", "powershell"}
_PATH_KEYS = {"path", "paths", "file", "files", "root", "roots", "directory", "directories", "dir", "cwd"}


@dataclass(frozen=True)
class ProxyConfig:
    policy_path: Optional[Path]
    repo_root: Path
    client: str
    audit_log: Path
    policy_dry_run: bool = True

    @classmethod
    def from_environment(
        cls,
        policy_path: Optional[str] = None,
        repo_root: Optional[str] = None,
        client: Optional[str] = None,
        audit_log: Optional[str] = None,
        policy_dry_run: Optional[bool] = None,
    ) -> "ProxyConfig":
        home = Path(os.getenv("SPECTRONA_HOME", str(Path.home() / ".spectrona"))).expanduser()
        configured_policy = policy_path or os.getenv("SPECTRONA_POLICY_PATH")
        configured_repo = repo_root or os.getenv("SPECTRONA_REPO_ROOT") or os.getcwd()
        configured_client = client or os.getenv("SPECTRONA_CLIENT") or "mcp-client"
        configured_audit = audit_log or os.getenv("SPECTRONA_MCP_AUDIT_LOG") or str(home / "logs" / "mcp_audit.jsonl")
        if policy_dry_run is None:
            configured_dry_run = not _env_bool("SPECTRONA_MCP_ENFORCE")
            if _env_bool("SPECTRONA_POLICY_DRY_RUN"):
                configured_dry_run = True
        else:
            configured_dry_run = policy_dry_run
        return cls(
            policy_path=Path(configured_policy).expanduser() if configured_policy else None,
            repo_root=Path(configured_repo).expanduser().resolve(),
            client=configured_client,
            audit_log=Path(configured_audit).expanduser(),
            policy_dry_run=configured_dry_run,
        )


@dataclass(frozen=True)
class ToolCallDecision:
    decision: Decision
    tool_name: str
    dlp_findings_count: int
    shell_risk: bool
    filesystem_risk: bool
    dry_run: bool = False

    @property
    def blocked(self) -> bool:
        return not self.dry_run and self.decision.action in {"deny", "require_approval"}

    @property
    def policy_action(self) -> str:
        if self.dry_run and self.decision.action != "allow":
            return "dry_run_" + self.decision.action
        return self.decision.action

    @property
    def action(self) -> str:
        if self.dry_run:
            if self.decision.action == "deny":
                return "would_block_then_passthrough"
            if self.decision.action == "require_approval":
                return "would_require_approval_then_passthrough"
            if self.decision.action == "redact":
                return "would_redact_then_passthrough"
            return "passthrough"
        if self.decision.action == "deny":
            return "blocked"
        if self.decision.action == "require_approval":
            return "approval_required"
        if self.decision.action == "redact":
            return "redacted_then_passthrough"
        return "passthrough"


@dataclass(frozen=True)
class ToolResponseDecision:
    decision: Decision
    tool_name: str
    dlp_findings_count: int
    dry_run: bool = False

    @property
    def blocked(self) -> bool:
        return not self.dry_run and self.decision.action in {"deny", "require_approval"}

    @property
    def policy_action(self) -> str:
        if self.dry_run and self.decision.action != "allow":
            return "dry_run_" + self.decision.action
        return self.decision.action

    @property
    def action(self) -> str:
        if self.dry_run:
            if self.decision.action == "deny":
                return "would_response_block_then_passthrough"
            if self.decision.action == "require_approval":
                return "would_response_require_approval_then_passthrough"
            if self.decision.action == "redact":
                return "would_response_redact_then_passthrough"
            return "passthrough"
        if self.decision.action == "deny":
            return "response_blocked"
        if self.decision.action == "require_approval":
            return "response_approval_required"
        if self.decision.action == "redact":
            return "response_redacted_then_passthrough"
        return "passthrough"


def handle_message(
    message: dict,
    config: ProxyConfig,
    upstream_handler: Optional[Callable[[dict], Optional[dict]]] = None,
) -> Optional[dict]:
    method = message.get("method")
    request_id = message.get("id")

    if not method:
        return _jsonrpc_error(request_id, -32600, "Invalid JSON-RPC request.")

    if method == "notifications/initialized":
        if upstream_handler:
            upstream_handler(message)
        return None

    if method == "tools/call":
        return _handle_tool_call(message, config, upstream_handler)

    if upstream_handler:
        return upstream_handler(message)

    if method == "initialize":
        return _jsonrpc_result(request_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "spectrona-mcp-proxy", "version": "0.1.0"},
        })

    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": []})

    if request_id is None:
        return None
    return _jsonrpc_error(request_id, -32601, f"MCP method is not available without an upstream server: {method}")


def evaluate_tool_call(message: dict, config: ProxyConfig) -> ToolCallDecision:
    params = message.get("params", {})
    if not isinstance(params, dict):
        params = {}
    tool_name = str(params.get("name", "unknown"))
    arguments = params.get("arguments", {})
    body_text = json.dumps(params, sort_keys=True, default=str)
    dlp_hits = findings_count(body_text)
    shell_risk = _detect_shell_risk(tool_name, arguments)
    filesystem_risk = _detect_filesystem_risk(tool_name, arguments, config.repo_root)

    context = PolicyContext(
        route="mcp/tools/call",
        provider_type="mcp",
        model=tool_name,
        client=config.client,
        dlp_findings_count=dlp_hits,
        shell_risk=shell_risk,
        filesystem_risk=filesystem_risk,
        dry_run=config.policy_dry_run,
    )
    decision = PolicyEngine(load_policy(config.policy_path)).evaluate(context)
    return ToolCallDecision(
        decision=decision,
        tool_name=tool_name,
        dlp_findings_count=dlp_hits,
        shell_risk=shell_risk,
        filesystem_risk=filesystem_risk,
        dry_run=config.policy_dry_run,
    )


def evaluate_tool_response(response: dict, tool_name: str, config: ProxyConfig) -> ToolResponseDecision:
    body_text = json.dumps(response, sort_keys=True, default=str)
    dlp_hits = findings_count(body_text)
    context = PolicyContext(
        route="mcp/tools/call",
        provider_type="mcp",
        model=tool_name,
        client=config.client,
        dlp_findings_count=dlp_hits,
        shell_risk=False,
        filesystem_risk=False,
    )
    decision = PolicyEngine(load_policy(config.policy_path)).evaluate(context)
    return ToolResponseDecision(
        decision=decision,
        tool_name=tool_name,
        dlp_findings_count=dlp_hits,
        dry_run=config.policy_dry_run,
    )


def serve_stdio(config: ProxyConfig, upstream_command: Optional[list] = None) -> int:
    _print_mode_notice(config)
    upstream = None
    upstream_handler = None
    transport = None
    stdout_lock = threading.Lock()
    if upstream_command:
        upstream = subprocess.Popen(
            upstream_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        transport = _UpstreamTransport(
            upstream,
            notification_sink=lambda message: _write_json_line(message, sys.stdout, stdout_lock),
            stderr_log=lambda line: _log_upstream_stderr(config, line),
        )
        upstream_handler = transport.request

    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = handle_message(message, config, upstream_handler)
            except Exception as exc:
                response = _jsonrpc_error(None, -32603, f"Spectrona MCP proxy error: {exc}")
            if response is not None:
                _write_json_line(response, sys.stdout, stdout_lock)
        return 0
    finally:
        if upstream:
            upstream.terminate()
            try:
                upstream.wait(timeout=3)
            except subprocess.TimeoutExpired:
                upstream.kill()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Spectrona MCP stdio proxy")
    parser.add_argument("--policy", help="Policy YAML path. Defaults to SPECTRONA_POLICY_PATH or built-in policy.")
    parser.add_argument("--repo-root", help="Repository root for filesystem-risk decisions. Defaults to cwd.")
    parser.add_argument("--client", help="Client/app name recorded in policy context and audit log.")
    parser.add_argument("--audit-log", help="MCP audit JSONL path. Defaults to ~/.spectrona/logs/mcp_audit.jsonl.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Record policy decisions without blocking or redacting MCP traffic. This is the default.")
    mode.add_argument("--enforce", action="store_true", help="Opt in to blocking/redaction enforcement for MCP traffic.")
    parser.add_argument("upstream", nargs=argparse.REMAINDER, help="Optional upstream MCP server command after --")
    args = parser.parse_args(argv)

    upstream = args.upstream
    if upstream and upstream[0] == "--":
        upstream = upstream[1:]
    config = ProxyConfig.from_environment(
        policy_path=args.policy,
        repo_root=args.repo_root,
        client=args.client,
        audit_log=args.audit_log,
        policy_dry_run=False if args.enforce else True if args.dry_run else None,
    )
    return serve_stdio(config, upstream_command=upstream or None)


def _handle_tool_call(
    message: dict,
    config: ProxyConfig,
    upstream_handler: Optional[Callable[[dict], Optional[dict]]],
) -> Optional[dict]:
    decision = evaluate_tool_call(message, config)
    request_id = message.get("id")

    if decision.blocked:
        _log_tool_event(config, decision)
        if request_id is None:
            return None
        if decision.decision.action == "require_approval":
            return _jsonrpc_error(
                request_id,
                -32042,
                "Spectrona policy requires approval before this MCP tool call can continue.",
                _error_data(decision),
            )
        return _jsonrpc_error(
            request_id,
            -32041,
            "Spectrona policy blocked this MCP tool call.",
            _error_data(decision),
        )

    forwarded = redact_json(message) if decision.decision.action == "redact" and not decision.dry_run else message
    _log_tool_event(config, decision)
    if upstream_handler:
        response = upstream_handler(forwarded)
        return _guard_tool_response(response, config, decision, request_id)
    if request_id is None:
        return None
    return _jsonrpc_error(
        request_id,
        -32050,
        "Spectrona policy allowed this MCP tool call, but no upstream MCP server is configured.",
        _error_data(decision),
    )


def _guard_tool_response(
    response: Optional[dict],
    config: ProxyConfig,
    request_decision: ToolCallDecision,
    request_id: Any,
) -> Optional[dict]:
    if response is None:
        return None

    response_decision = evaluate_tool_response(response, request_decision.tool_name, config)
    if response_decision.dlp_findings_count > 0 or response_decision.decision.action != "allow":
        _log_tool_response_event(config, response_decision)

    if response_decision.blocked:
        code = -32044 if response_decision.decision.action == "require_approval" else -32043
        message = (
            "Spectrona policy requires approval before this MCP tool response can be returned."
            if response_decision.decision.action == "require_approval"
            else "Spectrona policy blocked this MCP tool response."
        )
        return _jsonrpc_error(request_id, code, message, _response_error_data(response_decision))

    if response_decision.decision.action == "redact" and not response_decision.dry_run:
        return redact_json(response)
    return response


def _error_data(decision: ToolCallDecision) -> dict:
    return {
        "policy_action": decision.decision.action,
        "policy_rule_id": redact_text(decision.decision.rule_id),
        "policy_reason": redact_text(decision.decision.reason),
        "tool_name": redact_text(decision.tool_name),
        "dlp_findings_count": decision.dlp_findings_count,
        "shell_risk": decision.shell_risk,
        "filesystem_risk": decision.filesystem_risk,
    }


def _response_error_data(decision: ToolResponseDecision) -> dict:
    return {
        "policy_action": decision.decision.action,
        "policy_rule_id": redact_text(decision.decision.rule_id),
        "policy_reason": redact_text(decision.decision.reason),
        "tool_name": redact_text(decision.tool_name),
        "dlp_findings_count": decision.dlp_findings_count,
        "shell_risk": False,
        "filesystem_risk": False,
    }


def _jsonrpc_result(request_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Optional[dict] = None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


class _UpstreamTransport:
    def __init__(
        self,
        upstream: subprocess.Popen,
        notification_sink: Optional[Callable[[dict], None]] = None,
        stderr_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        if upstream.stdin is None or upstream.stdout is None:
            raise RuntimeError("upstream MCP process is not connected")
        self._upstream = upstream
        self._notification_sink = notification_sink
        self._stderr_log = stderr_log
        self._pending: dict[Any, queue.Queue] = {}
        self._pending_lock = threading.Lock()
        self._stdin_lock = threading.Lock()
        self._stdout_thread = threading.Thread(target=self._pump_stdout, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread = None
        if upstream.stderr is not None:
            self._stderr_thread = threading.Thread(target=self._pump_stderr, daemon=True)
            self._stderr_thread.start()

    def request(self, message: dict) -> Optional[dict]:
        request_id = message.get("id")
        response_queue = None
        if request_id is not None:
            response_queue = queue.Queue(maxsize=1)
            with self._pending_lock:
                self._pending[request_id] = response_queue

        try:
            self._send(message)
            if response_queue is None:
                return None
            response = response_queue.get()
            if isinstance(response, BaseException):
                raise response
            return response
        finally:
            if request_id is not None:
                with self._pending_lock:
                    if self._pending.get(request_id) is response_queue:
                        del self._pending[request_id]

    def _send(self, message: dict) -> None:
        line = json.dumps(message, separators=(",", ":")) + "\n"
        with self._stdin_lock:
            if self._upstream.stdin is None:
                raise RuntimeError("upstream MCP process is not connected")
            self._upstream.stdin.write(line)
            self._upstream.stdin.flush()

    def _pump_stdout(self) -> None:
        assert self._upstream.stdout is not None
        try:
            for line in self._upstream.stdout:
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as exc:
                    self._fail_pending(RuntimeError(f"upstream MCP process emitted invalid JSON: {exc}"))
                    continue
                request_id = message.get("id") if isinstance(message, dict) else None
                pending = None
                if request_id is not None:
                    with self._pending_lock:
                        pending = self._pending.get(request_id)
                if pending is not None:
                    pending.put(message)
                    continue
                self._forward_notification(message)
        finally:
            self._fail_pending(RuntimeError("upstream MCP process closed stdout"))

    def _pump_stderr(self) -> None:
        assert self._upstream.stderr is not None
        for line in self._upstream.stderr:
            if self._stderr_log:
                self._stderr_log(line.rstrip("\n"))

    def _forward_notification(self, message: dict) -> None:
        if self._notification_sink:
            self._notification_sink(message)

    def _fail_pending(self, error: RuntimeError) -> None:
        with self._pending_lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for response_queue in pending:
            response_queue.put(error)


def _forward_to_upstream(
    upstream: subprocess.Popen,
    message: dict,
    notification_sink: Optional[Callable[[dict], None]] = None,
    stderr_log: Optional[Callable[[str], None]] = None,
) -> Optional[dict]:
    sink = notification_sink if notification_sink is not None else lambda item: _write_json_line(item)
    transport = _UpstreamTransport(upstream, notification_sink=sink, stderr_log=stderr_log)
    return transport.request(message)


def _write_json_line(message: dict, stream: Any = sys.stdout, lock: Optional[threading.Lock] = None) -> None:
    line = json.dumps(message, separators=(",", ":"))
    if lock is None:
        print(line, file=stream, flush=True)
        return
    with lock:
        print(line, file=stream, flush=True)


def _log_tool_event(config: ProxyConfig, decision: ToolCallDecision) -> None:
    config.audit_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": "mcp/tools/call",
        "provider_type": "mcp",
        "client": redact_text(config.client),
        "tool_name": redact_text(decision.tool_name),
        "action": decision.action,
        "policy_action": decision.policy_action,
        "policy_rule_id": redact_text(decision.decision.rule_id),
        "policy_reason": redact_text(decision.decision.reason),
        "dlp_findings_count": decision.dlp_findings_count,
        "shell_risk": decision.shell_risk,
        "filesystem_risk": decision.filesystem_risk,
    }
    with open(config.audit_log, "a") as handle:
        handle.write(json.dumps(event) + "\n")


def _log_tool_response_event(config: ProxyConfig, decision: ToolResponseDecision) -> None:
    config.audit_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": "mcp/tools/call",
        "provider_type": "mcp",
        "client": redact_text(config.client),
        "tool_name": redact_text(decision.tool_name),
        "action": decision.action,
        "policy_action": decision.policy_action,
        "policy_rule_id": redact_text(decision.decision.rule_id),
        "policy_reason": redact_text(decision.decision.reason),
        "dlp_findings_count": decision.dlp_findings_count,
        "shell_risk": False,
        "filesystem_risk": False,
    }
    with open(config.audit_log, "a") as handle:
        handle.write(json.dumps(event) + "\n")


def _log_upstream_stderr(config: ProxyConfig, line: str) -> None:
    if not line:
        return
    config.audit_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": "mcp/upstream/stderr",
        "provider_type": "mcp",
        "client": redact_text(config.client),
        "action": "upstream_stderr",
        "message": redact_text(line),
        "dlp_findings_count": findings_count(line),
    }
    with open(config.audit_log, "a") as handle:
        handle.write(json.dumps(event) + "\n")


def _print_mode_notice(config: ProxyConfig) -> None:
    if config.policy_dry_run:
        print(
            "Spectrona MCP proxy running in dry-run mode: policy decisions are audited but MCP traffic is not blocked or redacted. "
            "Use --enforce or SPECTRONA_MCP_ENFORCE=true to opt in to enforcement.",
            file=sys.stderr,
            flush=True,
        )
        return
    print(
        "Spectrona MCP proxy enforcement enabled by explicit opt-in; policy decisions can block or redact MCP traffic.",
        file=sys.stderr,
        flush=True,
    )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _detect_shell_risk(tool_name: str, arguments: Any, tool_schema: Optional[dict] = None) -> bool:
    if _is_shell_tool(tool_name):
        return True
    if not tool_schema:
        return False
    command_paths = set(_schema_command_paths(tool_schema))
    return any(path in command_paths and _looks_like_shell_command(value) for path, value in _iter_key_paths(arguments))


def _is_shell_tool(tool_name: str) -> bool:
    normalized = tool_name.strip().lower().replace("-", "_")
    if normalized in _SHELL_TOOL_NAMES:
        return True
    return any(token in _SHELL_TOOL_NAMES for token in _name_tokens(normalized))


def _name_tokens(value: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9]+|_", value) if part}


def _schema_command_paths(schema: dict, prefix: str = "") -> Iterator[str]:
    if not isinstance(schema, dict):
        return
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key, child in properties.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if _schema_declares_command(str(key), child):
                yield path
            if isinstance(child, dict):
                yield from _schema_command_paths(child, path)


def _schema_declares_command(key: str, schema: Any) -> bool:
    if not isinstance(schema, dict):
        return key.lower() in _COMMAND_KEYS
    if key.lower() in _COMMAND_KEYS:
        return True
    description = " ".join(str(schema.get(field, "")) for field in ("title", "description"))
    return "shell command" in description.lower() or "command to execute" in description.lower()


def _looks_like_shell_command(value: Any) -> bool:
    if isinstance(value, list):
        return any(_looks_like_shell_command(item) for item in value)
    if not isinstance(value, str):
        return False
    parts = value.strip().split(None, 1)
    return bool(parts and parts[0].lower() in _SHELL_COMMANDS)


def _detect_filesystem_risk(tool_name: str, arguments: Any, repo_root: Path) -> bool:
    paths = [
        path
        for key_path, value in _iter_key_paths(arguments)
        if _path_key(key_path) and isinstance(value, str)
        for path in _extract_absolute_paths(value)
    ]
    if not paths:
        return False
    filesystem_tool = _is_filesystem_tool(tool_name) or any(_path_key(key_path) for key_path, _ in _iter_key_paths(arguments))
    return filesystem_tool and any(not _is_within_repo(path, repo_root) for path in paths)


def _extract_absolute_paths(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _extract_absolute_paths(item)
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith("/") or text.startswith("~"):
            yield Path(text).expanduser()


def _iter_key_paths(value: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path, child
            yield from _iter_key_paths(child, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_key_paths(item, f"{prefix}[{index}]")


def _path_key(key_path: str) -> bool:
    key = key_path.rsplit(".", 1)[-1].lower()
    key = key.split("[", 1)[0]
    return key in _PATH_KEYS


def _is_filesystem_tool(tool_name: str) -> bool:
    tokens = _name_tokens(tool_name.strip().lower().replace("-", "_"))
    return bool(tokens & {"file", "filesystem", "path", "directory", "read", "write"})


def _is_within_repo(path: Path, repo_root: Path) -> bool:
    try:
        path.resolve().relative_to(repo_root.resolve())
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
