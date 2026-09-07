from ..models import Finding
from .secrets_detector import is_known_secret_value


_PACKAGE_COMMANDS = frozenset(["npx", "npm", "pnpm", "yarn", "pip", "pip3", "pipx", "uvx"])


def _looks_like_package_arg(arg: str) -> bool:
    if not arg or arg.startswith("-"):
        return False
    if _is_env_reference(arg):
        return False
    if is_known_secret_value(arg):
        return False
    if arg in {".", ".."}:
        return False
    if arg.startswith(("/", "~", "http://", "https://", "git+")):
        return False
    if "/" in arg and not arg.startswith("@"):
        return False
    return any(ch.isalpha() for ch in arg)


def _is_env_reference(arg: str) -> bool:
    return arg.startswith("${") and arg.endswith("}") and len(arg) > 3


def _is_pinned_package(arg: str) -> bool:
    if arg.startswith("@"):
        # Scoped npm packages are @scope/name@version. The first @ is not a pin.
        return "@" in arg[1:]
    return "@" in arg or "==" in arg


def _unpinned_packages(config: dict) -> list:
    command = config.get("command", "")
    if not isinstance(command, str):
        return []
    if command.lower() not in _PACKAGE_COMMANDS:
        return []

    unpinned = []
    for arg in config.get("args", []):
        if not isinstance(arg, str):
            continue
        if _looks_like_package_arg(arg) and not _is_pinned_package(arg):
            unpinned.append(arg)
    return unpinned


def detect(servers: dict, source_file: str) -> list:
    """Detect MCP_UNPINNED_PACKAGE findings across configured MCP servers."""
    evidence_items = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        packages = _unpinned_packages(config)
        if not packages:
            continue
        evidence_items.append(f"mcpServers.{name}.args: " + ", ".join(packages))

    if not evidence_items:
        return []

    return [
        Finding(
            id="MCP_UNPINNED_PACKAGE",
            title="MCP server installed from unpinned package source",
            severity="medium",
            category="supply-chain",
            source=f"{source_file} → mcpServers.*.args",
            evidence="; ".join(evidence_items),
            why_it_matters=(
                "Unpinned MCP package installs can silently change between runs, "
                "creating supply-chain and reproducibility risk."
            ),
            recommended_fix=(
                "Pin MCP server package versions, for example "
                "@modelcontextprotocol/server-filesystem@1.2.3."
            ),
            confidence="medium",
        )
    ]
