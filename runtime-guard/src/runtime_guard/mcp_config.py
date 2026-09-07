import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


_LOCAL_SEARCH = [".claude/mcp.json", ".mcp.json", "mcp.json"]
_GLOBAL_SEARCH = [Path.home() / ".claude" / "mcp.json"]


@dataclass(frozen=True)
class WrapResult:
    config: dict
    wrapped: int
    skipped: int
    already_wrapped: int


def find_mcp_config(repo_root: Path) -> Optional[Path]:
    for rel in _LOCAL_SEARCH:
        path = repo_root / rel
        if path.exists():
            return path
    for path in _GLOBAL_SEARCH:
        if path.exists():
            return path
    return None


def load_mcp_config(path: Path) -> dict:
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("MCP config root must be a JSON object")
    servers = data.get("mcpServers", {})
    if servers is not None and not isinstance(servers, dict):
        raise ValueError("MCP config mcpServers must be a JSON object")
    return data


def wrap_mcp_config(
    data: dict,
    repo_root: Path,
    spectrona_command: str = "spectrona",
    policy_path: Optional[Path] = None,
    audit_log: Optional[Path] = None,
) -> WrapResult:
    servers = data.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("MCP config mcpServers must be a JSON object")

    wrapped_config = dict(data)
    wrapped_servers = {}
    wrapped = 0
    skipped = 0
    already_wrapped = 0

    for name, server in servers.items():
        if not isinstance(server, dict):
            wrapped_servers[name] = server
            skipped += 1
            continue
        if is_wrapped_server(server):
            wrapped_servers[name] = server
            already_wrapped += 1
            continue
        command = server.get("command")
        if not isinstance(command, str) or not command.strip():
            wrapped_servers[name] = server
            skipped += 1
            continue

        upstream_args = server.get("args", [])
        if upstream_args is None:
            upstream_args = []
        if not isinstance(upstream_args, list):
            wrapped_servers[name] = server
            skipped += 1
            continue

        proxy_args = [
            "mcp",
            "proxy",
            "--client",
            f"mcp:{name}",
            "--repo-root",
            str(repo_root),
        ]
        if policy_path is not None:
            proxy_args.extend(["--policy", str(policy_path)])
        if audit_log is not None:
            proxy_args.extend(["--audit-log", str(audit_log)])
        proxy_args.extend(["--", command, *[str(arg) for arg in upstream_args]])

        next_server = dict(server)
        next_server["command"] = spectrona_command
        next_server["args"] = proxy_args
        wrapped_servers[name] = next_server
        wrapped += 1

    wrapped_config["mcpServers"] = wrapped_servers
    return WrapResult(
        config=wrapped_config,
        wrapped=wrapped,
        skipped=skipped,
        already_wrapped=already_wrapped,
    )


def wrap_file(
    input_path: Path,
    repo_root: Path,
    output_path: Optional[Path],
    apply: bool = False,
    force: bool = False,
    spectrona_command: str = "spectrona",
    policy_path: Optional[Path] = None,
    audit_log: Optional[Path] = None,
) -> tuple[WrapResult, Optional[Path], Optional[Path]]:
    data = load_mcp_config(input_path)
    result = wrap_mcp_config(
        data=data,
        repo_root=repo_root,
        spectrona_command=spectrona_command,
        policy_path=policy_path,
        audit_log=audit_log,
    )
    if not apply and output_path is None:
        return result, None, None

    target = input_path if apply else output_path
    if target is None:
        raise ValueError("output path is required when apply is false")
    if target.exists() and target != input_path and not force:
        raise FileExistsError(f"output already exists: {target}")

    backup_path = None
    if apply:
        backup_path = Path(str(input_path) + ".spectrona.bak")
        if not backup_path.exists():
            backup_path.write_text(json.dumps(data, indent=2) + "\n")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.config, indent=2) + "\n")
    return result, target, backup_path


def restore_backup(config_path: Path, backup_path: Optional[Path] = None) -> Path:
    backup = backup_path or Path(str(config_path) + ".spectrona.bak")
    if not backup.exists():
        raise FileNotFoundError(f"backup not found: {backup}")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(backup.read_text())
    return backup


def is_wrapped_server(server: dict) -> bool:
    args = server.get("args", [])
    if not isinstance(args, list):
        return False
    return len(args) >= 2 and args[0] == "mcp" and args[1] == "proxy"
