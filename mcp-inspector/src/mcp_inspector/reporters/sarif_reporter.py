import json
import sys
from pathlib import Path


_SARIF_VERSION = "2.1.0"
_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_SEVERITY_TO_LEVEL = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}


def generate_sarif(report: dict) -> dict:
    findings = report.get("findings", [])
    scan_target = str(report.get("scan_target", ""))
    rules = [_rule(rule_id, grouped) for rule_id, grouped in _findings_by_rule(findings).items()]
    results = [_result(finding, scan_target) for finding in findings]

    return {
        "$schema": _SARIF_SCHEMA,
        "version": _SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Spectrona",
                        "informationUri": "https://github.com/0basedHuman/spectrona",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


def print_sarif(report: dict) -> None:
    print(json.dumps(generate_sarif(report), indent=2))


def write_sarif(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(generate_sarif(report), f, indent=2)
        f.write("\n")
    print(f"SARIF report written to: {path}", file=sys.stderr)


def _findings_by_rule(findings: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for finding in findings:
        rule_id = str(finding.get("id", "SPECTRONA_FINDING"))
        grouped.setdefault(rule_id, []).append(finding)
    return grouped


def _rule(rule_id: str, findings: list[dict]) -> dict:
    finding = findings[0]
    severity = str(finding.get("severity", "low")).lower()
    return {
        "id": rule_id,
        "name": rule_id,
        "shortDescription": {"text": str(finding.get("title", rule_id))},
        "fullDescription": {"text": str(finding.get("why_it_matters", ""))},
        "help": {"text": str(finding.get("recommended_fix", ""))},
        "properties": {
            "category": str(finding.get("category", "")),
            "precision": str(finding.get("confidence", "medium")),
            "problem.severity": severity,
            "security-severity": _security_severity(severity),
        },
    }


def _result(finding: dict, scan_target: str) -> dict:
    severity = str(finding.get("severity", "low")).lower()
    source = str(finding.get("source", ""))
    artifact_uri = _artifact_uri(source, scan_target)
    message = _message(finding)
    return {
        "ruleId": str(finding.get("id", "SPECTRONA_FINDING")),
        "level": _SEVERITY_TO_LEVEL.get(severity, "warning"),
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": artifact_uri},
                    "region": {"startLine": 1},
                }
            }
        ],
        "properties": {
            "severity": severity,
            "confidence": str(finding.get("confidence", "medium")),
            "source": source,
        },
    }


def _message(finding: dict) -> str:
    title = str(finding.get("title", "Spectrona finding"))
    evidence = str(finding.get("evidence", "")).strip()
    fix = str(finding.get("recommended_fix", "")).strip()
    parts = [title]
    if evidence:
        parts.append(f"Evidence: {evidence}")
    if fix:
        parts.append(f"Fix: {fix}")
    return "\n".join(parts)


def _artifact_uri(source: str, scan_target: str) -> str:
    candidate = source.split("→", 1)[0].strip() or scan_target
    if not candidate:
        return "spectrona-scan"
    path = Path(candidate)
    if path.is_absolute():
        try:
            return path.as_posix()
        except ValueError:
            return candidate
    return candidate.replace("\\", "/")


def _security_severity(severity: str) -> str:
    return {
        "critical": "9.0",
        "high": "7.0",
        "medium": "4.0",
        "low": "1.0",
    }.get(severity, "4.0")
