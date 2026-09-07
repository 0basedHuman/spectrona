import sys

_COLORS = {
    "critical": "\033[91m",
    "high":     "\033[33m",
    "medium":   "\033[93m",
    "low":      "\033[36m",
    "green":    "\033[92m",
    "bold":     "\033[1m",
    "reset":    "\033[0m",
}


def _c(key: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{_COLORS.get(key, '')}{text}{_COLORS['reset']}"


def _bold(text: str) -> str:
    return _c("bold", text)


def print_report(findings: list, scan_target: str) -> None:
    print()
    print(_bold("mcp-inspector") + "  —  local MCP security scanner")
    print(f"Scan target : {scan_target}")
    print()

    if not findings:
        print(_c("green", "✓  No findings — config looks safe."))
        print()
        return

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    total = sum(counts.values())
    parts = [
        _c(sev, f"{n} {sev.upper()}")
        for sev, n in counts.items()
        if n > 0
    ]
    print(_bold(f"FINDINGS  ({total} total: {', '.join(parts)})"))
    print("─" * 62)

    for f in findings:
        print()
        label = _c(f.severity, f"[{f.severity.upper()}]")
        print(f"  {label}  {_bold(f.id)}")
        print(f"  Title      : {f.title}")
        print(f"  Source     : {f.source}")
        print(f"  Evidence   : {f.evidence}")
        print(f"  Why        : {f.why_it_matters}")
        print(f"  Fix        : {f.recommended_fix}")
        print(f"  Confidence : {f.confidence}")

    print()
    print("─" * 62)

    if counts.get("critical", 0) > 0:
        print(_c("critical", "✗  UNSAFE — critical issues found. Fix immediately."))
    elif counts.get("high", 0) > 0:
        print(_c("high", "✗  UNSAFE — action required."))
    else:
        print(_c("medium", "⚠  REVIEW — low/medium findings present."))
    print()
