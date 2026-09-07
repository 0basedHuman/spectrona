#!/usr/bin/env python3
"""Build a deterministic Spectrona source archive for Homebrew releases."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = (
    "spectrona-detection",
    "mcp-inspector",
    "policy-engine",
    "runtime-guard",
    "spectrona-cli",
    "spectrona-gateway",
    "docs",
    "validation",
    "packaging",
)
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "dist",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".DS_Store",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Spectrona release archive")
    parser.add_argument("--version", help="Release version. Defaults to spectrona-cli pyproject version.")
    parser.add_argument("--output-dir", default="dist", help="Directory for release outputs.")
    parser.add_argument(
        "--source-url",
        help="Published source URL to include in the manifest. Defaults to the GitHub tag tarball URL.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable manifest JSON.")
    args = parser.parse_args()

    version = args.version or _project_version(ROOT / "spectrona-cli" / "pyproject.toml")
    _validate_versions(version)

    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    archive = output_dir / f"spectrona-{version}.tar.gz"
    source_url = args.source_url or f"https://github.com/spectrona/spectrona/archive/refs/tags/v{version}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="spectrona-release-") as tmp:
        staging_root = Path(tmp) / f"spectrona-{version}"
        staging_root.mkdir(parents=True)
        for component in COMPONENTS:
            src = ROOT / component
            if not src.exists():
                raise SystemExit(f"Missing release component: {component}")
            _copy_component(src, staging_root / component)
        _write_archive(staging_root, archive)

    sha256 = _sha256(archive)
    manifest = {
        "name": "spectrona",
        "version": version,
        "archive": str(archive),
        "sha256": sha256,
        "source_url": source_url,
        "homebrew_formula": str(ROOT / "packaging" / "homebrew" / "spectrona.rb"),
    }
    manifest_path = output_dir / f"spectrona-{version}.release.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"Archive: {archive}")
        print(f"SHA256 : {sha256}")
        print(f"URL    : {source_url}")
        print(f"Formula: {manifest['homebrew_formula']}")
    return 0


def _project_version(path: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(), re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not read project version from {path}")
    return match.group(1)


def _validate_versions(expected: str) -> None:
    for project in ("spectrona-detection", "mcp-inspector", "policy-engine", "runtime-guard", "spectrona-cli", "spectrona-gateway"):
        version = _project_version(ROOT / project / "pyproject.toml")
        if version != expected:
            raise SystemExit(f"{project} version {version} does not match release version {expected}")


def _copy_component(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    for path in sorted(src.rglob("*")):
        relative = path.relative_to(src)
        if _excluded(relative, path):
            continue
        target = dst / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _excluded(relative: Path, path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if path.name in EXCLUDED_SUFFIXES:
        return True
    return any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def _write_archive(staging_root: Path, archive: Path) -> None:
    with archive.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for path in [staging_root, *sorted(staging_root.rglob("*"))]:
                    info = tar.gettarinfo(str(path), arcname=str(path.relative_to(staging_root.parent)))
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if path.is_file():
                        with path.open("rb") as handle:
                            tar.addfile(info, handle)
                    else:
                        tar.addfile(info)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    sys.exit(main())
