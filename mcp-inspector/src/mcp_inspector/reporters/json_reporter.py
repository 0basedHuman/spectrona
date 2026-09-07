import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone


def generate(findings: list, scan_target: str) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    return {
        "scan_target": scan_target,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "summary": {**counts, "total": sum(counts.values())},
        "findings": [asdict(f) for f in findings],
    }


def print_json(report: dict) -> None:
    print(json.dumps(report, indent=2))


def write_json(report: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report written to: {path}", file=sys.stderr)
