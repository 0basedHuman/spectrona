import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "vendor",
    ".venv",
    "venv",
}

_MAX_FILE_BYTES = 1024 * 1024
_MAX_FILES = 2000


@dataclass
class RepoFile:
    path: str
    relative_path: str
    size_bytes: int
    text: str


@dataclass
class RepoScan:
    repo_root: str
    files: list[RepoFile]
    gitignore_patterns: list[str]
    git_tracked_files: set[str]


def parse_repo_target(file_path: Optional[str], repo_root: Optional[str]) -> RepoScan:
    """Parse a repository directory or single file for static repo scanning."""
    root = Path(repo_root).expanduser().resolve() if repo_root else Path.cwd().resolve()
    target = Path(file_path).expanduser().resolve() if file_path else root

    if not target.exists():
        raise FileNotFoundError(str(target))

    if target.is_file():
        scan_root = root if _is_within(target, root) else target.parent
        paths = [target]
    else:
        scan_root = target
        paths = _discover_files(scan_root)

    return RepoScan(
        repo_root=str(scan_root),
        files=[_read_file(path, scan_root) for path in paths],
        gitignore_patterns=_read_gitignore(scan_root),
        git_tracked_files=_git_tracked_files(scan_root),
    )


def _discover_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*")):
        if len(files) >= _MAX_FILES:
            break
        if path.is_dir():
            continue
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _read_file(path: Path, root: Path) -> RepoFile:
    try:
        size_bytes = path.stat().st_size
    except OSError:
        size_bytes = 0
    try:
        raw = path.read_bytes()
    except OSError:
        raw = b""
    if b"\x00" in raw[:4096]:
        text = ""
    else:
        text = raw.decode("utf-8", errors="replace")
    return RepoFile(
        path=str(path),
        relative_path=_relative(path, root),
        size_bytes=size_bytes,
        text=text,
    )


def _read_gitignore(root: Path) -> list[str]:
    path = root / ".gitignore"
    if not path.exists():
        return []
    patterns = []
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("!"):
            continue
        patterns.append(stripped)
    return patterns


def _git_tracked_files(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
