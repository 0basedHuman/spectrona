import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_LOCAL_CLAUDE_FILES = [
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/settings.local.json",
]

_GLOBAL_CLAUDE_FILES = [
    Path.home() / ".claude" / "settings.json",
    Path.home() / ".claude" / "settings.local.json",
]


@dataclass
class ClaudeConfigFile:
    path: str
    kind: str
    size_bytes: int
    text: str
    data: Optional[dict]


def discover_claude_files(repo_root: str, include_global: bool = True) -> list[str]:
    """Return existing Claude config files in deterministic scan order."""
    root = Path(repo_root)
    candidates = [root / rel for rel in _LOCAL_CLAUDE_FILES]
    if include_global:
        candidates.extend(_GLOBAL_CLAUDE_FILES)

    seen = set()
    found = []
    for path in candidates:
        resolved = str(path.expanduser().resolve())
        if resolved in seen or not Path(resolved).exists():
            continue
        seen.add(resolved)
        found.append(resolved)
    return found


def parse_claude_target(file_path: Optional[str], repo_root: str) -> list[ClaudeConfigFile]:
    """Parse one Claude file, or discover known Claude files under a directory/root."""
    if file_path:
        target = Path(file_path).expanduser()
        if target.is_dir():
            paths = discover_claude_files(str(target), include_global=False)
        else:
            paths = [str(target)]
    else:
        paths = discover_claude_files(repo_root)

    return [parse_claude_file(path) for path in paths]


def parse_claude_file(file_path: str) -> ClaudeConfigFile:
    path = Path(file_path).expanduser()
    size_bytes = path.stat().st_size
    text = path.read_text(errors="replace")
    kind = _classify(path)
    data = None

    if kind == "settings":
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid Claude settings JSON: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError("Claude settings JSON must be an object")
        data = loaded

    return ClaudeConfigFile(
        path=str(path),
        kind=kind,
        size_bytes=size_bytes,
        text=text,
        data=data,
    )


def _classify(path: Path) -> str:
    name = path.name.lower()
    if name == "claude.md":
        return "instructions"
    if name in {"settings.json", "settings.local.json"}:
        return "settings"
    if path.suffix.lower() == ".json":
        return "settings"
    if path.suffix.lower() in {".md", ".markdown"}:
        return "instructions"
    return "unknown"
