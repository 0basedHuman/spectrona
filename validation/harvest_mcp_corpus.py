#!/usr/bin/env python3
"""Harvest redacted MCP config candidates from GitHub code search.

This helper intentionally does not run in the default validation gate. It needs
network access and, for GitHub code search, usually a token in GITHUB_TOKEN.
Output records are candidates: humans must review and set expected_finding_ids
before promotion into the labeled benchmark corpus.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERIES = (
    '"mcpServers" "command" "args"',
    '"mcpServers" "@modelcontextprotocol"',
    '"mcpServers" "uvx"',
    '"mcpServers" "npx"',
    '"mcpServers" "server-filesystem"',
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        action="append",
        help="GitHub code search query. May be repeated; defaults cover common MCP config shapes.",
    )
    parser.add_argument("--limit", type=int, default=1000, help="Maximum candidates to emit.")
    parser.add_argument("--output", required=True, help="Output JSONL candidate path.")
    args = parser.parse_args()

    _ensure_detection_importable()
    from spectrona_detection.secrets import redact_json

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        print("GITHUB_TOKEN is required for GitHub code search harvesting", file=sys.stderr)
        return 2

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out.open("w", encoding="utf-8") as handle:
        for item in _search_queries(_queries(args.query), token, args.limit):
            raw = _fetch_file(item["url"], token)
            config = _extract_first_mcp_config(raw)
            if config is None:
                continue
            record = {
                "case_id": _case_id(item),
                "source_url": item["html_url"],
                "source_type": "public_github",
                "repo_root": "__CORPUS_REPO__",
                "config": redact_json(config),
                "expected_finding_ids": [],
                "label_notes": "UNLABELED: review before benchmark use.",
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            written += 1
            if written >= args.limit:
                break
    print(f"wrote {written} redacted candidate records to {out}")
    return 0


def _ensure_detection_importable() -> None:
    src = ROOT / "spectrona-detection" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _search(query: str, token: str, limit: int):
    page = 1
    yielded = 0
    while yielded < limit:
        params = urllib.parse.urlencode({"q": query, "per_page": min(100, limit - yielded), "page": page})
        data = _github_json(f"https://api.github.com/search/code?{params}", token)
        items = data.get("items", [])
        if not items:
            return
        for item in items:
            yield item
            yielded += 1
            if yielded >= limit:
                return
        page += 1


def _search_queries(queries: list[str], token: str, limit: int, search=None):
    search = search or _search
    seen = set()
    yielded = 0
    for query in queries:
        if yielded >= limit:
            return
        for item in search(query, token, limit - yielded):
            key = item.get("html_url") or item.get("url") or _case_id(item)
            if key in seen:
                continue
            seen.add(key)
            yield item
            yielded += 1
            if yielded >= limit:
                return


def _queries(values: list[str] | None) -> list[str]:
    queries = [value.strip() for value in (values or DEFAULT_QUERIES) if value and value.strip()]
    if not queries:
        raise ValueError("at least one GitHub search query is required")
    return queries


def _fetch_file(api_url: str, token: str) -> str:
    data = _github_json(api_url, token)
    content = data.get("content", "")
    encoding = data.get("encoding")
    if encoding == "base64":
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return str(content)


def _github_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_first_mcp_config(text: str) -> dict[str, Any] | None:
    for candidate in _json_objects(text):
        parsed = _parse_json(candidate)
        if isinstance(parsed, dict) and isinstance(parsed.get("mcpServers"), dict):
            return {"mcpServers": parsed["mcpServers"]}
    return None


def _json_objects(text: str):
    starts = [match.start() for match in re.finditer(r"\{", text)]
    for start in starts:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    yield text[start:index + 1]
                    break


def _parse_json(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _case_id(item: dict[str, Any]) -> str:
    repo = item.get("repository", {}).get("full_name", "unknown")
    path = item.get("path", "unknown")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{repo}_{path}")
    return safe[:160]


if __name__ == "__main__":
    raise SystemExit(main())
