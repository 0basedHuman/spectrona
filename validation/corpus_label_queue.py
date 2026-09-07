#!/usr/bin/env python3
"""Build a human-labeling queue from redacted MCP corpus candidates."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "validation" / "corpus" / "labeling_queue.jsonl"


@dataclass(frozen=True)
class QueueRecord:
    data: dict[str, Any]
    predicted_ids: tuple[str, ...]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Redacted candidate JSONL from harvest_mcp_corpus.py.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output labeling queue JSONL.")
    parser.add_argument("--sample-size", type=int, default=250, help="Maximum queue records to write.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary.")
    args = parser.parse_args(argv)

    if args.sample_size < 1:
        print("--sample-size must be at least 1", file=sys.stderr)
        return 2

    _ensure_imports()
    records = [_prepare_record(item) for item in _load_jsonl(Path(args.input))]
    selected = _stratified_sample(records, args.sample_size)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record.data, sort_keys=True) + "\n")

    summary = {
        "input_records": len(records),
        "queued_records": len(selected),
        "output": str(out),
        "strata": _strata_summary(records),
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"read {len(records)} candidate records")
        print(f"wrote {len(selected)} labeling queue records to {out}")
        for key, count in summary["strata"].items():
            print(f"{key}: {count}")
    return 0


def _ensure_imports() -> None:
    for src in (
        ROOT / "spectrona-detection" / "src",
        ROOT / "mcp-inspector" / "src",
    ):
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(f"{path}:{line_no}: record must be an object")
            config = data.get("config")
            if not isinstance(config, dict):
                raise ValueError(f"{path}:{line_no}: config must be an object")
            expected = data.get("expected_finding_ids", [])
            if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
                raise ValueError(f"{path}:{line_no}: expected_finding_ids must be a list of strings")
            rows.append(data)
    return rows


def _prepare_record(data: dict[str, Any]) -> QueueRecord:
    findings = _scan_record(data)
    predicted = tuple(sorted({finding["id"] for finding in findings}))
    queued = dict(data)
    queued["predicted_finding_ids"] = list(predicted)
    queued["scanner_findings"] = findings
    queued["label_notes"] = _label_notes(data)
    queued.setdefault("expected_finding_ids", [])
    return QueueRecord(queued, predicted)


def _scan_record(data: dict[str, Any]) -> list[dict[str, str]]:
    from mcp_inspector.scanner import scan_mcp_config
    from spectrona_detection.secrets import redact_json

    files = data.get("files", {})
    if not isinstance(files, dict):
        files = {}

    case_id = str(data.get("case_id") or "candidate")
    with tempfile.TemporaryDirectory(prefix="spectrona_label_") as tmp_name:
        tmp = Path(tmp_name)
        case_dir = tmp / _safe_case_dir(case_id)
        case_dir.mkdir(parents=True)
        repo_root = case_dir / "repo"
        repo_root.mkdir()
        for relative, content in files.items():
            if not isinstance(relative, str) or not isinstance(content, str):
                continue
            target = (case_dir / relative).resolve()
            target.relative_to(case_dir.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        config_path = case_dir / "mcp.json"
        config_path.write_text(json.dumps(redact_json(data["config"]), indent=2) + "\n", encoding="utf-8")
        findings = scan_mcp_config(str(config_path), repo_root=str(repo_root))

    return [
        {
            "id": finding.id,
            "severity": finding.severity,
            "source": _normalize_source(finding.source),
            "evidence": str(redact_json(finding.evidence)),
        }
        for finding in findings
    ]


def _safe_case_dir(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "._-" else "_" for char in value)
    return safe[:120] or "candidate"


def _normalize_source(value: str) -> str:
    if " -> " in value:
        return "<corpus>/mcp.json -> " + value.split(" -> ", 1)[1]
    if value.endswith("mcp.json"):
        return "<corpus>/mcp.json"
    return value


def _label_notes(data: dict[str, Any]) -> str:
    notes = str(data.get("label_notes") or "").strip()
    prefix = "UNLABELED: review scanner_findings and set expected_finding_ids before benchmark promotion."
    if not notes:
        return prefix
    if notes.startswith("UNLABELED"):
        return notes
    return f"{prefix} Prior notes: {notes}"


def _stratified_sample(records: list[QueueRecord], limit: int) -> list[QueueRecord]:
    strata: dict[tuple[str, tuple[str, ...]], deque[QueueRecord]] = defaultdict(deque)
    for record in records:
        source_type = str(record.data.get("source_type") or "unknown")
        strata[(source_type, record.predicted_ids)].append(record)

    selected = []
    keys = deque(sorted(strata))
    while keys and len(selected) < limit:
        key = keys.popleft()
        queue = strata[key]
        selected.append(queue.popleft())
        if queue:
            keys.append(key)
    return selected


def _strata_summary(records: list[QueueRecord]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        source_type = str(record.data.get("source_type") or "unknown")
        predicted = ",".join(record.predicted_ids) if record.predicted_ids else "clean"
        counts[f"{source_type}:{predicted}"] += 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
