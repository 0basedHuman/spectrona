#!/usr/bin/env python3
"""Promote human-labeled MCP queue records into a benchmark corpus."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "validation" / "corpus" / "mcp_configs_labeled.jsonl"
PREDICTION_ONLY_FIELDS = {"predicted_finding_ids", "scanner_findings"}
RAW_SECRET_MARKERS = (
    "REALSECRETVALUE123456",
    "SuperSecret123",
    "sk_live_51H8xYzAbCdEfGhIjKlMnOp",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Human-labeled queue JSONL.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output benchmark corpus JSONL.")
    parser.add_argument("--min-size", type=int, default=1, help="Minimum labeled records required.")
    parser.add_argument("--check-benchmark", action="store_true", help="Run the precision benchmark before writing output.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary.")
    args = parser.parse_args(argv)

    if args.min_size < 1:
        print("--min-size must be at least 1", file=sys.stderr)
        return 2

    try:
        records = _load_promotable_records(Path(args.input))
        if len(records) < args.min_size:
            raise ValueError(f"labeled corpus has {len(records)} records; need at least {args.min_size}")
        serialized = "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n"
        _assert_no_raw_secret_markers(serialized)
        if args.check_benchmark:
            _run_benchmark_check(serialized, args.min_size)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(serialized, encoding="utf-8")

    summary = {"input_records": len(records), "output": str(out)}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"wrote {len(records)} labeled corpus records to {out}")
    return 0


def _load_promotable_records(path: Path) -> list[dict[str, Any]]:
    records = []
    seen_ids = set()
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(f"{path}:{line_no}: record must be an object")
            record = _normalize_record(data, path, line_no)
            case_id = record["case_id"]
            if case_id in seen_ids:
                raise ValueError(f"{path}:{line_no}: duplicate case_id {case_id}")
            seen_ids.add(case_id)
            records.append(record)
    return records


def _normalize_record(data: dict[str, Any], path: Path, line_no: int) -> dict[str, Any]:
    if _is_unlabeled(data):
        raise ValueError(f"{path}:{line_no}: record is still unlabeled")
    config = data.get("config")
    if not isinstance(config, dict):
        raise ValueError(f"{path}:{line_no}: config must be an object")
    expected = data.get("expected_finding_ids")
    if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
        raise ValueError(f"{path}:{line_no}: expected_finding_ids must be a list of strings")
    files = data.get("files", {})
    if not isinstance(files, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in files.items()):
        raise ValueError(f"{path}:{line_no}: files must be an object of path strings to content strings")
    normalized = {
        "case_id": str(data.get("case_id") or f"case-{line_no}"),
        "source_url": str(data.get("source_url") or "unknown"),
        "source_type": str(data.get("source_type") or "unknown"),
        "repo_root": str(data.get("repo_root") or "__CORPUS_REPO__"),
        "config": config,
        "expected_finding_ids": sorted(set(expected)),
        "label_notes": str(data.get("label_notes") or ""),
    }
    if files:
        normalized["files"] = files
    return normalized


def _is_unlabeled(data: dict[str, Any]) -> bool:
    notes = str(data.get("label_notes") or "")
    if notes.startswith("UNLABELED"):
        return True
    return bool(PREDICTION_ONLY_FIELDS & set(data)) and not data.get("reviewed")


def _assert_no_raw_secret_markers(text: str) -> None:
    for marker in RAW_SECRET_MARKERS:
        if marker in text:
            raise ValueError(f"raw reviewed secret marker found in labeled corpus: {marker}")


def _run_benchmark_check(serialized: str, min_size: int) -> None:
    validation_dir = str(ROOT / "validation")
    if validation_dir not in sys.path:
        sys.path.insert(0, validation_dir)
    import corpus_benchmark

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as handle:
        handle.write(serialized)
        temp_path = handle.name
    try:
        result = corpus_benchmark.main(["--corpus", temp_path, "--min-size", str(min_size)])
        if result != 0:
            raise ValueError("promoted corpus failed precision benchmark")
    finally:
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
