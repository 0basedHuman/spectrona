import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_LOCAL_CURSOR_FILES = [
    ".cursor/settings.json",
    ".cursorrules",
    ".cursor/mcp.json",
]

_GLOBAL_CURSOR_FILES = [
    Path.home() / ".cursor" / "mcp.json",
]

_RULE_EXTENSIONS = {".md", ".mdc", ".txt", ""}


@dataclass
class CursorConfigFile:
    path: str
    kind: str
    scope: str
    text: str
    data: Optional[dict]


def discover_cursor_files(repo_root: str, include_global: bool = True) -> list[str]:
    """Return existing Cursor config files in deterministic scan order."""
    root = Path(repo_root)
    candidates = [root / rel for rel in _LOCAL_CURSOR_FILES]
    candidates.extend(_discover_rule_files(root / ".cursor" / "rules"))
    if include_global:
        candidates.extend(_GLOBAL_CURSOR_FILES)

    seen = set()
    found = []
    for path in candidates:
        resolved = str(path.expanduser().resolve())
        if resolved in seen or not Path(resolved).exists():
            continue
        seen.add(resolved)
        found.append(resolved)
    return found


def parse_cursor_target(file_path: Optional[str], repo_root: str) -> list[CursorConfigFile]:
    """Parse one Cursor file, or discover known Cursor files under a directory/root."""
    if file_path:
        target = Path(file_path).expanduser()
        if target.is_dir():
            paths = discover_cursor_files(str(target), include_global=False)
            parse_root = str(target)
        else:
            paths = [str(target)]
            parse_root = repo_root
    else:
        paths = discover_cursor_files(repo_root)
        parse_root = repo_root

    return [parse_cursor_file(path, parse_root) for path in paths]


def parse_cursor_file(file_path: str, repo_root: str) -> CursorConfigFile:
    path = Path(file_path).expanduser()
    text = path.read_text(errors="replace")
    data = None

    if path.suffix.lower() == ".json":
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid Cursor JSON config: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError("Cursor JSON config must be an object")
        data = loaded

    return CursorConfigFile(
        path=str(path),
        kind=_classify(path, data),
        scope=_scope(path, repo_root),
        text=text,
        data=data,
    )


def _discover_rule_files(rules_dir: Path) -> list[Path]:
    if not rules_dir.exists() or not rules_dir.is_dir():
        return []
    return sorted(
        path
        for path in rules_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in _RULE_EXTENSIONS
    )


def _classify(path: Path, data: Optional[dict]) -> str:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if name == ".cursorrules" or "rules" in parts:
        return "rules"
    if data is not None and "mcpServers" in data:
        return "mcp"
    if name == "mcp.json" and path.parent.name.lower() == ".cursor":
        return "mcp"
    if path.suffix.lower() == ".json":
        return "settings"
    return "rules"


def _scope(path: Path, repo_root: str) -> str:
    try:
        path.expanduser().resolve().relative_to(Path(repo_root).expanduser().resolve())
        return "project"
    except ValueError:
        return "global"
