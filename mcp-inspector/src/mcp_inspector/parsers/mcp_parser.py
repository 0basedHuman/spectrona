import json
import sys


def parse_mcp_config(path: str) -> dict:
    """Return mcpServers dict from an MCP JSON config file."""
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        raise
    return data.get("mcpServers", {})
