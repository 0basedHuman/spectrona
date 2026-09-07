from pathlib import Path

from ..models import Finding


def _is_filesystem_server(name: str, config: dict) -> bool:
    if "filesystem" in name.lower():
        return True
    for arg in config.get("args", []):
        if isinstance(arg, str) and "filesystem" in arg.lower():
            return True
    return False


def _extract_absolute_paths(args: list) -> list:
    """Return args that look like absolute or home-relative paths."""
    paths = []
    for arg in args:
        if not isinstance(arg, str):
            continue
        if arg.startswith("/"):
            paths.append(arg)
        elif arg.startswith("~"):
            paths.append(str(Path(arg).expanduser()))
    return paths


def _is_within_repo(path: str, repo_root: str) -> bool:
    try:
        repo = Path(repo_root).resolve()
        target = Path(path).resolve()
        target.relative_to(repo)
        return True
    except ValueError:
        return False


def detect(servers: dict, repo_root: str, source_file: str) -> list:
    """Detect MCP_FS_OUTSIDE_REPO findings across all configured MCP servers."""
    findings = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        if not _is_filesystem_server(name, config):
            continue

        args = config.get("args", [])
        absolute_paths = _extract_absolute_paths(args)
        unsafe = [p for p in absolute_paths if not _is_within_repo(p, repo_root)]

        if unsafe:
            findings.append(Finding(
                id="MCP_FS_OUTSIDE_REPO",
                title="Filesystem MCP allows paths outside project root",
                severity="high",
                category="mcp-permissions",
                source=f"{source_file} → mcpServers.{name}.args",
                evidence="allowed paths: " + ", ".join(unsafe),
                why_it_matters=(
                    "Claude/MCP tools may read or write SSH keys, cloud credentials, "
                    "shell configs, and other sensitive files outside your project."
                ),
                recommended_fix='Restrict allowed paths to the project root only (e.g. ".").',
                confidence="high",
            ))
    return findings
