#!/usr/bin/env python3
"""Benchmark scanner precision/recall against a redacted MCP config corpus."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "validation" / "corpus" / "mcp_configs_seed.jsonl"
DEFAULT_THRESHOLD = 0.95


@dataclass(frozen=True)
class Case:
    case_id: str
    source_url: str
    source_type: str
    repo_root: str
    config: dict[str, Any]
    files: dict[str, str]
    expected_finding_ids: set[str]
    label_notes: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="JSONL corpus path.")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="Minimum precision per measured rule.")
    parser.add_argument("--min-size", type=int, default=1, help="Minimum number of labeled corpus cases required.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)

    _ensure_imports()
    cases = list(_load_cases(Path(args.corpus)))
    if len(cases) < args.min_size:
        print(f"corpus has {len(cases)} cases; need at least {args.min_size}", file=sys.stderr)
        return 2

    result = _run_benchmark(cases, args.threshold)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_text(result)

    return 1 if result["failed_rules"] else 0


def _ensure_imports() -> None:
    for src in (
        ROOT / "spectrona-detection" / "src",
        ROOT / "mcp-inspector" / "src",
    ):
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))


def _load_cases(path: Path) -> list[Case]:
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            data = json.loads(line)
            config = data.get("config")
            if not isinstance(config, dict):
                raise ValueError(f"{path}:{line_no}: config must be an object")
            expected = data.get("expected_finding_ids", [])
            if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
                raise ValueError(f"{path}:{line_no}: expected_finding_ids must be a list of strings")
            files = data.get("files", {})
            if not isinstance(files, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in files.items()):
                raise ValueError(f"{path}:{line_no}: files must be an object of path strings to content strings")
            cases.append(Case(
                case_id=str(data.get("case_id") or f"case-{line_no}"),
                source_url=str(data.get("source_url") or "unknown"),
                source_type=str(data.get("source_type") or "unknown"),
                repo_root=str(data.get("repo_root") or "__CORPUS_REPO__"),
                config=config,
                files=files,
                expected_finding_ids=set(expected),
                label_notes=str(data.get("label_notes") or ""),
            ))
    return cases


def _run_benchmark(cases: list[Case], threshold: float) -> dict[str, Any]:
    from mcp_inspector.scanner import scan_mcp_config

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    case_results = []

    with tempfile.TemporaryDirectory(prefix="spectrona_corpus_") as tmp_name:
        tmp = Path(tmp_name)
        for case in cases:
            case_dir = tmp / case.case_id
            case_dir.mkdir(parents=True)
            repo_root = case_dir / "repo"
            repo_root.mkdir()
            _materialize_files(case_dir, case.files)
            config_path = case_dir / "mcp.json"
            config_path.write_text(json.dumps(case.config, indent=2) + "\n", encoding="utf-8")

            expected = set(case.expected_finding_ids)
            findings = scan_mcp_config(str(config_path), repo_root=str(_repo_root(case.repo_root, repo_root)))
            predicted = {finding.id for finding in findings}
            for rule_id in sorted(expected | predicted):
                if rule_id in expected and rule_id in predicted:
                    counts[rule_id]["tp"] += 1
                elif rule_id in predicted:
                    counts[rule_id]["fp"] += 1
                else:
                    counts[rule_id]["fn"] += 1
            case_results.append({
                "case_id": case.case_id,
                "source_type": case.source_type,
                "expected": sorted(expected),
                "predicted": sorted(predicted),
                "unexpected": sorted(predicted - expected),
                "missed": sorted(expected - predicted),
            })

    rules = {}
    failed = []
    for rule_id, values in sorted(counts.items()):
        tp = values["tp"]
        fp = values["fp"]
        fn = values["fn"]
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        status = "pass"
        if precision is not None and precision < threshold:
            status = "fail"
            failed.append(rule_id)
        rules[rule_id] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "status": status,
        }

    return {
        "corpus_cases": len(cases),
        "threshold": threshold,
        "rules": rules,
        "failed_rules": failed,
        "cases": case_results,
    }


def _materialize_files(base: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        target = (base / relative).resolve()
        target.relative_to(base.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _repo_root(value: str, default: Path) -> Path:
    if value == "__CORPUS_REPO__":
        return default
    path = Path(value)
    return path if path.is_absolute() else default / path


def _print_text(result: dict[str, Any]) -> None:
    print(f"Corpus cases: {result['corpus_cases']}")
    print(f"Precision gate: {result['threshold']:.2%}")
    print("")
    print("rule_id,tp,fp,fn,precision,recall,status")
    for rule_id, item in result["rules"].items():
        precision = _fmt(item["precision"])
        recall = _fmt(item["recall"])
        print(f"{rule_id},{item['tp']},{item['fp']},{item['fn']},{precision},{recall},{item['status']}")
    if result["failed_rules"]:
        print("")
        print("Failed rules: " + ", ".join(result["failed_rules"]))


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


if __name__ == "__main__":
    raise SystemExit(main())
